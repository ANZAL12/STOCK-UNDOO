"""
STOCK UNDO! - Stock Query Routes
Strictly read-only endpoints returning quantities for permitted whitelist models only.
"""

from typing import List, Optional
from fastapi import APIRouter, Query

from app.config import settings
from app.models.stock import (
    StockItemResponse,
    StockSummaryResponse,
    WhitelistResponse,
)
from app.services.stock_service import StockService


router = APIRouter(prefix="/stock", tags=["Stock Queries"])


@router.get("/all", response_model=StockSummaryResponse)
async def get_all_stock(
    refresh: bool = Query(False, description="Bypass cache and query live Tally instances"),
) -> StockSummaryResponse:
    """Retrieve selected whitelist models from both Tally installations."""
    return await StockService.get_all_stock(force_refresh=refresh)


@router.get("/pc1", response_model=List[StockItemResponse])
async def get_pc1_stock(
    refresh: bool = Query(False, description="Bypass cache and query live PC 1"),
) -> List[StockItemResponse]:
    """Retrieve selected whitelist models exclusively from Tally 1 (Local)."""
    return await StockService.get_stock_for_source("pc1", force_refresh=refresh)


@router.get("/pc2", response_model=List[StockItemResponse])
async def get_pc2_stock(
    refresh: bool = Query(False, description="Bypass cache and query live PC 2"),
) -> List[StockItemResponse]:
    """Retrieve selected whitelist models exclusively from Tally 2 (Remote Tailscale)."""
    return await StockService.get_stock_for_source("pc2", force_refresh=refresh)


@router.get("/search", response_model=List[StockItemResponse])
async def search_stock(
    q: str = Query(..., min_length=1, description="Model query term (searches strictly within whitelist)"),
    source: Optional[str] = Query(None, description="Optional source filter: 'pc1' or 'pc2'"),
) -> List[StockItemResponse]:
    """
    Search stock exclusively within the configured model whitelist.
    Arbitrary or unwhitelisted product searches will return empty results.
    """
    return await StockService.search_stock(query=q, source=source)


@router.get("/whitelist", response_model=WhitelistResponse)
async def get_whitelist_models() -> WhitelistResponse:
    """Returns the list of authorized product models."""
    models = StockService.get_whitelist()
    return WhitelistResponse(
        total_models=len(models),
        models=models,
    )

