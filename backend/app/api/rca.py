"""
RCA Pipeline Control endpoints — trigger analysis and simulate faults.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Incident
from app.models.schemas import (
    PipelineStages,
    SimulateRequest,
    SimulateResponse,
    TriggerRCARequest,
    TriggerRCAResponse,
)

router = APIRouter(prefix="/rca", tags=["RCA Pipeline"])


@router.post("/trigger", response_model=TriggerRCAResponse)
async def trigger_rca(req: TriggerRCARequest, db: AsyncSession = Depends(get_db)):
    """Manually trigger the full 5-stage RCA pipeline for a time window."""
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

    # TODO: Phase 6 — call orchestrator.run_rca_pipeline(incident)

    return TriggerRCAResponse(
        incident_id=incident.id,
        pipeline_stages=PipelineStages(
            deic_gnn="pending",
            maml_adaptation="pending",
            causal_inference="pending",
            llm_reasoning="pending",
        ),
        execution_time_ms=0.0,
        result_url=f"/api/v1/incidents/{incident.id}/report",
    )


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_fault(req: SimulateRequest, db: AsyncSession = Depends(get_db)):
    """Generate a synthetic fault scenario and run the RCA pipeline on it."""
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

    # TODO: Phase 6 — call simulator + orchestrator

    return SimulateResponse(
        simulation_id=sim_id,
        incident_id=incident.id,
        injected_fault={
            "service": req.root_cause_service,
            "type": req.fault_type,
        },
        rca_result=None,  # Will be populated when pipeline completes
    )
