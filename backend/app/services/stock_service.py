"""
STOCK UNDO! - Stock Aggregation Service
Enforces whitelist filtering, concurrent dual-source retrieval, and TTL caching.
"""

import asyncio
from datetime import datetime, timezone
import logging
import re
import time
import weakref
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.stock import (
    StockItemResponse,
    StockStatus,
    StockSummaryResponse,
    TallyConnectionStatus,
)
from app.tally.tally_pc1 import TallyPC1Adapter
from app.tally.tally_pc2 import TallyPC2Adapter


logger = logging.getLogger("stock_undo.stock_service")


class StockService:
    """Core service for managing stock retrieval from PC 1 and PC 2."""

    # In-memory cache: { "cache_key": (timestamp, data) }
    _cache: Dict[str, Tuple[float, Any]] = {}
    _locks_by_loop: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        lock = cls._locks_by_loop.get(loop)
        if lock is None:
            lock = asyncio.Lock()
            cls._locks_by_loop[loop] = lock
        return lock

    @classmethod
    def get_whitelist(cls) -> List[str]:
        """Returns the list of permitted whitelist models."""
        return settings.get_whitelist()

    @classmethod
    def normalize_model_name(cls, name: str) -> str:
        """Normalizes model names for tolerant case-insensitive matching."""
        if not name:
            return ""
        return " ".join(name.strip().lower().split())

    @classmethod
    async def get_connection_status(cls) -> Tuple[TallyConnectionStatus, TallyConnectionStatus]:
        """Checks connectivity to PC 1 and PC 2 independently in parallel (with short 4s cache)."""
        now = time.time()
        cached = cls._cache.get("conn_status")
        if cached and (now - cached[0]) < 4.0:
            return cached[1]

        now_str = datetime.now(timezone.utc).isoformat()
        pc1_task = TallyPC1Adapter.check_health()
        pc2_task = TallyPC2Adapter.check_health()

        (pc1_res, pc2_res) = await asyncio.gather(pc1_task, pc2_task, return_exceptions=True)

        if isinstance(pc1_res, Exception):
            pc1_status = TallyConnectionStatus(
                pc="pc1",
                label=settings.PC1_LABEL,
                online=False,
                latency_ms=0.0,
                open_company=None,
                last_checked=now_str,
                error=str(pc1_res),
            )
        else:
            ok, latency, companies, err = pc1_res
            pc1_status = TallyConnectionStatus(
                pc="pc1",
                label=settings.PC1_LABEL,
                online=ok,
                latency_ms=round(latency, 1),
                open_company=companies[0] if companies else None,
                last_checked=now_str,
                error=err,
            )

        if isinstance(pc2_res, Exception):
            pc2_status = TallyConnectionStatus(
                pc="pc2",
                label=settings.PC2_LABEL,
                online=False,
                latency_ms=0.0,
                open_company=None,
                last_checked=now_str,
                error=str(pc2_res),
            )
        else:
            ok, latency, companies, err = pc2_res
            pc2_status = TallyConnectionStatus(
                pc="pc2",
                label=settings.PC2_LABEL,
                online=ok,
                latency_ms=round(latency, 1),
                open_company=companies[0] if companies else None,
                last_checked=now_str,
                error=err,
            )

        res_pair = (pc1_status, pc2_status)
        cls._cache["conn_status"] = (time.time(), res_pair)
        return res_pair

    @classmethod
    def _match_stock_for_model(
        cls,
        model: str,
        tally_items: Dict[str, Dict[str, Any]],
        source_label: str,
        is_source_online: bool,
        norm_lookup: Optional[Dict[str, Dict[str, Any]]] = None,
        now_str: Optional[str] = None,
    ) -> StockItemResponse:
        """Matches a single whitelist model against Tally's extracted stock summary in O(1) average time."""
        ts = now_str or datetime.now(timezone.utc).isoformat()

        if not is_source_online:
            return StockItemResponse(
                model=model,
                available_stock=0.0,
                unit="-",
                source=source_label,
                status=StockStatus.OFFLINE,
                closing_balance_display="Offline",
                last_updated=ts,
            )

        # 0. O(1) direct raw-key lookup
        data = tally_items.get(model)
        if data is None:
            norm_model = cls.normalize_model_name(model)
            # 1. O(1) normalized dictionary lookup
            if norm_lookup is not None:
                data = norm_lookup.get(norm_model)
                if data is None:
                    # 2. Fallback substring match only for unmatched whitelist entries
                    for norm_item, item_data in norm_lookup.items():
                        if norm_model in norm_item or norm_item in norm_model:
                            data = item_data
                            break
            else:
                for item_name, item_data in tally_items.items():
                    norm_item = cls.normalize_model_name(item_name)
                    if norm_item == norm_model or norm_model in norm_item or norm_item in norm_model:
                        data = item_data
                        break

        if data is not None:
            qty = data["closing_qty"]
            unit = data["unit"]
            status = StockStatus.AVAILABLE if qty > 0 else StockStatus.OUT_OF_STOCK
            return StockItemResponse(
                model=model,
                available_stock=qty,
                unit=unit,
                source=source_label,
                status=status,
                closing_balance_display=f"{int(qty) if qty.is_integer() else qty} {unit}",
                last_updated=ts,
            )

        # 3. Model Not Found in Tally
        return StockItemResponse(
            model=model,
            available_stock=0.0,
            unit="-",
            source=source_label,
            status=StockStatus.NOT_FOUND,
            closing_balance_display="Not Found",
            last_updated=ts,
        )

    @classmethod
    async def _fetch_source_with_status(
        cls,
        source: str,
        whitelist: List[str],
        force_refresh: bool = False,
    ) -> Tuple[List[StockItemResponse], TallyConnectionStatus]:
        """Retrieves stock and derives live connection status in a single Tally query (no redundant List of Companies)."""
        cache_key = f"stock_{source}"
        status_key = f"status_{source}"
        now = time.time()
        now_str = datetime.now(timezone.utc).isoformat()

        if not force_refresh and cache_key in cls._cache and status_key in cls._cache:
            cached_time, cached_data = cls._cache[cache_key]
            _, cached_status = cls._cache[status_key]
            if now - cached_time < settings.CACHE_TTL_SECONDS:
                return cached_data, cached_status

        adapter = TallyPC1Adapter if source == "pc1" else TallyPC2Adapter
        source_label = settings.PC1_LABEL if source == "pc1" else settings.PC2_LABEL

        ok, items_dict, latency_ms, err = await adapter.fetch_stock_with_status()

        conn_status = TallyConnectionStatus(
            pc=source,
            label=source_label,
            online=ok,
            latency_ms=round(latency_ms, 1),
            open_company=None,
            last_checked=now_str,
            error=err,
        )

        # Build O(N) normalized lookup map once instead of O(N^2) per model
        norm_lookup = (
            {cls.normalize_model_name(k): v for k, v in items_dict.items()}
            if (ok and items_dict)
            else {}
        )

        all_models_set = set(whitelist)
        if ok and items_dict:
            all_models_set.update(items_dict.keys())

        all_models = sorted(all_models_set, key=lambda x: x.strip().lower())

        results = [
            cls._match_stock_for_model(
                model,
                items_dict if ok else {},
                source_label,
                ok,
                norm_lookup=norm_lookup,
                now_str=now_str,
            )
            for model in all_models
        ]

        done_ts = time.time()
        cls._cache[cache_key] = (done_ts, results)
        cls._cache[status_key] = (done_ts, conn_status)
        return results, conn_status

    @classmethod
    async def get_stock_for_source(
        cls,
        source: str,  # "pc1" or "pc2"
        force_refresh: bool = False,
    ) -> List[StockItemResponse]:
        """Retrieves stock for a specific PC, discovering all live models from Tally."""
        items, _ = await cls._fetch_source_with_status(
            source, cls.get_whitelist(), force_refresh=force_refresh
        )
        return items

    @classmethod
    async def get_all_stock(
        cls,
        force_refresh: bool = False,
    ) -> StockSummaryResponse:
        """
        Retrieves and aggregates stock across PC 1 and PC 2.
        Uses single-flight request coalescing + 1-query-per-PC (eliminating redundant company probes).
        """
        now = time.time()
        cache_key = "stock_all"

        if not force_refresh and cache_key in cls._cache:
            cached_time, cached_summary = cls._cache[cache_key]
            if now - cached_time < settings.CACHE_TTL_SECONDS:
                return cached_summary

        async with cls._get_lock():
            now_locked = time.time()
            # Re-check cache after acquiring lock so concurrent requests share 1 Tally call
            if cache_key in cls._cache:
                cached_time, cached_summary = cls._cache[cache_key]
                ttl = 0.8 if force_refresh else settings.CACHE_TTL_SECONDS
                if now_locked - cached_time < ttl:
                    return cached_summary

            whitelist = cls.get_whitelist()
            (pc1_res, pc2_res) = await asyncio.gather(
                cls._fetch_source_with_status("pc1", whitelist, force_refresh=True),
                cls._fetch_source_with_status("pc2", whitelist, force_refresh=True),
            )
            pc1_items, pc1_status = pc1_res
            pc2_items, pc2_status = pc2_res

            cls._cache["conn_status"] = (time.time(), (pc1_status, pc2_status))

            # Map by model name
            pc1_map = {item.model: item for item in pc1_items}
            pc2_map = {item.model: item for item in pc2_items}

            # Combine all models across both PCs and whitelist
            all_models_set = set(pc1_map.keys()) | set(pc2_map.keys()) | set(whitelist)
            all_models = sorted(all_models_set, key=lambda x: x.strip().lower())

            aggregated_items: List[StockItemResponse] = []
            now_str = datetime.now(timezone.utc).isoformat()

            available_count = 0
            out_of_stock_count = 0
            not_found_count = 0

            for model in all_models:
                i1 = pc1_map.get(model)
                i2 = pc2_map.get(model)

                # Consolidate stock across both Tally installations (seamless single-item view)
                both_offline = (
                    (not pc1_status.online or (i1 and i1.status == StockStatus.OFFLINE)) and
                    (not pc2_status.online or (i2 and i2.status == StockStatus.OFFLINE))
                )

                if both_offline:
                    item_status = StockStatus.OFFLINE
                    total_qty = 0.0
                    unit = "-"
                    disp = "Offline"
                else:
                    any_found = False
                    total_qty = 0.0
                    unit = "Nos"

                    if i1 and i1.status in (StockStatus.AVAILABLE, StockStatus.OUT_OF_STOCK):
                        total_qty += i1.available_stock
                        unit = i1.unit if i1.unit != "-" else unit
                        any_found = True

                    if i2 and i2.status in (StockStatus.AVAILABLE, StockStatus.OUT_OF_STOCK):
                        total_qty += i2.available_stock
                        unit = i2.unit if i2.unit != "-" else unit
                        any_found = True

                    if any_found:
                        if total_qty > 0:
                            item_status = StockStatus.AVAILABLE
                            available_count += 1
                        else:
                            item_status = StockStatus.OUT_OF_STOCK
                            out_of_stock_count += 1
                        disp = f"{int(total_qty) if total_qty.is_integer() else total_qty} {unit}"
                    else:
                        item_status = StockStatus.NOT_FOUND
                        not_found_count += 1
                        disp = "Not Found"

                aggregated_items.append(
                    StockItemResponse(
                        model=model,
                        available_stock=total_qty,
                        unit=unit,
                        source="Central Stock",
                        status=item_status,
                        closing_balance_display=disp,
                        last_updated=now_str,
                    )
                )

            summary = StockSummaryResponse(
                timestamp=now_str,
                pc1_status=pc1_status,
                pc2_status=pc2_status,
                items=aggregated_items,
                total_models=len(all_models),
                available_count=available_count,
                out_of_stock_count=out_of_stock_count,
                not_found_count=not_found_count,
            )

            cls._cache[cache_key] = (time.time(), summary)
            return summary

    @classmethod
    async def search_stock(
        cls,
        query: str,
        source: Optional[str] = None,
    ) -> List[StockItemResponse]:
        """
        Searches stock using flexible space-, punctuation-, and order-insensitive matching.
        """
        summary = await cls.get_all_stock()
        if not query or not query.strip():
            return summary.items

        q_lower = query.lower()
        clean_q = re.sub(r"[^a-z0-9*]+", " ", q_lower).strip()
        compact_q = re.sub(r"[^a-z0-9*]", "", q_lower)
        tokens = [t for t in clean_q.split() if t]

        if not compact_q and not tokens:
            return summary.items

        matched = []
        for item in summary.items:
            model_lower = item.model.lower()
            compact_model = re.sub(r"[^a-z0-9*]", "", model_lower)
            if compact_q and compact_q in compact_model:
                matched.append(item)
                continue
            clean_model = re.sub(r"[^a-z0-9*]+", " ", model_lower).strip()
            if tokens and all((tok in clean_model or tok in compact_model) for tok in tokens):
                matched.append(item)

        return matched

