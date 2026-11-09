"""
STOCK UNDO! - PC 2 TallyPrime Adapter (Tailscale Remote)
"""

from typing import Any, Dict, List, Optional, Tuple
from app.config import settings
from app.tally.tally_client import TallyClient


class TallyPC2Adapter:
    """Handles communication with TallyPrime on PC 2 over the encrypted Tailscale mesh."""

    @classmethod
    async def check_health(cls) -> Tuple[bool, float, List[str], Optional[str]]:
        return await TallyClient.probe_connection(
            settings.PC2_HOST,
            settings.PC2_PORT,
            timeout=settings.TALLY_TIMEOUT_SECONDS
        )

    @classmethod
    async def fetch_stock_with_status(
        cls,
        company_name: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Dict[str, Any]], float, Optional[str]]:
        return await TallyClient.get_stock_quantities_with_meta(
            settings.PC2_HOST,
            settings.PC2_PORT,
            company_name=company_name,
            timeout=settings.TALLY_TIMEOUT_SECONDS
        )

    @classmethod
    async def fetch_stock_summary(
        cls,
        company_name: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Dict[str, Any]], Optional[str]]:
        return await TallyClient.get_stock_quantities(
            settings.PC2_HOST,
            settings.PC2_PORT,
            company_name=company_name,
            timeout=settings.TALLY_TIMEOUT_SECONDS
        )

