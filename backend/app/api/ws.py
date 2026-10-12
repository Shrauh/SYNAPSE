"""
WebSocket endpoint — live anomaly score streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger("synapse.ws")


class ConnectionManager:
    """Manages active WebSocket connections (thread-safe)."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        disconnected = []
        for connection in list(self.active_connections):  # iterate a copy
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()


@router.websocket("/live")
async def websocket_live(websocket: WebSocket):
    """
    WebSocket endpoint for live anomaly updates.

    Sends messages of type:
      - anomaly_update: per-service anomaly score changes
      - incident_detected: new incident alert
      - rca_complete: RCA pipeline finished
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; actual updates pushed via manager.broadcast()
            data = await websocket.receive_text()
            # Client can send ping/pong or filter commands
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, ConnectionResetError, Exception):
        manager.disconnect(websocket)

async def broadcast_json(data: dict) -> None:
    """Broadcast a JSON message to all connected WebSocket clients."""
    import json
    message = json.dumps(data)
    for ws in list(manager.active_connections):
        try:
            await ws.send_text(message)
        except Exception:
            manager.active_connections.discard(ws)
