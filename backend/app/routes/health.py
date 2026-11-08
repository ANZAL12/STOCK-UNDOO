"""
STOCK UNDO! - Health and Tally Status Routes
"""

from datetime import datetime, timezone
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.models.stock import HealthResponse, TallyConnectionStatus
from app.services.stock_service import StockService


router = APIRouter(tags=["Health & Status"])


@router.get("/health", response_model=HealthResponse)
async def check_health() -> HealthResponse:
    """Check backend health and high-level Tally readiness."""
    pc1_status, pc2_status = await StockService.get_connection_status()

    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        tagline=settings.TAGLINE,
        version=settings.VERSION,
        server_time=datetime.now(timezone.utc).isoformat(),
        tally_pc1_online=pc1_status.online,
        tally_pc2_online=pc2_status.online,
    )


@router.get("/tally/status", response_model=Dict[str, TallyConnectionStatus])
async def get_tally_status() -> Dict[str, TallyConnectionStatus]:
    """Check connectivity to both Tally installations independently."""
    pc1_status, pc2_status = await StockService.get_connection_status()
    return {
        "pc1": pc1_status,
        "pc2": pc2_status,
    }

