"""
STOCK UNDO! - Asynchronous Tally Client
Provides strictly read-only XML transport, connection testing, and fault isolation.
"""

import asyncio
import logging
import socket
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.tally.xml_parser import parse_companies, parse_stock_summary
from app.tally.xml_templates import build_company_list_request, build_stock_summary_request


logger = logging.getLogger("stock_undo.tally_client")


class TallyClient:
    """Async client communicating with TallyPrime via its local or Tailscale XML interface."""

    @staticmethod
    def test_tcp_port(host: str, port: int, timeout: float = 1.5) -> Tuple[bool, float, Optional[str]]:
        """Quick synchronous TCP socket probe."""
        start = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            latency_ms = (time.perf_counter() - start) * 1000.0
            s.close()
            return True, latency_ms, None
        except socket.timeout:
            return False, 0.0, "Connection timed out"
        except ConnectionRefusedError:
            return False, 0.0, "Connection refused (Tally service not running on port)"
        except Exception as e:
            return False, 0.0, str(e)
        finally:
            try:
                s.close()
            except Exception:
                pass

    @classmethod
    async def post_xml(
        cls,
        host: str,
        port: int,
        xml_payload: str,
        timeout: float = 3.5
    ) -> Tuple[bool, str, float, Optional[str]]:
        """
        Sends a read-only XML payload to Tally via HTTP POST.
        Returns: (success, response_text, latency_ms, error)
        """
        url = f"http://{host}:{port}/"
        headers = {
            "Content-Type": "application/xml; charset=utf-8",
            "Accept": "application/xml, text/xml",
        }

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    url,
                    content=xml_payload.encode("utf-8"),
                    headers=headers
                )
                latency_ms = (time.perf_counter() - start) * 1000.0
                if resp.status_code == 200:
                    return True, resp.text, latency_ms, None
                else:
                    return False, "", latency_ms, f"HTTP status {resp.status_code}"
        except httpx.ConnectTimeout:
            return False, "", (time.perf_counter() - start) * 1000.0, "Connection timed out"
        except httpx.ConnectError:
            return False, "", (time.perf_counter() - start) * 1000.0, "Connection refused (Tally is closed)"
        except Exception as e:
            return False, "", (time.perf_counter() - start) * 1000.0, str(e)

    @classmethod
    async def probe_connection(
        cls,
        host: str,
        port: int,
        timeout: float = 3.0
    ) -> Tuple[bool, float, List[str], Optional[str]]:
        """
        Tests if Tally is online and retrieves open company list.
        First does a fast TCP test, then an XML probe.
        """
        loop = asyncio.get_running_loop()
        tcp_ok, latency, err = await loop.run_in_executor(None, cls.test_tcp_port, host, port, 1.2)
        if not tcp_ok:
            return False, 0.0, [], err

        # Port is open; verify with read-only XML query
        xml_req = build_company_list_request()
        ok, resp_text, latency, xml_err = await cls.post_xml(host, port, xml_req, timeout=timeout)
        if not ok:
            return False, latency, [], xml_err

        companies = parse_companies(resp_text)
        return True, latency, companies, None

    @classmethod
    async def get_stock_quantities(
        cls,
        host: str,
        port: int,
        company_name: Optional[str] = None,
        timeout: float = 4.0
    ) -> Tuple[bool, Dict[str, Dict[str, Any]], Optional[str]]:
        """
        Retrieves all stock quantities from Tally's item-wise Stock Summary.
        Returns: (success, {item_name: {closing_qty, unit, raw}}, error)
        """
        xml_req = build_stock_summary_request(company_name)
        ok, resp_text, _, err = await cls.post_xml(host, port, xml_req, timeout=timeout)
        if not ok:
            return False, {}, err

        items = parse_stock_summary(resp_text)
        return True, items, None

