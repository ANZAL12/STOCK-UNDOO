import sys
import re

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

sys.path.insert(0, 'a:/Stock Undoo/scripts')
from test_tally_connectivity import post_tally_xml

ok, resp, lat = post_tally_xml('127.0.0.1', 9000, accounts_xml, timeout=15.0)
print(f"List of Accounts: OK={ok}, Latency={lat}ms, length={len(resp)}")

if ok:
    # Save a small sample of the response to inspect
    with open('a:/Stock Undoo/scripts/sample_accounts.xml', 'w', encoding='utf-8') as f:
        f.write(resp[:50000])
    print("Saved first 50k bytes to sample_accounts.xml")

