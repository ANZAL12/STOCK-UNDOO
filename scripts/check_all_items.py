import sys
import re
sys.path.insert(0, 'a:/Stock Undoo/scripts')
from test_tally_connectivity import post_tally_xml, parse_stock_summary

# 1. Test TDL Collection for all StockItems
tdl_xml = """<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
        <TDL>
          <TDLMESSAGE>
            <COLLECTION NAME="AllStockItems" ISINITIALIZE="Yes">
              <TYPE>StockItem</TYPE>
              <NATIVEMETHOD>Name</NATIVEMETHOD>
              <NATIVEMETHOD>ClosingBalance</NATIVEMETHOD>
              <NATIVEMETHOD>BaseUnits</NATIVEMETHOD>
            </COLLECTION>
          </TDLMESSAGE>
        </TDL>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

ok, resp, lat = post_tally_xml('127.0.0.1', 9000, tdl_xml)
print(f"TDL Query OK: {ok}, length: {len(resp)} bytes")
matches = re.findall(r'NAME="([^"]+)"', resp)
print(f"TDL matches: {len(matches)}")

# 2. Test List of Accounts
accounts_xml = """<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Accounts</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <ACCOUNTTYPE>Stock Items</ACCOUNTTYPE>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

ok2, resp2, lat2 = post_tally_xml('127.0.0.1', 9000, accounts_xml)
print(f"List of Accounts OK: {ok2}, length: {len(resp2)} bytes")
items2 = re.findall(r'<STOCKITEM[^>]*NAME="([^"]+)"', resp2)
print(f"List of Accounts found {len(items2)} stock items!")

# 3. Test Stock Summary with Explode & ItemWise
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
          <ISCONDENSED>No</ISCONDENSED>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

ok3, resp3, lat3 = post_tally_xml('127.0.0.1', 9000, summary_xml)
parsed = parse_stock_summary(resp3)
print(f"Stock Summary parsed {len(parsed)} items!")

