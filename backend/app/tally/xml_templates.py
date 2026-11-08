"""
STOCK UNDO! - Strictly Read-Only XML Request Templates for TallyPrime.
Under no circumstances are any write, modify, or insert tags generated.
"""

from typing import Optional


def escape_xml(text: Optional[str]) -> str:
    """Escapes special characters for safe inclusion in Tally XML envelopes."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_company_list_request() -> str:
    """Read-only request to list all currently open companies in Tally."""
    return """<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Companies</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def build_stock_summary_request(company_name: Optional[str] = None) -> str:
    """
    Read-only request to export item-wise Stock Summary with closing quantities.
    STRICTLY NON-FINANCIAL (rates and values are ignored by the parser).
    """
    company_filter = (
        f"<SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY>"
        if company_name
        else ""
    )
    return f"""<ENVELOPE>
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
          {company_filter}
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def build_stock_item_details_request(item_name: str, company_name: Optional[str] = None) -> str:
    """
    Read-only request for a specific Stock Item's closing quantity using TDL Collection.
    Guarantees no data mutation.
    """
    company_filter = (
        f"<SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY>"
        if company_name
        else ""
    )
    escaped_item = escape_xml(item_name)
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          {company_filter}
        </STATICVARIABLES>
        <TDL>
          <TDLMESSAGE>
            <COLLECTION NAME="SingleStockItemCollection" ISINITIALIZE="Yes">
              <TYPE>StockItem</TYPE>
              <NATIVEMETHOD>Name</NATIVEMETHOD>
              <NATIVEMETHOD>ClosingBalance</NATIVEMETHOD>
              <NATIVEMETHOD>BaseUnits</NATIVEMETHOD>
              <FILTERS>MatchSpecificItem</FILTERS>
            </COLLECTION>
            <SYSTEM TYPE="Formulae" NAME="MatchSpecificItem">
              $Name = "{escaped_item}"
            </SYSTEM>
          </TDLMESSAGE>
        </TDL>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

