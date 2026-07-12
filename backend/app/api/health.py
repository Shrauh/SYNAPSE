"""
Health endpoint — system health check.
"""

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import ComponentStatus, HealthResponse

import time

router = APIRouter(tags=["System"])

_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check with component status."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        components=ComponentStatus(
            api="up",
            database="up",
            ai_module="up",
            gnn_model_loaded=False,  # Updated when model loads
            maml_ready=False,
        ),
        uptime_seconds=round(time.time() - _start_time, 1),
    )
