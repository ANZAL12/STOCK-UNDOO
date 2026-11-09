"""
STOCK UNDO! - Real-Time WebSocket Hub & Background Live Stock Synchronizer
Pushes instant updates to mobile devices whenever stock is reduced or increased.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.services.stock_service import StockService


logger = logging.getLogger("stock_undo.websocket")
router = APIRouter(tags=["Real-Time WebSockets"])


class WebSocketHub:
    """Manages active browser WebSocket connections and broadcasts instant updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._last_snapshot: Dict[str, float] = {}
        self._poller_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[WS] Client connected. Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"[WS] Client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast_json(self, data: dict):
        """Sends data to all connected clients safely."""
        for ws in list(self.active_connections):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)

    def has_stock_changed(self, new_items: list) -> bool:
        """Compares current stock quantities against the previous snapshot."""
        new_snapshot = {item.model: item.available_stock for item in new_items}
        if not self._last_snapshot:
            self._last_snapshot = new_snapshot
            return True

        changed = False
        for model, qty in new_snapshot.items():
            prev_qty = self._last_snapshot.get(model)
            if prev_qty is None or prev_qty != qty:
                changed = True
                logger.info(f"[LIVE SYNC] Stock change detected: '{model}' changed from {prev_qty} to {qty}")
                break

        if changed or len(new_snapshot) != len(self._last_snapshot):
            self._last_snapshot = new_snapshot
            return True

        return False


ws_hub = WebSocketHub()


@router.websocket("/ws/stock")
async def websocket_stock_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for instant live stock streaming.
    Connected clients receive real-time JSON pushes whenever stock counts change.
    """
    await ws_hub.connect(websocket)
    try:
        # Send current live/cached state immediately upon connection without hammering Tally
        initial_data = await StockService.get_all_stock(force_refresh=False)
        await websocket.send_json({
            "type": "INITIAL_STOCK",
            "data": initial_data.model_dump()
        })

        # Keep socket open and listen for any ping / pong or client messages
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)
    except Exception as e:
        logger.warning(f"[WS] Connection closed: {e}")
        ws_hub.disconnect(websocket)


async def background_stock_sync_loop():
    """
    Continuous background loop that monitors TallyPrime for any stock movements.
    Runs every LIVE_POLL_INTERVAL_SECONDS (default: 3 seconds).
    If any model's closing quantity changes (reduced or increased),
    it immediately pushes the update to all connected web clients.
    """
    logger.info("[LIVE SYNC] Starting background Tally real-time stock monitor...")
    while True:
        try:
            # Poll only if there are connected clients or periodically to keep cache warm
            interval = settings.LIVE_POLL_INTERVAL_SECONDS
            if not ws_hub.active_connections:
                # If no clients are connected, sleep longer to avoid unnecessary Tally queries
                await asyncio.sleep(5.0)
                continue

            # Query live Tally stock
            summary = await StockService.get_all_stock(force_refresh=True)

            # Check if any quantity changed
            if ws_hub.has_stock_changed(summary.items):
                await ws_hub.broadcast_json({
                    "type": "STOCK_UPDATED",
                    "data": summary.model_dump()
                })

        except Exception as e:
            logger.debug(f"[LIVE SYNC] Polling tick error: {e}")

        await asyncio.sleep(settings.LIVE_POLL_INTERVAL_SECONDS)

