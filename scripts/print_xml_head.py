import sys
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
print("Response length:", len(resp))
print("First 1500 chars:\n", resp[:1500])

