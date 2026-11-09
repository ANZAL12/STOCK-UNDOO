"""
STOCK UNDO! - Asynchronous Tally Client
Provides strictly read-only XML transport, connection testing, and fault isolation.
"""

import asyncio
import logging
import socket
import time
import weakref
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.tally.xml_parser import parse_companies, parse_stock_summary
from app.tally.xml_templates import (
    build_company_list_request,
    build_fast_stock_collection_request,
    build_stock_summary_request,
)


logger = logging.getLogger("stock_undo.tally_client")

_FAST_STOCK_BYTES = build_fast_stock_collection_request().encode("utf-8")
_COMPANY_LIST_BYTES = build_company_list_request().encode("utf-8")
_XML_HEADERS = {
    "Content-Type": "application/xml; charset=utf-8",
    "Accept": "application/xml, text/xml",
}


class TallyClient:
    """Async client communicating with TallyPrime via its local or Tailscale XML interface."""

    _clients_by_loop: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

    @classmethod
    def _get_client(cls, timeout: float) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        client = cls._clients_by_loop.get(loop)
        if client is None or client.is_closed:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout, connect=1.2),
                limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
                headers=_XML_HEADERS,
            )
            cls._clients_by_loop[loop] = client
        return client

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
        xml_payload: str | bytes,
        timeout: float = 3.5
    ) -> Tuple[bool, str, float, Optional[str]]:
        """
        Sends a read-only XML payload to Tally via HTTP POST with connection pooling
        and a 1.2s fast connect timeout (avoids double TCP socket handshakes).
        Returns: (success, response_text, latency_ms, error)
        """
        url = f"http://{host}:{port}/"
        payload_bytes = xml_payload.encode("utf-8") if isinstance(xml_payload, str) else xml_payload

        start = time.perf_counter()
        client = cls._get_client(timeout)
        req_timeout = httpx.Timeout(timeout, connect=1.2)
        for attempt in range(2):
            try:
                resp = await client.post(url, content=payload_bytes, timeout=req_timeout)
                latency_ms = (time.perf_counter() - start) * 1000.0
                if resp.status_code == 200:
                    return True, resp.text, latency_ms, None
                return False, "", latency_ms, f"HTTP status {resp.status_code}"
            except (httpx.RemoteProtocolError, httpx.ReadError):
                # Re-open pooled connection if Tally closed an idle keep-alive socket
                if attempt == 0:
                    try:
                        await client.aclose()
                    except Exception:
                        pass
                    client = cls._get_client(timeout)
                    continue
                return False, "", (time.perf_counter() - start) * 1000.0, "Connection reset by Tally"
            except httpx.ConnectTimeout:
                return False, "", (time.perf_counter() - start) * 1000.0, "Connection timed out"
            except httpx.ConnectError:
                return False, "", (time.perf_counter() - start) * 1000.0, "Connection refused (Tally is closed)"
            except Exception as e:
                return False, "", (time.perf_counter() - start) * 1000.0, str(e)
        return False, "", (time.perf_counter() - start) * 1000.0, "Unknown transport error"

    @classmethod
    async def probe_connection(
        cls,
        host: str,
        port: int,
        timeout: float = 3.0
    ) -> Tuple[bool, float, List[str], Optional[str]]:
        """Tests if Tally is online and retrieves open company list in a single round-trip."""
        if not host or not host.strip():
            return False, 0.0, [], "Host disabled"

        ok, resp_text, latency, xml_err = await cls.post_xml(
            host, port, _COMPANY_LIST_BYTES, timeout=timeout
        )
        if not ok:
            return False, latency, [], xml_err

        companies = parse_companies(resp_text)
        return True, latency, companies, None

    @classmethod
    async def get_stock_quantities_with_meta(
        cls,
        host: str,
        port: int,
        company_name: Optional[str] = None,
        timeout: float = 4.0
    ) -> Tuple[bool, Dict[str, Dict[str, Any]], float, Optional[str]]:
        """
        High-speed stock retrieval using minimal TDL StockItem Collection query.
        Falls back to non-financial Stock Summary report only if TDL collection is unsupported.
        Returns: (success, {item_name: {closing_qty, unit}}, latency_ms, error)
        """
        if not host or not host.strip():
            return False, {}, 0.0, "Host disabled"

        payload: str | bytes = (
            _FAST_STOCK_BYTES
            if company_name is None
            else build_fast_stock_collection_request(company_name)
        )
        ok, resp_text, latency_ms, err = await cls.post_xml(host, port, payload, timeout=timeout)
        if not ok:
            return False, {}, latency_ms, err

        items = parse_stock_summary(resp_text)
        if (
            not items
            and "<COLLECTION" not in resp_text
            and "<STOCKITEM" not in resp_text
            and "<DSPACCNAME" not in resp_text
        ):
            # Fallback to rate-disabled Stock Summary report on older Tally versions if needed
            fallback_req = build_stock_summary_request(company_name)
            ok, resp_text, fb_latency, err = await cls.post_xml(host, port, fallback_req, timeout=timeout)
            latency_ms = max(latency_ms, fb_latency)
            if not ok:
                return False, {}, latency_ms, err
            items = parse_stock_summary(resp_text)

        return True, items, latency_ms, None

    @classmethod
    async def get_stock_quantities(
        cls,
        host: str,
        port: int,
        company_name: Optional[str] = None,
        timeout: float = 4.0
    ) -> Tuple[bool, Dict[str, Dict[str, Any]], Optional[str]]:
        """Backward-compatible wrapper returning (success, items_dict, error)."""
        ok, items, _, err = await cls.get_stock_quantities_with_meta(
            host, port, company_name=company_name, timeout=timeout
        )
        return ok, items, err

