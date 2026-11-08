#!/usr/bin/env python3
"""
STOCK UNDO! - TallyPrime Connectivity & Read-Only Stock Verification Script
Strictly Read-Only: Only performs XML data export requests. Never modifies Tally data.

Usage:
  python test_tally_connectivity.py
  python test_tally_connectivity.py --pc1 127.0.0.1:9000 --pc2 100.101.152.68:9000
  python test_tally_connectivity.py --model "FORMENTY LED FMTY -FM55UHDQTVDXB5 GOOGLE Q LED TV VELORA"
"""

import argparse
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Strict Read-Only Tally XML Request Templates
# ---------------------------------------------------------------------------

XML_COMPANY_LIST = """<ENVELOPE>
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
    company_tag = f"<SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY>" if company_name else ""
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
          {company_tag}
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

def build_single_item_request(model_name: str, company_name: Optional[str] = None) -> str:
    company_tag = f"<SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY>" if company_name else ""
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
          {company_tag}
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def escape_xml(text: Optional[str]) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def sanitize_tally_xml(xml_content: str) -> str:
    if not xml_content:
        return ""
    # Strip illegal XML entity references &#0; through &#31;
    s = re.sub(r'&#(?:[0-8]|1[1-2]|1[4-9]|[2-3][0-9]);', '', xml_content)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
    return s


# ---------------------------------------------------------------------------
# Low-level TCP & HTTP Probe
# ---------------------------------------------------------------------------

def test_tcp_port(host: str, port: int, timeout: float = 2.0) -> Tuple[bool, str]:
    """Test raw TCP connection to the host:port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        start = time.perf_counter()
        s.connect((host, port))
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        s.close()
        return True, f"TCP port open ({elapsed_ms:.1f}ms)"
    except socket.timeout:
        return False, "Connection timed out"
    except ConnectionRefusedError:
        return False, "Connection refused (Tally service not running on port)"
    except OSError as e:
        return False, f"Socket error: {e}"


