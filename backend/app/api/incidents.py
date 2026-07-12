"""
Incident endpoints — CRUD + RCA reports + causal graphs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Incident, RCAResult
from app.models.schemas import (
    CausalEdge,
    CausalGraphResponse,
    CausalNode,
    CreateIncidentRequest,
    CreateIncidentResponse,
    IncidentDetailResponse,
    IncidentListResponse,
    IncidentSummary,
    ModelInfo,
    RCAReportResponse,
    RootCauseInfo,
    TimelineEvent,
)

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    page: int = 1, per_page: int = 20, db: AsyncSession = Depends(get_db)
):
    """List all incidents with pagination."""
    result = await db.execute(
        select(Incident).order_by(Incident.detected_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    incidents = result.scalars().all()

    summaries = [
        IncidentSummary(
            id=inc.id,
            title=inc.title,
            status=inc.status,
            severity=inc.severity,
            root_cause_service=inc.root_cause_service,
            affected_services=inc.affected_services,
            detected_at=inc.detected_at,
            resolved_at=inc.resolved_at,
            confidence=inc.confidence,
        )
        for inc in incidents
    ]

    return IncidentListResponse(
        incidents=summaries,
        total=len(summaries),
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=CreateIncidentResponse, status_code=201)
async def create_incident(
    req: CreateIncidentRequest, db: AsyncSession = Depends(get_db)
):
    """Create an incident and trigger RCA analysis."""
    incident = Incident(
        title=req.title,
        description=req.description,
        status="analyzing",
        severity="medium",
        window_start=req.window_start,
        window_end=req.window_end,
        detected_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    # TODO: Phase 6 — trigger orchestrator.run_rca_pipeline() here

    return CreateIncidentResponse(
        id=incident.id,
        status="analyzing",
        message=f"RCA pipeline triggered. Results available at /incidents/{incident.id}/report",
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed incident information."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    root_cause = None
    if incident.root_cause_service:
        root_cause = RootCauseInfo(
            service=incident.root_cause_service,
            confidence=incident.confidence or 0.0,
            fault_type=incident.fault_type,
        )

    return IncidentDetailResponse(
        id=incident.id,
        title=incident.title,
        status=incident.status,
        severity=incident.severity,
        detected_at=incident.detected_at,
        resolved_at=incident.resolved_at,
        anomaly_scores=incident.anomaly_scores or {},
        root_cause=root_cause,
        affected_services=incident.affected_services,
        timeline=[TimelineEvent(**e) for e in (incident.timeline or [])],
    )


@router.get("/{incident_id}/report", response_model=RCAReportResponse)
async def get_incident_report(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Get the AI-generated RCA report for an incident."""
    result = await db.execute(
        select(RCAResult).where(RCAResult.incident_id == incident_id)
    )
    rca = result.scalar_one_or_none()

    if not rca:
        raise HTTPException(
            status_code=404, detail="RCA report not found. Pipeline may still be running."
        )

    return RCAReportResponse(
        incident_id=rca.incident_id,
        root_cause=RootCauseInfo(
            service=rca.root_cause_service,
            confidence=rca.confidence,
            fault_type=rca.fault_type,
        ),
        explanation=rca.explanation or "",
        propagation_chain=rca.propagation_chain or "",
        metric_deltas=rca.metric_deltas or {},
        recommended_actions=rca.recommended_actions or [],
        model_info=ModelInfo(**(rca.model_info or {})),
    )


@router.get("/{incident_id}/causal-graph", response_model=CausalGraphResponse)
async def get_causal_graph(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Get the causal DAG visualization for an incident."""
    result = await db.execute(
        select(RCAResult).where(RCAResult.incident_id == incident_id)
    )
    rca = result.scalar_one_or_none()

    if not rca or not rca.causal_graph:
        raise HTTPException(
            status_code=404, detail="Causal graph not found for this incident."
        )

    cg = rca.causal_graph
    return CausalGraphResponse(
        incident_id=incident_id,
        causal_nodes=[CausalNode(**n) for n in cg.get("nodes", [])],
        causal_edges=[CausalEdge(**e) for e in cg.get("edges", [])],
    )
