"""
Log API — fetch, push and analyze service logs.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.log_analyzer import (
    analyze_service_logs,
    analyze_multiple_services,
    receive_pushed_logs,
    _pushed_logs,
)

router = APIRouter(prefix="/logs", tags=["Log Analysis"])
logger = logging.getLogger("synapse.logs.api")


class PushLogsRequest(BaseModel):
    service: str
    lines: List[str]


class AnalyzeRequest(BaseModel):
    services: List[str]
    namespace: str = "default"
    minutes_back: int = 10


@router.get("/analyze/{service}")
async def analyze_logs(service: str, namespace: str = "default", minutes_back: int = 10) -> Dict[str, Any]:
    """Fetch and analyze logs for a single service (Loki → kubectl → push)."""
    return await analyze_service_logs(service, namespace, minutes_back)


@router.post("/analyze")
async def analyze_multiple(req: AnalyzeRequest) -> Dict[str, Any]:
    """Analyze logs for multiple services at once."""
    results = await analyze_multiple_services(req.services, req.namespace)
    total_errors = sum(r.get("error_count", 0) for r in results.values())
    return {"services": results, "total_errors": total_errors, "analyzed": len(results)}


@router.post("/push")
def push_logs(req: PushLogsRequest) -> Dict[str, str]:
    """
    Push logs from any service to SYNAPSE.
    Call this from your application's error handler.
    
    Example (Python):
      requests.post('http://synapse:8000/api/v1/logs/push',
        json={'service': 'my-api', 'lines': ['ERROR: connection refused']})
    """
    receive_pushed_logs(req.service, req.lines)
    return {"status": "received", "service": req.service, "lines": len(req.lines)}


@router.get("/push/status")
def push_log_status() -> Dict[str, Any]:
    """Show which services are pushing logs."""
    return {
        "services_with_logs": list(_pushed_logs.keys()),
        "line_counts": {svc: len(lines) for svc, lines in _pushed_logs.items()},
    }
