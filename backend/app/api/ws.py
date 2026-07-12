"""
WebSocket endpoint — live anomaly score streaming.
"""

from __future__ import annotations

import asyncio
import json
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)


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
    except WebSocketDisconnect:
        manager.disconnect(websocket)
