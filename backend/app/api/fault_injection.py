"""
Fault Injection API for SYNAPSE demo.

Provides endpoints to inject faults into running microservices
for demonstrating real-time anomaly detection.
"""
import httpx
import logging
import os
from typing import Optional
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fault-injection", tags=["Fault Injection"])

SERVICE_PORTS = {
    "api-gateway": 8080,
    "auth-service": 8081,
    "user-service": 8082,
    "order-service": 8083,
    "payment-service": 8085,
}

K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "")

def _build_url(service: str, port: int, path: str) -> str:
    if K8S_NAMESPACE:
        return f"http://{service}.{K8S_NAMESPACE}.svc.cluster.local:{port}{path}"
    return f"http://localhost:{port}{path}"


@router.post("/inject")
async def inject_fault(
    service: str,
    latency_ms: int = 0,
    error_rate: float = 0.0,
    cpu_burn: bool = False,
):
    """Inject a fault into a running microservice."""
    if service not in SERVICE_PORTS:
        raise HTTPException(404, f"Unknown service: {service}")

    port = SERVICE_PORTS[service]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                _build_url(service, port, "/fault"),
                params={
                    "latency_ms": latency_ms,
                    "error_rate": error_rate,
                    "cpu_burn": cpu_burn,
                },
            )
            return resp.json()
    except Exception as e:
        raise HTTPException(503, f"Cannot reach {service}: {e}")


@router.post("/clear/{service}")
async def clear_fault(service: str):
    """Clear all injected faults from a service."""
    if service not in SERVICE_PORTS:
        raise HTTPException(404, f"Unknown service: {service}")

    port = SERVICE_PORTS[service]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(_build_url(service, port, "/fault/clear"))
            return resp.json()
    except Exception as e:
        raise HTTPException(503, f"Cannot reach {service}: {e}")


@router.post("/clear-all")
async def clear_all_faults():
    """Clear faults from all services."""
    results = {}
    for service, port in SERVICE_PORTS.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(_build_url(service, port, "/fault/clear"))
                results[service] = "cleared"
        except Exception:
            results[service] = "unreachable"
    return results


@router.get("/services")
async def list_services():
    """List all available services and their status."""
    statuses = {}
    for service, port in SERVICE_PORTS.items():
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(_build_url(service, port, "/health"))
                statuses[service] = {"status": "running", "port": port}
        except Exception:
            statuses[service] = {"status": "down", "port": port}
    return statuses
