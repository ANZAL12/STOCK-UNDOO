"""
Unit tests for STOCK UNDO! FastAPI Backend
"""

import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure app is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.models.stock import StockStatus
from app.tally.xml_parser import parse_quantity_and_unit, parse_stock_summary
from app.tally.xml_templates import (
    build_fast_stock_collection_request,
    build_stock_item_details_request,
    build_stock_summary_request,
)


class TestStockUndoAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["app_name"], "STOCK UNDO!")
        self.assertEqual(data["tagline"], "Check stock before you call the godown!")

    def test_tally_status_endpoint(self):
        response = self.client.get("/api/tally/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("pc1", data)
        self.assertIn("pc2", data)
        self.assertEqual(data["pc1"]["pc"], "pc1")
        self.assertEqual(data["pc2"]["pc"], "pc2")

    def test_whitelist_endpoint(self):
        response = self.client.get("/api/stock/whitelist")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data["total_models"], 0)
        self.assertIsInstance(data["models"], list)

    def test_all_stock_endpoint(self):
        response = self.client.get("/api/stock/all")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("pc1_status", data)
        self.assertIn("pc2_status", data)
        self.assertIn("items", data)
        self.assertGreater(len(data["items"]), 0)

    def test_search_stock_endpoint(self):
        response = self.client.get("/api/stock/search?q=FORMENTY")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        for item in data:
            self.assertIn("FORMENTY", item["model"].upper())

    def test_search_flexible_spacing_and_punctuation(self):
        # 1. Missing/added spaces & hyphens: "asgg 18 cpaa" should match "ASGG 18CPAA-B 1.5 INV"
        res_spaced = self.client.get("/api/stock/search?q=asgg%2018%20cpaa")
        self.assertEqual(res_spaced.status_code, 200)
        models_spaced = [item["model"] for item in res_spaced.json()]
        self.assertGreater(len(models_spaced), 0)
        self.assertTrue(any("18CPAA" in m.upper() for m in models_spaced))

        # 2. Extra spaces & skipped middle words: "32 smart" should match "32 HDS FM 32 HDSOP 2  SMART"
        res_multi_word = self.client.get("/api/stock/search?q=32%20smart")
        self.assertEqual(res_multi_word.status_code, 200)
        models_multi = [item["model"] for item in res_multi_word.json()]
        self.assertGreater(len(models_multi), 0)
        self.assertTrue(any("32" in m and "SMART" in m.upper() for m in models_multi))

        # 3. Added spaces in compact model: "fm 40 hdspt3" should match "FM40HDSPT3"
        res_split = self.client.get("/api/stock/search?q=fm%2040%20hdspt3")
        self.assertEqual(res_split.status_code, 200)
        models_split = [item["model"] for item in res_split.json()]
        self.assertGreater(len(models_split), 0)
        self.assertTrue(any("FM40HDSPT3" in m.upper() for m in models_split))

    def test_parse_collection_with_unbound_udf_prefix(self):
        xml = """<ENVELOPE>
          <BODY>
            <DATA>
              <COLLECTION>
                <STOCKITEM NAME="ES3V-C1(H)I:EWH/M/Dummy/3L" RESERVEDNAME="">
                  <CLOSINGBALANCE TYPE="Quantity"> 3 Nos</CLOSINGBALANCE>
                  <LANGUAGENAME.LIST>
                    <UDF:HO_QTY.LIST DESC="`HO_QTY`"><UDF:HO_QTY>1</UDF:HO_QTY></UDF:HO_QTY.LIST>
                  </LANGUAGENAME.LIST>
                </STOCKITEM>
              </COLLECTION>
            </DATA>
          </BODY>
        </ENVELOPE>"""
        parsed = parse_stock_summary(xml)
        self.assertIn("ES3V-C1(H)I:EWH/M/Dummy/3L", parsed)
        self.assertEqual(parsed["ES3V-C1(H)I:EWH/M/Dummy/3L"]["closing_qty"], 3.0)
        self.assertEqual(parsed["ES3V-C1(H)I:EWH/M/Dummy/3L"]["unit"], "Nos")

    def test_parser_never_parses_rates_or_financial_values(self):
        # Collection XML containing financial/rate tags and alternate-unit/rate strings
        collection_xml = """<ENVELOPE>
          <BODY>
            <DATA>
              <COLLECTION>
                <STOCKITEM NAME="MODEL-RATE-IN-TAGS">
                  <CLOSINGBALANCE TYPE="Quantity">12 Nos</CLOSINGBALANCE>
                  <CLOSINGRATE>24999.00/Nos</CLOSINGRATE>
                  <CLOSINGVALUE>-299988.00</CLOSINGVALUE>
                  <OPENINGRATE>21000.00/Nos</OPENINGRATE>
                  <OPENINGVALUE>-105000.00</OPENINGVALUE>
                  <STANDARDCOST.LIST><RATE>19500.00/Nos</RATE></STANDARDCOST.LIST>
                  <STANDARDPRICE.LIST><RATE>25999.00/Nos</RATE></STANDARDPRICE.LIST>
                </STOCKITEM>
                <STOCKITEM NAME="MODEL-ALT-UNIT">
                  <CLOSINGBALANCE>1 Nos =  2.00 NA</CLOSINGBALANCE>
                </STOCKITEM>
                <STOCKITEM NAME="MODEL-ANNOTATED-RATE">
                  <CLOSINGBALANCE>7 Pcs @ 15000/Pcs = 105000</CLOSINGBALANCE>
                </STOCKITEM>
              </COLLECTION>
            </DATA>
          </BODY>
        </ENVELOPE>"""

        parsed = parse_stock_summary(collection_xml)
        for item_data in parsed.values():
            self.assertEqual(set(item_data.keys()), {"closing_qty", "unit"})

        self.assertEqual(parsed["MODEL-RATE-IN-TAGS"], {"closing_qty": 12.0, "unit": "Nos"})
        self.assertEqual(parsed["MODEL-ALT-UNIT"], {"closing_qty": 1.0, "unit": "Nos"})
        self.assertEqual(parsed["MODEL-ANNOTATED-RATE"], {"closing_qty": 7.0, "unit": "Pcs"})

        # Stock Summary XML containing DSPCLRATE and DSPCLAMTA must be ignored completely
        summary_xml = """<ENVELOPE>
          <DSPACCNAME><DSPDISPNAME>MODEL-SUMMARY-TEST</DSPDISPNAME></DSPACCNAME>
          <DSPSTKINFO>
            <DSPSTKCL>
              <DSPCLQTY>9 Nos</DSPCLQTY>
              <DSPCLRATE>34500.00</DSPCLRATE>
              <DSPCLAMTA>-310500.00</DSPCLAMTA>
            </DSPSTKCL>
          </DSPSTKINFO>
        </ENVELOPE>"""
        parsed_summary = parse_stock_summary(summary_xml)
        self.assertEqual(parsed_summary["MODEL-SUMMARY-TEST"], {"closing_qty": 9.0, "unit": "Nos"})

        # Direct rate/currency strings must never leak as stock quantity or unit
        self.assertEqual(parse_quantity_and_unit("15000.00/Nos"), (0.0, "Nos"))
        self.assertEqual(parse_quantity_and_unit("Rs. 25000"), (0.0, "Nos"))
        self.assertEqual(parse_quantity_and_unit("₹ 19,500.00"), (0.0, "Nos"))
        self.assertEqual(parse_quantity_and_unit("25000 INR"), (0.0, "Nos"))

    def test_xml_templates_and_api_exclude_rates(self):
        fast_req = build_fast_stock_collection_request()
        self.assertIn("<FETCH>ClosingBalance</FETCH>", fast_req)
        for forbidden in ("Rate", "ClosingRate", "ClosingValue", "OpeningValue", "Amount", "Cost", "Price"):
            self.assertNotIn(forbidden, fast_req)

        summary_req = build_stock_summary_request()
        self.assertIn("<DSPSHOWRATE>No</DSPSHOWRATE>", summary_req)
        self.assertIn("<DSPSHOWVALUE>No</DSPSHOWVALUE>", summary_req)

        details_req = build_stock_item_details_request("TEST MODEL")
        self.assertIn("<NATIVEMETHOD>ClosingBalance</NATIVEMETHOD>", details_req)
        self.assertNotIn("Rate", details_req)

        forbidden_json_keys = {"rate", "price", "cost", "value", "amount", "closing_rate", "closing_value", "mrp", "raw"}
        res = self.client.get("/api/stock/all")
        self.assertEqual(res.status_code, 200)
        for item in res.json()["items"]:
            self.assertTrue(forbidden_json_keys.isdisjoint({k.lower() for k in item.keys()}))


if __name__ == "__main__":
    unittest.main()
