"""
Metrics endpoint — system-wide statistics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Incident
from app.models.schemas import MetricsResponse, ModelStats, SystemStats

router = APIRouter(tags=["System"])


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Return system-wide operational metrics."""
    total = (await db.execute(select(func.count(Incident.id)))).scalar() or 0
    active = (
        await db.execute(
            select(func.count(Incident.id)).where(Incident.status == "analyzing")
        )
    ).scalar() or 0

    return MetricsResponse(
        total_incidents=total,
        active_incidents=active,
        avg_resolution_time_sec=0.0,
        model_stats=ModelStats(),
        system=SystemStats(cpu_usage=0.0, memory_usage=0.0),
    )
