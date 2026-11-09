"""
STOCK UNDO! - Robust XML Parser for TallyPrime Responses.
Strictly extracts item names, closing quantities, and units.
Silently discards any financial, cost, rate, or ledger data.
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger("stock_undo.xml_parser")

# Pre-compiled patterns for high-speed, strictly quantity-only parsing
_ILLEGAL_ENTITY_RE = re.compile(r"&#(?:[0-8]|1[1-2]|1[4-9]|[2-3][0-9]);")
_QTY_RE = re.compile(r"^([+-]?\d+(?:\.\d+)?)\s*(?:([A-Za-z][A-Za-z.\s-]{0,15}?))?\s*$")
_RATE_PREFIX_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?\s*/")
_CURRENCY_LEAD_RE = re.compile(r"^(?:rs\.?|inr|usd|eur|gbp|aed|sar|₹|\$|€|£)\b|^[₹$€£]", re.IGNORECASE)
_CURRENCY_UNIT_TOKENS = frozenset({"INR", "RS", "RS.", "USD", "EUR", "GBP", "AED", "SAR", "DR", "CR"})
_NS_PREFIX_RE = re.compile(r"<([A-Za-z_][A-Za-z0-9_.-]*):[A-Za-z_]")
_CONTROL_TRANS_TABLE = str.maketrans(
    "", "", "".join(chr(c) for c in range(32) if c not in (9, 10, 13))
)


def sanitize_tally_xml(xml_content: str) -> str:
    """
    Sanitizes Tally XML output by removing illegal XML character entities
    (&#0; through &#31;), unprintable ASCII control characters, and adding
    missing xmlns:UDF namespace declarations emitted by TallyPrime TDL/Collections.
    """
    if not xml_content:
        return ""
    s = xml_content.translate(_CONTROL_TRANS_TABLE)
    if "&#" in s:
        s = _ILLEGAL_ENTITY_RE.sub("", s)
    if "<UDF:" in s and "xmlns:UDF" not in s[:300]:
        s = s.replace("<ENVELOPE>", '<ENVELOPE xmlns:UDF="TallyUDF">', 1)
    return s


def _parse_xml_root(clean_xml: str) -> ET.Element:
    """Parses XML to ElementTree root, auto-binding any undeclared Tally TDL prefixes."""
    try:
        return ET.fromstring(clean_xml)
    except ET.ParseError as err:
        if "unbound prefix" in str(err):
            prefixes = {
                p for p in _NS_PREFIX_RE.findall(clean_xml)
                if p.lower() != "xml" and f"xmlns:{p}=" not in clean_xml[:400]
            }
            if prefixes:
                ns_attrs = " ".join(f'xmlns:{p}="urn:tally-{p}"' for p in sorted(prefixes))
                patched = re.sub(r"<(ENVELOPE\b[^>]*?)>", rf"<\1 {ns_attrs}>", clean_xml, count=1)
                return ET.fromstring(patched)
        raise


def clean_node_text(node: Optional[ET.Element]) -> str:
    """Extracts and strips inner text from an XML element safely."""
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def parse_quantity_and_unit(qty_str: str) -> Tuple[float, str]:
    """
    Strictly extracts numeric closing quantity and unit of measure ONLY:
      "14 Nos"                      -> (14.0, "Nos")
      "-2 Box"                      -> (-2.0, "Box")
      "1,250.50 Kg"                 -> (1250.5, "Kg")
      "1 Nos =  2.00 NA"            -> (1.0, "Nos")   (strips alternate-unit tail)
      "14 Nos @ 15000/Nos = 210000" -> (14.0, "Nos")   (strips any rate/value tail)
      "15000/Nos" / "Rs. 500"       -> (0.0, "Nos")    (rejects rates & currency)
    """
    if not qty_str:
        return 0.0, "Nos"

    cleaned = qty_str.replace(",", "").strip() if "," in qty_str else qty_str.strip()
    if not cleaned:
        return 0.0, "Nos"

    # Reject pure rate ("1500/Nos") or currency ("Rs. 500", "₹ 1500") strings immediately
    if _CURRENCY_LEAD_RE.match(cleaned) or _RATE_PREFIX_RE.match(cleaned):
        return 0.0, "Nos"

    # Strip any rate/value/alternate-unit suffix (@ rate, = value/alt, (note), /rate)
    for sep in ("@", "=", "(", "[", ";", "/"):
        if sep in cleaned:
            cleaned = cleaned.split(sep, 1)[0].strip()

    if not cleaned:
        return 0.0, "Nos"

    match = _QTY_RE.match(cleaned)
    if match:
        try:
            qty = float(match.group(1))
            raw_unit = (match.group(2) or "").strip(" .-")
            if raw_unit.upper() in _CURRENCY_UNIT_TOKENS:
                return 0.0, "Nos"
            unit = "Nos" if not raw_unit or raw_unit.upper() == "NA" else raw_unit
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
        root = _parse_xml_root(clean_xml)

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
    Strictly extracts model name, numeric closing quantity, and unit ONLY
    from Tally XML stock responses (fast TDL Collection OR Stock Summary Report).
    Never reads or stores rates, prices, amounts, closing values, or raw XML text.
    Returns:
      {
         "FORMENTY LED FMTY -FM55UHDQTVDXB5": {
             "closing_qty": 14.0,
             "unit": "Nos"
         }
      }
    """
    items: Dict[str, Dict[str, Any]] = {}
    if not xml_content or not xml_content.strip():
        return items

    clean_xml = sanitize_tally_xml(xml_content)
    try:
        root = _parse_xml_root(clean_xml)

        # Fast path 1: TDL Collection response (<BODY><DATA><COLLECTION><STOCKITEM NAME="...">)
        collection = root.find("./BODY/DATA/COLLECTION")
        if collection is not None:
            for si in collection:
                tag = si.tag.upper().split("}")[-1]
                if tag not in ("STOCKITEM", "ITEM"):
                    continue
                name = si.attrib.get("NAME") or clean_node_text(si.find("NAME"))
                if not name:
                    continue
                cl = si.find("CLOSINGBALANCE")
                qty_text = clean_node_text(cl) if cl is not None else "0 Nos"
                qty, unit = parse_quantity_and_unit(qty_text)
                items[name.strip()] = {
                    "closing_qty": qty,
                    "unit": unit,
                }
            if items:
                return items

        # Fast path 2: Stock Summary Report (<DSPACCNAME> + <DSPSTKINFO>, ignores DSPCLRATE/DSPCLAMTA)
        current_item_name: Optional[str] = None
        for elem in root:
            tag = elem.tag.upper().split("}")[-1]
            if tag == "DSPACCNAME":
                disp = elem.find("DSPDISPNAME")
                if disp is not None and disp.text:
                    current_item_name = disp.text.strip()
            elif tag == "DSPSTKINFO" and current_item_name:
                cl = elem.find(".//DSPCLQTY")
                qty_text = clean_node_text(cl) if cl is not None else "0 Nos"
                qty, unit = parse_quantity_and_unit(qty_text)
                items[current_item_name] = {
                    "closing_qty": qty,
                    "unit": unit,
                }
                current_item_name = None

        # Fallback: Scan any nested <STOCKITEM> elements if present
        if not items:
            for si in root.iter():
                tag = si.tag.upper().split("}")[-1]
                if tag in ("STOCKITEM", "ITEM"):
                    name = si.attrib.get("NAME") or clean_node_text(si.find("NAME"))
                    if not name:
                        continue
                    cl = si.find("CLOSINGBALANCE")
                    qty_text = clean_node_text(cl) if cl is not None else "0 Nos"
                    qty, unit = parse_quantity_and_unit(qty_text)
                    items[name.strip()] = {
                        "closing_qty": qty,
                        "unit": unit,
                    }

    except Exception as e:
        logger.warning(f"Error parsing Tally stock summary: {e}")

    return items

