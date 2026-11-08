from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class StockStatus(str, Enum):
    AVAILABLE = "Available"
    OUT_OF_STOCK = "Out of Stock"
    NOT_FOUND = "Model Not Found"
    OFFLINE = "Source Offline"


class StockItemResponse(BaseModel):
    model: str = Field(..., description="Permitted whitelist product model")
    available_stock: float = Field(0.0, description="Available closing balance quantity")
    unit: str = Field("Nos", description="Unit of measurement (Nos, Unit, Kg, etc.)")
    source: str = Field(..., description="Tally source origin (Tally PC 1, Tally PC 2, or Aggregated)")
    status: StockStatus = Field(StockStatus.NOT_FOUND, description="Current availability state")
    closing_balance_display: str = Field("0 Nos", description="Human-readable quantity representation")
    last_updated: Optional[str] = None


class TallyConnectionStatus(BaseModel):
    pc: str = Field(..., description="Identifier (pc1 or pc2)")
    label: str = Field(..., description="Friendly display label")
    online: bool = Field(False, description="Whether Tally HTTP/XML server is reachable")
    latency_ms: float = Field(0.0, description="Ping/response latency in milliseconds")
    open_company: Optional[str] = Field(None, description="Active Tally company name if online")
    last_checked: str = Field(..., description="ISO 8601 timestamp of last health probe")
    error: Optional[str] = Field(None, description="Diagnostic error details if offline")


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    tagline: str
    version: str
    server_time: str
    tally_pc1_online: bool
    tally_pc2_online: bool


class WhitelistResponse(BaseModel):
    total_models: int
    models: List[str]


class StockSummaryResponse(BaseModel):
    timestamp: str
    pc1_status: TallyConnectionStatus
    pc2_status: TallyConnectionStatus
    items: List[StockItemResponse]
    total_models: int
    available_count: int
    out_of_stock_count: int
    not_found_count: int

