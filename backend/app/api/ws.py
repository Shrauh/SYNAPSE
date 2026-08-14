"""
SYNAPSE WebSocket Endpoint — Live Anomaly Score Streaming.

Pushes updates every 2 seconds to all connected dashboard clients.

Message types:
  - anomaly_update     → per-service anomaly scores (every 2s)
  - incident_detected  → new incident alert
  - rca_complete       → RCA pipeline finished with root cause
  - remediation_executed → auto-remediation action taken
  - log_event          → error log from a service
  - alert              → pre-computed alert from Kafka

WebSocket endpoint: /api/v1/live
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages active WebSocket connections with broadcast support."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[WS] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"[WS] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict) -> None:
        """Send a message to all connected clients (best-effort)."""
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

    async def send_to(self, websocket: WebSocket, message: dict) -> None:
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


manager = ConnectionManager()


@router.websocket("/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint — streams live anomaly data to the dashboard.

    The client should listen for JSON objects with a "type" field:
      - anomaly_update: Contains current anomaly scores for all services
      - incident_detected: New incident was created
      - rca_complete: RCA analysis finished
      - remediation_executed: Auto-remediation was taken
    """
    await manager.connect(websocket)

    # Send initial state immediately on connect
    try:
        initial_data = _get_current_state()
        await manager.send_to(websocket, {
            "type": "initial_state",
            "data": initial_data,
        })
    except Exception:
        pass

    try:
        while True:
            # Keep connection alive — actual data pushed via broadcast_loop
            data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=30.0,  # 30s receive timeout (for ping/pong)
            )
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except asyncio.TimeoutError:
        # No data from client in 30s — send keepalive
        try:
            await websocket.send_json({"type": "keepalive", "timestamp": _now()})
        except Exception:
            manager.disconnect(websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_current_state() -> dict:
    """Get current system state for initial WS payload."""
    try:
        from app.services.graph_builder import graph_builder
        scores = graph_builder.get_anomaly_scores()
        graph_data = {
            "nodes": [
                {
                    "id": node,
                    "anomaly_score": scores.get(node, 0.0),
                    "status": "anomalous" if scores.get(node, 0.0) > settings.anomaly_threshold else "healthy",
                }
                for node in graph_builder.service_names
            ]
        }
    except Exception:
        graph_data = {}

    return {
        "timestamp": _now(),
        "graph": graph_data,
        "system": "operational",
    }


async def broadcast_loop() -> None:
    """Background task: push anomaly updates every 2 seconds.

    Runs as a forever-loop in the application lifespan.
    Fetches current anomaly scores from the graph builder and broadcasts
    them to all connected WebSocket clients.
    """
    logger.info("[WS] Broadcast loop started (2s interval)")
    _tick = 0
    _live_sim_state: Dict[str, float] = {}  # Simulated live scores when no real data

    while True:
        try:
            await asyncio.sleep(2.0)
            _tick += 1

            if not manager.active_connections:
                continue

            # Get current anomaly scores
            try:
                from app.services.graph_builder import graph_builder
                anomaly_scores = graph_builder.get_anomaly_scores()
                service_names = graph_builder.service_names
            except Exception:
                # Fallback: generate mock scores for demo
                service_names = [
                    "frontend", "checkout", "cart", "payment",
                    "order", "catalog", "ad", "redis", "email", "orderdb"
                ]
                if not _live_sim_state:
                    _live_sim_state = {svc: 0.05 + random.random() * 0.1 for svc in service_names}
                else:
                    # Drift the scores slightly each tick
                    for svc in service_names:
                        current = _live_sim_state.get(svc, 0.05)
                        drift = random.uniform(-0.02, 0.02)
                        _live_sim_state[svc] = max(0.01, min(1.0, current + drift))
                anomaly_scores = _live_sim_state

            # Build per-service status
            services_data = []
            for svc in service_names:
                score = anomaly_scores.get(svc, 0.0)
                status = (
                    "critical" if score > 0.85 else
                    "warning" if score > settings.anomaly_threshold else
                    "healthy"
                )
                services_data.append({
                    "id": svc,
                    "anomaly_score": round(score, 4),
                    "status": status,
                })

            # Check for newly anomalous services
            critical_services = [s for s in services_data if s["status"] == "critical"]

            await manager.broadcast({
                "type": "anomaly_update",
                "timestamp": _now(),
                "tick": _tick,
                "data": {
                    "services": services_data,
                    "max_score": max((s["anomaly_score"] for s in services_data), default=0.0),
                    "anomalous_count": sum(1 for s in services_data if s["anomaly_score"] > settings.anomaly_threshold),
                    "critical_services": [s["id"] for s in critical_services],
                }
            })

            # Every 30 ticks (~1 min), also broadcast graph topology
            if _tick % 15 == 0:
                try:
                    from app.services.graph_builder import graph_builder
                    await manager.broadcast({
                        "type": "graph_update",
                        "timestamp": _now(),
                        "data": graph_builder.to_dict(),
                    })
                except Exception:
                    pass

        except asyncio.CancelledError:
            logger.info("[WS] Broadcast loop cancelled")
            break
        except Exception as e:
            logger.error(f"[WS] Broadcast loop error: {e}")
            await asyncio.sleep(2.0)
