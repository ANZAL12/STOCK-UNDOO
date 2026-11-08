import sys
import re
import xml.etree.ElementTree as ET
sys.path.insert(0, 'a:/Stock Undoo/scripts')
from test_tally_connectivity import post_tally_xml, sanitize_tally_xml

accounts_xml = """<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
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

ok, resp, _ = post_tally_xml('127.0.0.1', 9000, accounts_xml)
clean = sanitize_tally_xml(resp)

# Find first 5 STOCKITEM blocks
stock_items = re.findall(r'<STOCKITEM\s+NAME="([^"]+)"[^>]*>(.*?)</STOCKITEM>', clean, re.DOTALL)
print(f"Total STOCKITEM blocks found by regex: {len(stock_items)}")
for name, body in stock_items[:5]:
    closing = re.search(r'<CLOSINGBALANCE>([^<]+)</CLOSINGBALANCE>', body)
    units = re.search(r'<BASEUNITS>([^<]+)</BASEUNITS>', body)
    cl_val = closing.group(1) if closing else "None"
    u_val = units.group(1) if units else "None"
    print(f" - {name} | Closing: {cl_val} | Unit: {u_val}")

