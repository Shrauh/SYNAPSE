"""
Connect endpoint — test and store external system connections.

Allows users to register their Prometheus/Alertmanager, Kubernetes,
or custom webhook endpoints and verify connectivity.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("synapse.connect")

router = APIRouter(prefix="/connect", tags=["Connect"])

# ── In-memory connection store ──
_connections: Dict[str, Dict[str, Any]] = {}


class ConnectionTestRequest(BaseModel):
    """Request to test a connection to an external system."""
    name: str = "my-system"
    type: str = "prometheus"  # prometheus | kubernetes | webhook | custom
    url: str = "http://localhost:9090"
    api_key: Optional[str] = None
    namespace: Optional[str] = "default"


class ConnectionTestResponse(BaseModel):
    """Response from a connection test."""
    name: str
    type: str
    url: str
    status: str  # connected | failed | timeout
    latency_ms: float
    message: str
    timestamp: str


class ConnectionInfo(BaseModel):
    """Stored connection information."""
    name: str
    type: str
    url: str
    status: str
    latency_ms: float
    last_checked: str
    namespace: Optional[str] = None


@router.post("/test", response_model=ConnectionTestResponse)
async def test_connection(req: ConnectionTestRequest):
    """Test connectivity to an external system (Prometheus, K8s, webhook)."""
    import time

    start = time.time()
    status = "failed"
    message = ""

    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Determine the health/probe endpoint based on type
            if req.type == "prometheus":
                probe_url = req.url.rstrip("/") + "/-/ready"
            elif req.type == "alertmanager":
                probe_url = req.url.rstrip("/") + "/-/ready"
            elif req.type == "kubernetes":
                probe_url = req.url.rstrip("/") + "/api/v1/namespaces/" + (req.namespace or "default")
                # K8s API usually needs auth
            else:
                probe_url = req.url

            headers = {}
            if req.api_key:
                headers["Authorization"] = f"Bearer {req.api_key}"

            resp = await client.get(probe_url, headers=headers)
            latency_ms = round((time.time() - start) * 1000, 1)

            if resp.status_code < 400:
                status = "connected"
                message = f"Successfully reached {req.type} at {req.url} (HTTP {resp.status_code})"
            else:
                status = "failed"
                message = f"Received HTTP {resp.status_code} from {probe_url}"

    except Exception as e:
        latency_ms = round((time.time() - start) * 1000, 1)
        err_str = str(e)
        if "ConnectError" in err_str or "Connection refused" in err_str:
            message = f"Connection refused — is {req.type} running at {req.url}?"
        elif "TimeoutException" in err_str or "timed out" in err_str.lower():
            status = "timeout"
            message = f"Connection to {req.url} timed out after 5s"
        else:
            message = f"Connection failed: {err_str[:200]}"

    now = datetime.now(timezone.utc).isoformat()

    # Store the connection result
    _connections[req.name] = {
        "name": req.name,
        "type": req.type,
        "url": req.url,
        "status": status,
        "latency_ms": latency_ms,
        "last_checked": now,
        "namespace": req.namespace,
    }

    logger.info(f"Connection test: {req.name} ({req.type}) → {status} ({latency_ms}ms)")

    return ConnectionTestResponse(
        name=req.name,
        type=req.type,
        url=req.url,
        status=status,
        latency_ms=latency_ms,
        message=message,
        timestamp=now,
    )


@router.get("/list", response_model=List[ConnectionInfo])
async def list_connections():
    """List all saved connections and their status."""
    return [ConnectionInfo(**c) for c in _connections.values()]


@router.delete("/{name}")
async def remove_connection(name: str):
    """Remove a saved connection."""
    if name in _connections:
        del _connections[name]
        return {"message": f"Connection '{name}' removed"}
    return {"message": f"Connection '{name}' not found"}
