"""
STOCK UNDO! - PC 1 TallyPrime Adapter (Localhost)
"""

from typing import Any, Dict, List, Optional, Tuple
from app.config import settings
from app.tally.tally_client import TallyClient


class TallyPC1Adapter:
    """Handles communication with TallyPrime on PC 1."""

    @classmethod
    async def check_health(cls) -> Tuple[bool, float, List[str], Optional[str]]:
        return await TallyClient.probe_connection(
            settings.PC1_HOST,
            settings.PC1_PORT,
            timeout=settings.TALLY_TIMEOUT_SECONDS
        )

    @classmethod
    async def fetch_stock_summary(
        cls,
        company_name: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Dict[str, Any]], Optional[str]]:
        return await TallyClient.get_stock_quantities(
            settings.PC1_HOST,
            settings.PC1_PORT,
            company_name=company_name,
            timeout=settings.TALLY_TIMEOUT_SECONDS
        )

