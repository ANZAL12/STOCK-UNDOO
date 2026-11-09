import json
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent

# Default Whitelist Models
DEFAULT_WHITELIST = [
    "FORMENTY LED FMTY -FM55UHDQTVDXB5 GOOGLE Q LED TV VELORA",
    "FORMENTY AC FMTY Split Inverter FRIO 1.0T3*-Fm12ininv3froed",
    "CARRIER AC MIDEA 12K SANTIS NXG (V-PRO) DLX INV 1 TON 3*",
    "CARRIER CARRIER AC 12K XCEL EDGE GXI INV AC 5*",
    "GENERAL ASSGG24CGWA-B 2T INV AC 4*",
    "GENERAL ASGG 24 CPAB-B 3*",
    "GENERAL ASGG 22CNWA-B 1.8T INV AC 3*",
    "GENERAL ASGG 18 CKWA-B 1.5T INV AC 3*",
    "ROCKWELL GFR1210F",
    "ROCKWELL GFR 450 DDUC-5S",
    "ROCKWELL GFR 550 DDUC5S",
    "ROCKWELL GFR 550 DDUCSS5S",
    "ROCKWELL RVC 1100",
    "CARRIER AC CARRIER 18K INDUS GXI ALPHA HYBRIDJET 1.5 TON 3*",
    "CARRIER CARRIER 24K XCEED EDGE GXIINV AC 5*"
]


class Settings(BaseSettings):
    APP_NAME: str = "STOCK UNDO!"
    TAGLINE: str = "Check stock before you call the godown!"
    VERSION: str = "1.0.0"

    # Security
    STAFF_ACCESS_TOKEN: str = os.getenv("STAFF_ACCESS_TOKEN", "stock-undo-staff-secure-token-2026")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "stock-undo-internal-secret-key-salt")
    REQUIRE_AUTH: bool = False  # Set to True in production with Cloudflare

    # PC 1 Tally Connectivity (Localhost)
    PC1_HOST: str = os.getenv("PC1_HOST", "127.0.0.1")
    PC1_PORT: int = int(os.getenv("PC1_PORT", "9000"))
    PC1_LABEL: str = os.getenv("PC1_LABEL", "Tally PC 1 (Central)")

    # PC 2 Tally Connectivity (Tailscale Private Mesh)
    PC2_HOST: str = os.getenv("PC2_HOST", "100.101.152.68")
    PC2_PORT: int = int(os.getenv("PC2_PORT", "9000"))
    PC2_LABEL: str = os.getenv("PC2_LABEL", "Tally PC 2 (Branch / Godown)")

    # Timeouts & Cache (Cache TTL >= WS poll interval so HTTP polls hit RAM cache)
    TALLY_TIMEOUT_SECONDS: float = float(os.getenv("TALLY_TIMEOUT_SECONDS", "6.0"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "4"))
    LIVE_POLL_INTERVAL_SECONDS: float = float(os.getenv("LIVE_POLL_INTERVAL_SECONDS", "3.0"))

    # Rate Limiting (Allows fast live polling)
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "300"))

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://*.vercel.app",
        "*"
    ]

    # Whitelist Storage
    WHITELIST_FILE: Path = BASE_DIR / "whitelist.json"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_whitelist(self) -> List[str]:
        """Loads whitelist from JSON file if present, else uses default list."""
        if self.WHITELIST_FILE.exists():
            try:
                with open(self.WHITELIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        return [str(m).strip() for m in data if str(m).strip()]
            except Exception:
                pass
        return DEFAULT_WHITELIST


settings = Settings()

