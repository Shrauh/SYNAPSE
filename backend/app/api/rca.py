"""
RCA Pipeline Control endpoints — trigger analysis and simulate faults.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_module.orchestrator import pipeline
from app.db.database import async_session, get_db
from app.db.models import Incident
from app.models.schemas import (
    ModelInfo,
    PipelineStages,
    RCAReportResponse,
    RootCauseInfo,
    SimulateRequest,
    SimulateResponse,
    TriggerRCARequest,
    TriggerRCAResponse,
)

router = APIRouter(prefix="/rca", tags=["RCA Pipeline"])


async def _run_pipeline_background(incident_id: str, simulation_result=None):
    """Run the RCA pipeline in the background."""
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if incident:
            try:
                await pipeline.run_rca_pipeline(incident, db, simulation_result)
            except Exception as e:
                incident.status = "error"
                incident.description = (incident.description or "") + f"\nPipeline error: {e}"
                await db.commit()
                print(f"[RCA] Pipeline error for {incident_id}: {e}")


@router.post("/trigger", response_model=TriggerRCAResponse)
async def trigger_rca(
    req: TriggerRCARequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger the full RCA pipeline for a time window."""
    incident = Incident(
        title=f"Manual RCA — {req.window_start.isoformat()} to {req.window_end.isoformat()}",
        status="analyzing",
        severity="medium",
        window_start=req.window_start,
        window_end=req.window_end,
        detected_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    # Run pipeline in background
    background_tasks.add_task(_run_pipeline_background, incident.id)

    return TriggerRCAResponse(
        incident_id=incident.id,
        pipeline_stages=PipelineStages(
            deic_gnn="running",
            maml_adaptation="pending",
            causal_inference="pending",
            llm_reasoning="pending",
        ),
        execution_time_ms=0.0,
        result_url=f"/api/v1/incidents/{incident.id}/report",
    )


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_fault(
    req: SimulateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Generate a synthetic fault scenario and run the RCA pipeline on it."""
    from data.simulator import MicroserviceSimulator

    sim_id = f"sim_{uuid.uuid4().hex[:6]}"
    incident = Incident(
        title=f"Simulated {req.fault_type} in {req.root_cause_service}",
        status="analyzing",
        severity=req.severity,
        detected_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    # Generate simulation data
    sim = MicroserviceSimulator()
    severity_map = {"low": 2.0, "medium": 4.0, "high": 6.0, "critical": 8.0}
    sim_result = sim.simulate_incident(
        root_cause=req.root_cause_service,
        fault_type=req.fault_type,
        severity=severity_map.get(req.severity, 5.0),
        num_steps=max(30, req.duration_minutes * 2),
    )

    # Run pipeline in background with pre-generated data
    background_tasks.add_task(
        _run_pipeline_background, incident.id, sim_result
    )

    return SimulateResponse(
        simulation_id=sim_id,
        incident_id=incident.id,
        injected_fault={
            "service": req.root_cause_service,
            "type": req.fault_type,
        },
        rca_result=None,  # Populated when pipeline completes — poll /incidents/{id}/report
    )
