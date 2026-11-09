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
    Read-only request to export item-wise Stock Summary with closing quantities ONLY.
    STRICTLY NON-FINANCIAL: disables rates, values, inwards, and outwards at Tally source.
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
          <DSPSHOWQTY>Yes</DSPSHOWQTY>
          <DSPSHOWRATE>No</DSPSHOWRATE>
          <DSPSHOWVALUE>No</DSPSHOWVALUE>
          <DSPSHOWINWARDS>No</DSPSHOWINWARDS>
          <DSPSHOWOUTWARDS>No</DSPSHOWOUTWARDS>
          {company_filter}
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def build_fast_stock_collection_request(company_name: Optional[str] = None) -> str:
    """
    High-speed, minimal-CPU read-only TDL Collection query for TallyPrime.
    Fetches ONLY ClosingBalance (stock count) for non-zero items while Tally emits
    item NAME as the STOCKITEM attribute; zero rates, values, or master UDFs are fetched.
    """
    company_filter = (
        f"<SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY>"
        if company_name
        else ""
    )
    return f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>StockUndoFastCollection</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        {company_filter}
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="StockUndoFastCollection" ISMODIFY="No">
            <TYPE>StockItem</TYPE>
            <FETCH>ClosingBalance</FETCH>
            <FILTER>NonZeroClosing</FILTER>
          </COLLECTION>
          <SYSTEM TYPE="Formulae" NAME="NonZeroClosing">Not $$IsEmpty:$ClosingBalance</SYSTEM>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""


def build_stock_item_details_request(item_name: str, company_name: Optional[str] = None) -> str:
    """
    Read-only request for a specific Stock Item's closing quantity ONLY using TDL Collection.
    Guarantees no financial data or mutation.
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
              <NATIVEMETHOD>ClosingBalance</NATIVEMETHOD>
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

