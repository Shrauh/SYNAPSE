"""
Metrics endpoint — system-wide statistics with real data.
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
    """Return system-wide operational metrics with real data."""
    total = (await db.execute(select(func.count(Incident.id)))).scalar() or 0
    active = (
        await db.execute(
            select(func.count(Incident.id)).where(Incident.status == "analyzing")
        )
    ).scalar() or 0

    # Compute real average resolution time
    resolved = (
        await db.execute(
            select(Incident).where(Incident.status == "detected")
        )
    ).scalars().all()

    avg_time = 0.0
    if resolved:
        times = []
        for inc in resolved:
            if inc.resolved_at and inc.detected_at:
                delta = (inc.resolved_at - inc.detected_at).total_seconds()
                times.append(delta)
        avg_time = sum(times) / len(times) if times else 0.0

    # Get real system stats
    import psutil
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent

    return MetricsResponse(
        total_incidents=total,
        active_incidents=active,
        avg_resolution_time_sec=round(avg_time, 2),
        model_stats=ModelStats(),
        system=SystemStats(cpu_usage=cpu, memory_usage=mem),
    )
