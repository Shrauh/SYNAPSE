"""
Health endpoint — system health check.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_module.orchestrator import pipeline
from app.ai_module.meta.maml import maml_adapter
from app.config import settings
from app.models.schemas import ComponentStatus, HealthResponse
from app.utils.uptime import get_uptime
from app.db.database import get_db

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """System health check with component status."""
    try:
        await db.execute(text('SELECT 1'))
        db_status = "up"
    except Exception:
        db_status = "down"

    try:
        model_status = pipeline.get_model_status()
    except Exception:
        model_status = {}

    try:
        maml_ready = maml_adapter.is_initialized
    except Exception:
        maml_ready = False

    ai_module = "up" if model_status.get("initialized") else "initializing"
    gnn_model_loaded = model_status.get("model_trained", False)

    is_healthy = db_status == "up" and ai_module == "up" and maml_ready
    status = "healthy" if is_healthy else "degraded"

    return HealthResponse(
        status=status,
        version=settings.app_version,
        components=ComponentStatus(
            api="up",
            database=db_status,
            ai_module=ai_module,
            gnn_model_loaded=gnn_model_loaded,
            maml_ready=maml_ready,
        ),
        uptime_seconds=round(get_uptime(), 1),
    )
