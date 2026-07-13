"""
Health endpoint — system health check.
"""

import time

from fastapi import APIRouter

from app.ai_module.orchestrator import pipeline
from app.ai_module.meta.maml import maml_adapter
from app.config import settings
from app.models.schemas import ComponentStatus, HealthResponse

router = APIRouter(tags=["System"])

_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check with component status."""
    model_status = pipeline.get_model_status()

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        components=ComponentStatus(
            api="up",
            database="up",
            ai_module="up" if model_status.get("initialized") else "initializing",
            gnn_model_loaded=model_status.get("model_trained", False),
            maml_ready=maml_adapter.is_initialized,
        ),
        uptime_seconds=round(time.time() - _start_time, 1),
    )
