"""
STOCK UNDO! - Stock Aggregation Service
Enforces whitelist filtering, concurrent dual-source retrieval, and TTL caching.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
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

    @classmethod
    def get_whitelist(cls) -> List[str]:
        """Returns the list of permitted whitelist models."""
        return settings.get_whitelist()

    @classmethod
    def normalize_model_name(cls, name: str) -> str:
        """Normalizes model names for tolerant case-insensitive matching."""
        if not name:
            return ""
        # Collapse multiple spaces and lower-case
        return " ".join(name.strip().lower().split())

    @classmethod
    async def get_connection_status(cls) -> Tuple[TallyConnectionStatus, TallyConnectionStatus]:
        """Checks connectivity to PC 1 and PC 2 independently in parallel."""
        now_str = datetime.now(timezone.utc).isoformat()

        pc1_task = TallyPC1Adapter.check_health()
        pc2_task = TallyPC2Adapter.check_health()

        (pc1_res, pc2_res) = await asyncio.gather(pc1_task, pc2_task, return_exceptions=True)

        # Process PC 1
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

        # Process PC 2
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

        return pc1_status, pc2_status

    @classmethod
    def _match_stock_for_model(
        cls,
        model: str,
        tally_items: Dict[str, Dict[str, Any]],
        source_label: str,
        is_source_online: bool,
    ) -> StockItemResponse:
        """Matches a single whitelist model against Tally's extracted stock summary."""
        now_str = datetime.now(timezone.utc).isoformat()

        if not is_source_online:
            return StockItemResponse(
                model=model,
                available_stock=0.0,
                unit="-",
                source=source_label,
                status=StockStatus.OFFLINE,
                closing_balance_display="Offline",
                last_updated=now_str,
            )

        norm_model = cls.normalize_model_name(model)

        # 1. Exact match
        for item_name, data in tally_items.items():
            if cls.normalize_model_name(item_name) == norm_model:
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
                    last_updated=now_str,
                )

        # 2. Substring match
        for item_name, data in tally_items.items():
            norm_item = cls.normalize_model_name(item_name)
            if norm_model in norm_item or norm_item in norm_model:
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
                    last_updated=now_str,
                )

        # 3. Model Not Found in Tally
        return StockItemResponse(
            model=model,
            available_stock=0.0,
            unit="-",
            source=source_label,
            status=StockStatus.NOT_FOUND,
            closing_balance_display="Not Found",
            last_updated=now_str,
        )

    @classmethod
    async def get_stock_for_source(
        cls,
        source: str,  # "pc1" or "pc2"
        force_refresh: bool = False,
    ) -> List[StockItemResponse]:
        """Retrieves stock for a specific PC, discovering all live models from Tally."""
        cache_key = f"stock_{source}"
        now = time.time()

        if not force_refresh and cache_key in cls._cache:
            cached_time, cached_data = cls._cache[cache_key]
            if now - cached_time < settings.CACHE_TTL_SECONDS:
                return cached_data

        whitelist = cls.get_whitelist()
        adapter = TallyPC1Adapter if source == "pc1" else TallyPC2Adapter
        source_label = settings.PC1_LABEL if source == "pc1" else settings.PC2_LABEL

        ok, items_dict, _ = await adapter.fetch_stock_summary()

        # Combine configured whitelist with ALL live models discovered from Tally
        all_models_set = set(whitelist)
        if ok and items_dict:
            all_models_set.update(items_dict.keys())

        # Sort alphabetically (case-insensitive)
        all_models = sorted(list(all_models_set), key=lambda x: x.strip().lower())

        results: List[StockItemResponse] = []
        for model in all_models:
            res = cls._match_stock_for_model(model, items_dict if ok else {}, source_label, ok)
            results.append(res)

        cls._cache[cache_key] = (now, results)
        return results

    @classmethod
    async def get_all_stock(
        cls,
        force_refresh: bool = False,
    ) -> StockSummaryResponse:
        """Retrieves and aggregates stock for all models across PC 1 and PC 2."""
        now = time.time()
        cache_key = "stock_all"

        if not force_refresh and cache_key in cls._cache:
            cached_time, cached_summary = cls._cache[cache_key]
            if now - cached_time < settings.CACHE_TTL_SECONDS:
                return cached_summary

        # Check status and fetch data concurrently
        pc1_status_task = cls.get_connection_status()
        pc1_stock_task = cls.get_stock_for_source("pc1", force_refresh=force_refresh)
        pc2_stock_task = cls.get_stock_for_source("pc2", force_refresh=force_refresh)

        (conn_statuses, pc1_items, pc2_items) = await asyncio.gather(
            pc1_status_task, pc1_stock_task, pc2_stock_task
        )
        pc1_status, pc2_status = conn_statuses

        # Map by model name
        pc1_map = {item.model: item for item in pc1_items}
        pc2_map = {item.model: item for item in pc2_items}

        # Combine all models across both PCs and whitelist
        all_models_set = set(pc1_map.keys()) | set(pc2_map.keys()) | set(cls.get_whitelist())
        all_models = sorted(list(all_models_set), key=lambda x: x.strip().lower())

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

        cls._cache[cache_key] = (now, summary)
        return summary

    @classmethod
    async def search_stock(
        cls,
        query: str,
        source: Optional[str] = None,
    ) -> List[StockItemResponse]:
        """
        Searches stock strictly within permitted whitelist models.
        """
        summary = await cls.get_all_stock()
        if not query or not query.strip():
            return summary.items

        norm_q = cls.normalize_model_name(query)
        return [
            item for item in summary.items
            if norm_q in cls.normalize_model_name(item.model)
        ]

