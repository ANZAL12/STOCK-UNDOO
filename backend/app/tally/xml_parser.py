"""
STOCK UNDO! - Robust XML Parser for TallyPrime Responses.
Strictly extracts item names, closing quantities, and units.
Silently discards any financial, cost, rate, or ledger data.
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


logger = logging.getLogger("stock_undo.xml_parser")


def sanitize_tally_xml(xml_content: str) -> str:
    """
    Sanitizes Tally XML output by removing illegal XML character entities
    (&#0; through &#31;) and unprintable ASCII control characters.
    """
    if not xml_content:
        return ""
    # Strip illegal entity references
    s = re.sub(r'&#(?:[0-8]|1[1-2]|1[4-9]|[2-3][0-9]);', '', xml_content)
    # Strip raw control characters except tab (\t), newline (\n), and CR (\r)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
    return s


def clean_node_text(node: Optional[ET.Element]) -> str:
    """Extracts and strips inner text from an XML element safely."""
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def parse_quantity_and_unit(qty_str: str) -> (float, str):
    """
    Parses Tally closing balance strings like:
      "14 Nos"       -> (14.0, "Nos")
      "-2 Box"       -> (-2.0, "Box")
      "1,250.50 Kg"  -> (1250.5, "Kg")
      "0"            -> (0.0, "Nos")
    """
    if not qty_str:
        return 0.0, "Nos"

    cleaned = qty_str.replace(",", "").strip()
    # Match optional negative sign, digits, optional decimal, and remaining unit string
    match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*(.*)", cleaned)
    if match:
        try:
            qty = float(match.group(1))
            unit = match.group(2).strip() or "Nos"
            return qty, unit
        except ValueError:
            pass
    return 0.0, "Nos"


def parse_companies(xml_content: str) -> List[str]:
    """Extracts open company names from Tally XML response."""
    companies: List[str] = []
    if not xml_content or not xml_content.strip():
        return companies

    clean_xml = sanitize_tally_xml(xml_content)
    try:
        root = ET.fromstring(clean_xml)

        # 1. Check direct SVCURRENTCOMPANY in envelope
        cur = root.findtext(".//SVCURRENTCOMPANY")
        if cur and cur.strip() and cur.strip() not in companies:
            companies.append(cur.strip())

        # 2. Iterate COMPANY nodes
        for comp in root.iter():
            tag = comp.tag.upper().split("}")[-1]
            if tag == "COMPANY":
                name = comp.attrib.get("NAME") or clean_node_text(comp.find("NAME"))
                if not name:
                    rem = comp.find("REMOTECMPINFO.LIST")
                    if rem is not None:
                        name = clean_node_text(rem.find("NAME"))
                if name and name not in companies:
                    companies.append(name)
    except Exception as e:
        logger.warning(f"Error parsing Tally companies: {e}")

    return companies


def parse_stock_summary(xml_content: str) -> Dict[str, Dict[str, Any]]:
    """
    Parses item-wise Stock Summary from Tally XML.
    Returns:
      {
         "FORMENTY LED FMTY -FM55UHDQTVDXB5": {
             "closing_qty": 14.0,
             "unit": "Nos",
             "raw": "14 Nos"
         }
      }
    """
    items: Dict[str, Dict[str, Any]] = {}
    if not xml_content or not xml_content.strip():
        return items

    clean_xml = sanitize_tally_xml(xml_content)
    try:
        root = ET.fromstring(clean_xml)

        current_item_name: Optional[str] = None
        for elem in root:
            tag = elem.tag.upper().split("}")[-1]

            # In Tally Stock Summary Report:
            # <DSPACCNAME><DSPDISPNAME>Product Name</DSPDISPNAME></DSPACCNAME>
            # <DSPSTKINFO><DSPCLQTY>14 Nos</DSPCLQTY></DSPSTKINFO>
            if tag == "DSPACCNAME":
                disp = elem.find("DSPDISPNAME")
                if disp is not None and disp.text:
                    current_item_name = disp.text.strip()
            elif tag == "DSPSTKINFO" and current_item_name:
                cl = elem.find(".//DSPCLQTY")
                raw_qty = clean_node_text(cl) if cl is not None else "0 Nos"
                qty, unit = parse_quantity_and_unit(raw_qty)

                items[current_item_name] = {
                    "closing_qty": qty,
                    "unit": unit,
                    "raw": raw_qty
                }
                current_item_name = None

        # Fallback: Check if response contains direct <STOCKITEM> nodes
        if not items:
            for si in root.iter():
                tag = si.tag.upper().split("}")[-1]
                if tag in ("STOCKITEM", "ITEM"):
                    name = si.attrib.get("NAME") or clean_node_text(si.find("NAME"))
                    if not name:
                        continue
                    cl = si.find("CLOSINGBALANCE")
                    raw_qty = clean_node_text(cl) if cl is not None else "0 Nos"
                    qty, unit = parse_quantity_and_unit(raw_qty)
                    items[name.strip()] = {
                        "closing_qty": qty,
                        "unit": unit,
                        "raw": raw_qty
                    }

    except Exception as e:
        logger.warning(f"Error parsing Tally stock summary: {e}")

    return items

