#!/usr/bin/env python3
"""
STOCK UNDO! - TallyPrime Connectivity & Strictly Non-Financial Verification Script
Strictly Read-Only & Non-Financial: Requests ONLY stock quantities (no rates or values).

Usage:
  python test_tally_connectivity.py
  python test_tally_connectivity.py --pc1 100.123.59.93:9000 --pc2 100.101.152.68:9000
  python test_tally_connectivity.py --model "FORMENTY LED FMTY -FM55UHDQTVDXB5 GOOGLE Q LED TV VELORA"
"""

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.tally.xml_parser import parse_companies, parse_stock_summary
from app.tally.xml_templates import (
    build_company_list_request,
    build_fast_stock_collection_request,
    build_stock_summary_request,
)


XML_COMPANY_LIST = build_company_list_request()


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

    companies = parse_companies(resp_xml)
    result["open_companies"] = companies
    print(f"  [3] Open Tally Company:  {companies if companies else 'None active / Default'}")

    # Step 3: Quantity-Only Collection Export (never requests or parses rates/values)
    company = companies[0] if companies else None
    fast_xml = build_fast_stock_collection_request(company)
    s_ok, s_xml, s_latency = post_tally_xml(host, port, fast_xml, timeout=6.0)
    if s_ok and "<COLLECTION" not in s_xml and "<STOCKITEM" not in s_xml and "<DSPACCNAME" not in s_xml:
        summary_xml = build_stock_summary_request(company)
        s_ok, s_xml, s_latency = post_tally_xml(host, port, summary_xml, timeout=6.0)

    if s_ok:
        stock_data = parse_stock_summary(s_xml)
        print(f"  [4] Stock Quantity Only: [PASS] Found {len(stock_data)} items ({s_latency:.1f}ms)")

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
        print(f"  [4] Stock Quantity Only: [FAIL] {s_xml}")
        result["error"] = f"Stock quantity query failed: {s_xml}"

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

