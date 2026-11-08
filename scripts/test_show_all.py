import sys
sys.path.insert(0, 'a:/Stock Undoo/scripts')
from test_tally_connectivity import post_tally_xml, parse_stock_summary

# Test Stock Summary with DSPSHOWALLACCOUNTS = Yes
summary_xml = """<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Stock Summary</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
          <ISITEMWISE>Yes</ISITEMWISE>
          <DSPSHOWALLACCOUNTS>Yes</DSPSHOWALLACCOUNTS>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

ok, resp, lat = post_tally_xml('127.0.0.1', 9000, summary_xml, timeout=10.0)
parsed = parse_stock_summary(resp)
print(f"Stock Summary with DSPSHOWALLACCOUNTS=Yes returned {len(parsed)} items in {lat:.1f}ms!")

# Test without DSPSHOWALLACCOUNTS
summary_xml_normal = """<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Stock Summary</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
          <ISITEMWISE>Yes</ISITEMWISE>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

ok2, resp2, lat2 = post_tally_xml('127.0.0.1', 9000, summary_xml_normal, timeout=10.0)
parsed2 = parse_stock_summary(resp2)
print(f"Normal Stock Summary returned {len(parsed2)} items in {lat2:.1f}ms!")