def post_tally_xml(host: str, port: int, xml_payload: str, timeout: float = 4.0) -> Tuple[bool, str, float]:
    """Send read-only XML request to Tally via HTTP POST."""
    url = f"http://{host}:{port}/"
    headers = {
        "Content-Type": "application/xml; charset=utf-8",
        "Accept": "application/xml, text/xml",
    }
    req = urllib.request.Request(
        url,
        data=xml_payload.encode("utf-8"),
        headers=headers,
        method="POST"
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode("utf-8", errors="replace")
            latency_ms = (time.perf_counter() - start) * 1000.0
            return True, content, latency_ms
    except urllib.error.URLError as e:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return False, str(e.reason), latency_ms
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return False, str(e), latency_ms


def parse_companies_from_xml(xml_content: str) -> List[str]:
    """Extract open company names from Tally XML response."""
    companies = []
    if not xml_content:
        return companies
    clean_xml = sanitize_tally_xml(xml_content)
    try:
        root = ET.fromstring(clean_xml)
        for comp in root.iter("COMPANY"):
            name = comp.attrib.get("NAME")
            if not name:
                name_elem = comp.find("NAME")
                if name_elem is not None and name_elem.text:
                    name = name_elem.text.strip()
            if name and name not in companies:
                companies.append(name)
        # Check SVCURRENTCOMPANY tag
        cur = root.findtext(".//SVCURRENTCOMPANY")
        if cur and cur.strip() and cur.strip() not in companies:
            companies.insert(0, cur.strip())
    except Exception:
        pass
    return companies


def parse_stock_summary(xml_content: str) -> Dict[str, Dict[str, Any]]:
    """
    Parses item-wise Stock Summary from Tally.
    Returns: { "item name": { "closing_qty": float, "unit": str } }
    """
    items = {}
    if not xml_content:
        return items
    clean_xml = sanitize_tally_xml(xml_content)
    try:
        root = ET.fromstring(clean_xml)
        current_name = None
        for elem in root:
            tag = elem.tag.upper().split("}")[-1]
            if tag == "DSPACCNAME":
                disp = elem.find("DSPDISPNAME")
                if disp is not None and disp.text:
                    current_name = disp.text.strip()
            elif tag == "DSPSTKINFO" and current_name:
                cl = elem.find(".//DSPCLQTY")
                qty_str = cl.text.strip() if (cl is not None and cl.text) else "0"
                # Parse quantity number and unit
                # e.g., "12 Nos" or "100.00 Kg"
                m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*(.*)", qty_str)
                qty = float(m.group(1)) if m else 0.0
                unit = m.group(2).strip() if (m and m.group(2)) else "Nos"
                items[current_name] = {
                    "closing_qty": qty,
                    "unit": unit,
                    "raw": qty_str
                }
                current_name = None
    except Exception as e:
        pass
    return items


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

def run_diagnostic(name: str, host: str, port: int, test_models: List[str]) -> Dict[str, Any]:
    print(f"\n{'='*60}")
    print(f"[*] Testing {name}: {host}:{port}")
    print(f"{'='*60}")

    result = {
        "name": name,
        "host": host,
        "port": port,
        "tcp_open": False,
        "http_ok": False,
        "latency_ms": 0.0,
        "open_companies": [],
        "models_checked": {},
        "error": None
    }

    # Step 1: Raw TCP probe
    tcp_ok, tcp_msg = test_tcp_port(host, port, timeout=2.5)
    result["tcp_open"] = tcp_ok
    print(f"  [1] TCP Socket Probe:    {'[PASS]' if tcp_ok else '[FAIL]'} -> {tcp_msg}")
    if not tcp_ok:
        result["error"] = tcp_msg
        return result

    # Step 2: Read-Only XML Company Probe
    http_ok, resp_xml, latency = post_tally_xml(host, port, XML_COMPANY_LIST, timeout=4.0)
    result["http_ok"] = http_ok
    result["latency_ms"] = latency
    print(f"  [2] Read-Only XML HTTP:  {'[PASS]' if http_ok else '[FAIL]'} -> {latency:.1f}ms response")
    if not http_ok:
        result["error"] = f"HTTP request failed: {resp_xml}"
        return result

    companies = parse_companies_from_xml(resp_xml)
    result["open_companies"] = companies
    print(f"  [3] Open Tally Company:  {companies if companies else 'None active / Default'}")

    # Step 3: Stock Summary Export
    company = companies[0] if companies else None
    summary_xml = build_stock_summary_request(company)
    s_ok, s_xml, s_latency = post_tally_xml(host, port, summary_xml, timeout=6.0)
    if s_ok:
        stock_data = parse_stock_summary(s_xml)
        print(f"  [4] Stock Summary Probe: [PASS] Found {len(stock_data)} items ({s_latency:.1f}ms)")

        for model in test_models:
            matched = False
            for item_name, details in stock_data.items():
                if model.strip().lower() == item_name.strip().lower() or model.strip().lower() in item_name.strip().lower():
                    result["models_checked"][model] = {
                        "status": "Available" if details["closing_qty"] > 0 else "Out of Stock",
                        "stock": details["closing_qty"],
                        "unit": details["unit"],
                        "matched_item": item_name
                    }
                    matched = True
                    break
            if not matched:
                result["models_checked"][model] = {
                    "status": "Model Not Found",
                    "stock": 0,
                    "unit": "-",
                    "matched_item": None
                }
    else:
        print(f"  [4] Stock Summary Probe: [FAIL] {s_xml}")
        result["error"] = f"Stock summary query failed: {s_xml}"

    return result


def main():
    parser = argparse.ArgumentParser(description="STOCK UNDO! Tally Connectivity Diagnostic")
    parser.add_argument("--pc1", default="127.0.0.1:9000", help="PC 1 Tally host:port (default: 127.0.0.1:9000)")
    parser.add_argument("--pc2", default="100.101.152.68:9000", help="PC 2 Tally host:port via Tailscale (default: 100.101.152.68:9000)")
    parser.add_argument("--model", action="append", help="Specific model to check (can be specified multiple times)")
    parser.add_argument("--json", action="store_true", help="Output diagnostic results as JSON")
    args = parser.parse_args()

    # Default whitelist models from catalog
    sample_models = args.model or [
        "FORMENTY LED FMTY -FM55UHDQTVDXB5 GOOGLE Q LED TV VELORA",
        "FORMENTY AC FMTY Split Inverter FRIO 1.0T3*-Fm12ininv3froed",
        "CARRIER AC MIDEA 12K SANTIS NXG (V-PRO) DLX INV 1 TON 3*",
        "GENERAL ASSGG24CGWA-B 2T INV AC 4*",
        "ROCKWELL GFR1210F"
    ]

    pc1_host, pc1_port = args.pc1.split(":")
    pc2_host, pc2_port = args.pc2.split(":")

    print("\n" + "="*60)
    print(" STOCK UNDO! - TallyPrime Independent Connectivity Test")
    print(" Tagline: 'Check stock before you call the godown!'")
    print("="*60)

    res_pc1 = run_diagnostic("Tally PC 1 (Local)", pc1_host, int(pc1_port), sample_models)
    res_pc2 = run_diagnostic("Tally PC 2 (Tailscale Remote)", pc2_host, int(pc2_port), sample_models)

    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60)
    print(f" PC 1 ({args.pc1}): {'ONLINE' if res_pc1['http_ok'] else 'OFFLINE'} - {res_pc1.get('error') or 'OK'}")
    print(f" PC 2 ({args.pc2}): {'ONLINE' if res_pc2['http_ok'] else 'OFFLINE'} - {res_pc2.get('error') or 'OK'}")
    print("="*60)

    if args.json:
        print("\nJSON Output:")
        print(json.dumps({"pc1": res_pc1, "pc2": res_pc2}, indent=2))

if __name__ == "__main__":
    main()

