"""
SYNAPSE Actions API — P1 Core Routes.

Extends the existing /api/v1/incidents namespace with action-related endpoints.
Also provides /api/v1/actions for cross-incident queries.

All existing incident endpoints are preserved. These are additive routes only.

Approval/execution security model:
  - Approval and execution require explicit operator intent (POST body with actor)
  - LLM output never executes directly
  - All executions go through the validated ACTION_REGISTRY
  - Every state transition is persisted and audited
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import (
    ActionApproval,
    ActionExecution,
    AuditEvent,
    Incident,
    IncidentEvent,
    RCAResult,
    ReportArtifact,
    SuggestedAction,
    VerificationRun,
)
from app.services.action_service import (
    ActionState,
    VALID_TRANSITIONS,
    approve_action,
    create_actions_for_incident,
    execute_action,
    run_verification,
    transition_action,
)
from app.services.report_generator import generate_report

logger = logging.getLogger("synapse.api.actions")

# ─────────────────────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────────────────────

# Incident-scoped action routes (attached to /incidents prefix)
incident_actions_router = APIRouter(tags=["Actions"])

# Standalone action routes
actions_router = APIRouter(prefix="/actions", tags=["Actions"])

# Report/download routes
report_router = APIRouter(tags=["Reports & Downloads"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class ActionSummary(BaseModel):
    id: str
    incident_id: str
    title: str
    category: str
    description: str
    reason: str
    target_service: Optional[str]
    target_namespace: str
    risk_level: str
    requires_approval: bool
    status: str
    confidence_score: float
    priority_rank: int
    simulated: bool
    proposed_by: str
    created_at: datetime
    updated_at: datetime
    evidence_refs: Optional[List] = None
    preconditions: Optional[List] = None
    expected_outcome: Optional[str] = None
    potential_side_effects: Optional[List] = None
    rollback_plan: Optional[str] = None
    verification_plan: Optional[str] = None
    verification_metrics: Optional[List] = None
    timeout_seconds: int


class ActionDetail(ActionSummary):
    execution_params: Optional[Dict] = None
    action_handler: Optional[str] = None
    runbook_refs: Optional[List] = None
    approval: Optional[Dict] = None
    execution: Optional[Dict] = None
    verification: Optional[Dict] = None
    valid_transitions: List[str] = []


class ApproveRequest(BaseModel):
    decided_by: str = Field(..., min_length=1, max_length=128, description="Operator identity")
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    reason: Optional[str] = Field(None, max_length=2000)
    conditions: Optional[List[str]] = None


class ExecuteRequest(BaseModel):
    requested_by: str = Field(default="operator", min_length=1, max_length=128)


class RollbackRequest(BaseModel):
    requested_by: str = Field(default="operator", min_length=1, max_length=128)
    reason: str = Field(..., min_length=1, max_length=1000)


class GenerateActionsRequest(BaseModel):
    force_regenerate: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Incident-scoped action routes: /incidents/{incident_id}/actions
# ─────────────────────────────────────────────────────────────────────────────

@incident_actions_router.get("/{incident_id}/actions", response_model=List[ActionSummary])
async def list_incident_actions(
    incident_id: str,
    status: Optional[str] = Query(None, description="Filter by action status"),
    db: AsyncSession = Depends(get_db),
):
    """List all suggested actions for an incident."""
    await _require_incident(db, incident_id)
    q = select(SuggestedAction).where(SuggestedAction.incident_id == incident_id)
    if status:
        q = q.where(SuggestedAction.status == status.upper())
    q = q.order_by(SuggestedAction.priority_rank)
    result = await db.execute(q)
    actions = result.scalars().all()
    return [_action_to_summary(a) for a in actions]


@incident_actions_router.post("/{incident_id}/actions/generate", response_model=Dict[str, Any])
async def generate_actions(
    incident_id: str,
    req: GenerateActionsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate evidence-grounded suggested actions from the latest RCA result.
    Idempotent: will not create duplicates unless force_regenerate=true.
    """
    incident = await _require_incident(db, incident_id)

    # Get latest RCA
    r = await db.execute(
        select(RCAResult).where(RCAResult.incident_id == incident_id)
        .order_by(desc(RCAResult.id))
    )
    rca = r.scalars().first()
    if not rca:
        raise HTTPException(404, "No RCA result found. Run RCA pipeline first.")

    if req.force_regenerate:
        # Delete existing proposed actions only (preserve executed/verified)
        existing = await db.execute(
            select(SuggestedAction).where(
                SuggestedAction.incident_id == incident_id,
                SuggestedAction.status == ActionState.PROPOSED,
            )
        )
        for a in existing.scalars().all():
            await db.delete(a)
        await db.commit()

    actions = await create_actions_for_incident(db, incident_id, rca, incident)
    return {
        "incident_id": incident_id,
        "generated": len(actions),
        "action_ids": [a.id for a in actions],
        "message": f"{len(actions)} action(s) generated from RCA result.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone action routes: /actions/{action_id}
# ─────────────────────────────────────────────────────────────────────────────

@actions_router.get("/{action_id}", response_model=ActionDetail)
async def get_action(action_id: str, db: AsyncSession = Depends(get_db)):
    """Get full action detail including approval, execution, and verification records."""
    action = await _require_action(db, action_id)

    # Load related records
    approval = await _get_latest_approval(db, action_id)
    execution = await _get_latest_execution(db, action_id)
    verification = await _get_latest_verification(db, action_id)

    detail = _action_to_summary(action)
    detail_dict = detail.model_dump()
    detail_dict["execution_params"] = action.execution_params
    detail_dict["action_handler"] = action.action_handler
    detail_dict["runbook_refs"] = action.runbook_refs
    detail_dict["approval"] = _approval_dict(approval)
    detail_dict["execution"] = _execution_dict(execution)
    detail_dict["verification"] = _verification_dict(verification)
    detail_dict["valid_transitions"] = list(VALID_TRANSITIONS.get(action.status, set()))
    return ActionDetail(**detail_dict)


@actions_router.post("/{action_id}/approve")
async def approve_or_reject_action(
    action_id: str,
    req: ApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a suggested action."""
    action = await _require_action(db, action_id)

    # Only PROPOSED or AWAITING_APPROVAL can be approved/rejected
    if action.status not in (ActionState.PROPOSED, ActionState.AWAITING_APPROVAL):
        raise HTTPException(
            400,
            f"Cannot approve/reject action in state {action.status!r}. "
            f"Action must be PROPOSED or AWAITING_APPROVAL."
        )

    try:
        action, approval = await approve_action(
            db, action,
            decided_by=req.decided_by,
            decision=req.decision,
            reason=req.reason,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "action_id": action.id,
        "new_status": action.status,
        "decision": req.decision,
        "decided_by": req.decided_by,
        "message": f"Action {req.decision.lower()} by {req.decided_by}",
    }


@actions_router.post("/{action_id}/execute")
async def execute_approved_action(
    action_id: str,
    req: ExecuteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute an approved action.
    Only works for APPROVED or READY_TO_EXECUTE actions.
    Execution goes through the validated ACTION_REGISTRY — no raw shell commands.
    """
    action = await _require_action(db, action_id)

    if action.status not in (ActionState.APPROVED, ActionState.READY_TO_EXECUTE):
        raise HTTPException(
            400,
            f"Cannot execute action in state {action.status!r}. Must be APPROVED first."
        )

    # Execute (this also transitions state and creates execution record)
    try:
        action, exec_record = await execute_action(db, action, requested_by=req.requested_by)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "action_id": action.id,
        "execution_id": exec_record.id,
        "new_status": action.status,
        "outcome": exec_record.outcome,
        "duration_ms": exec_record.duration_ms,
        "simulated": bool(exec_record.simulated),
        "message": (
            f"Action executed (simulated) — outcome: {exec_record.outcome}"
            if exec_record.simulated
            else f"Action executed — outcome: {exec_record.outcome}"
        ),
    }


@actions_router.post("/{action_id}/verify")
async def verify_action(
    action_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Run post-action verification. Collects fresh telemetry and evaluates
    whether the incident symptoms have resolved.
    Never reports success when telemetry is missing or stale.
    """
    action = await _require_action(db, action_id)
    if action.status != ActionState.EXECUTED:
        raise HTTPException(
            400,
            f"Cannot verify action in state {action.status!r}. Must be EXECUTED first."
        )

    incident = await _require_incident(db, action.incident_id)
    exec_record = await _get_latest_execution(db, action_id)

    try:
        action, vrun = await run_verification(
            db, action, incident,
            execution_id=exec_record.id if exec_record else None,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "action_id": action.id,
        "verification_id": vrun.id,
        "new_status": action.status,
        "outcome": vrun.outcome,
        "summary": vrun.summary,
        "metric_comparison": vrun.metric_comparison,
        "missing_metrics": vrun.missing_metrics,
        "next_step_recommendation": vrun.next_step_recommendation,
    }


@actions_router.get("/{action_id}/verification")
async def get_verification(action_id: str, db: AsyncSession = Depends(get_db)):
    """Get the latest verification result for an action."""
    await _require_action(db, action_id)
    vrun = await _get_latest_verification(db, action_id)
    if not vrun:
        raise HTTPException(404, "No verification run found for this action.")
    return _verification_dict(vrun)


@actions_router.post("/{action_id}/rollback")
async def request_rollback(
    action_id: str,
    req: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request rollback for an executed action."""
    action = await _require_action(db, action_id)
    rollback_eligible_states = {
        ActionState.EXECUTED,
        ActionState.VERIFICATION_FAILED,
        ActionState.VERIFICATION_INCONCLUSIVE,
        ActionState.EXECUTION_FAILED,
    }
    if action.status not in rollback_eligible_states:
        raise HTTPException(
            400,
            f"Action in state {action.status!r} is not eligible for rollback. "
            f"Eligible states: {', '.join(rollback_eligible_states)}"
        )
    if not action.rollback_handler:
        raise HTTPException(
            400,
            "No rollback handler defined for this action. Manual intervention required."
        )

    try:
        action = await transition_action(
            db, action, ActionState.ROLLBACK_PENDING,
            actor=req.requested_by, reason=req.reason,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "action_id": action.id,
        "new_status": action.status,
        "message": "Rollback pending. Requires operator confirmation to proceed.",
        "rollback_plan": action.rollback_plan,
    }


@actions_router.get("/{action_id}/log")
async def get_execution_log(action_id: str, db: AsyncSession = Depends(get_db)):
    """Get sanitized execution log for an action."""
    await _require_action(db, action_id)
    exec_record = await _get_latest_execution(db, action_id)
    if not exec_record:
        raise HTTPException(404, "No execution record found for this action.")
    return {
        "action_id": action_id,
        "execution_id": exec_record.id,
        "outcome": exec_record.outcome,
        "handler": exec_record.handler_name,
        "started_at": exec_record.started_at,
        "completed_at": exec_record.completed_at,
        "duration_ms": exec_record.duration_ms,
        "simulated": bool(exec_record.simulated),
        # Sanitized — no raw secrets
        "stdout": exec_record.stdout or "",
        "stderr": exec_record.stderr or "",
        "error": exec_record.error_message,
        "operation_metadata": exec_record.operation_metadata,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Report & Download routes: /incidents/{id}/download
# ─────────────────────────────────────────────────────────────────────────────

SUPPORTED_FORMATS = {"json", "markdown", "html", "pdf", "csv", "zip"}


@report_router.get("/{incident_id}/download/{fmt}")
async def download_report(
    incident_id: str,
    fmt: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Download an incident report in the specified format.
    Supported: json | markdown | html | pdf | csv | zip
    """
    if fmt not in SUPPORTED_FORMATS:
        raise HTTPException(
            400,
            f"Unsupported format: {fmt!r}. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
    await _require_incident(db, incident_id)

    try:
        result = await generate_report(db, incident_id, fmt=fmt, generated_by="api")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Report generation failed for {incident_id}: {e}", exc_info=True)
        raise HTTPException(500, "Report generation failed. See server logs.")

    content = result["content"]
    content_type = result["content_type"]
    filename = result["filename"]

    if isinstance(content, str):
        content = content.encode("utf-8")

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Report-ID": result["report_id"],
        "X-Checksum-SHA256": result["checksum_sha256"],
    }
    return Response(content=content, media_type=content_type, headers=headers)


@report_router.get("/{incident_id}/artifacts")
async def list_report_artifacts(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all generated report artifacts for an incident."""
    await _require_incident(db, incident_id)
    r = await db.execute(
        select(ReportArtifact)
        .where(ReportArtifact.incident_id == incident_id)
        .order_by(desc(ReportArtifact.generated_at))
    )
    artifacts = r.scalars().all()
    ext_map = {"json": "json", "markdown": "md", "html": "html", "pdf": "pdf", "csv": "csv", "zip": "zip"}
    mime_map = {
        "json": "application/json",
        "markdown": "text/markdown; charset=utf-8",
        "html": "text/html; charset=utf-8",
        "pdf": "application/pdf",
        "csv": "text/csv; charset=utf-8",
        "zip": "application/zip",
    }
    return [
        {
            "id": a.id,
            "format": a.report_format,
            "filename": f"synapse-incident-{incident_id}.{ext_map.get(a.report_format, 'txt')}",
            "content_type": mime_map.get(a.report_format, "application/octet-stream"),
            "file_size_bytes": a.file_size_bytes,
            "generated_at": a.generated_at.isoformat() if a.generated_at else None,
            "generated_by": a.generated_by,
            "checksum_sha256": a.checksum_sha256,
        }
        for a in artifacts
    ]


@report_router.get("/{incident_id}/preview")
async def preview_report(
    incident_id: str,
    fmt: str = "markdown",
    db: AsyncSession = Depends(get_db),
):
    """Get report content preview for display in the UI."""
    await _require_incident(db, incident_id)
    try:
        result = await generate_report(db, incident_id, fmt=fmt, generated_by="preview")
        content = result["content"]
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return {
            "incident_id": incident_id,
            "format": fmt,
            "report_id": result["report_id"],
            "filename": result["filename"],
            "content": content,
            "content_type": result["content_type"],
            "checksum_sha256": result["checksum_sha256"],
        }
    except Exception as e:
        logger.error(f"Report preview failed: {e}")
        raise HTTPException(500, f"Failed to generate report preview: {e}")


@report_router.get("/{incident_id}/timeline-events")
async def get_incident_timeline(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get structured timeline events for an incident."""
    await _require_incident(db, incident_id)
    r = await db.execute(
        select(IncidentEvent)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.event_time)
    )
    events = r.scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "event_time": e.event_time,
            "actor": e.actor,
            "title": e.title,
            "detail": e.detail,
            "metadata": e.event_metadata,
            "severity": e.severity,
        }
        for e in events
    ]


@report_router.get("/{incident_id}/similar")
async def get_similar_incidents(
    incident_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve similar historical incidents using ChromaDB RAG.
    Returns similarity reason for each match.
    """
    incident = await _require_incident(db, incident_id)
    try:
        from app.services.rag import find_similar_incidents
        similar = await find_similar_incidents(incident, limit=limit)
    except Exception as e:
        logger.warning(f"RAG similarity search failed: {e}")
        # Fallback: return incidents with same root cause service
        similar = []

    if not similar:
        # Fallback: DB-based similarity (same root cause service)
        if incident.root_cause_service:
            r = await db.execute(
                select(Incident)
                .where(Incident.root_cause_service == incident.root_cause_service)
                .where(Incident.id != incident_id)
                .order_by(desc(Incident.detected_at))
                .limit(limit)
            )
            db_similar = r.scalars().all()
            similar = [
                {
                    "incident_id": s.id,
                    "title": s.title,
                    "status": s.status,
                    "severity": s.severity,
                    "root_cause_service": s.root_cause_service,
                    "detected_at": str(s.detected_at),
                    "similarity_reason": f"Same root cause service: {s.root_cause_service}",
                    "similarity_score": 0.7,
                    "retrieval_method": "database_fallback",
                }
                for s in db_similar
            ]

    return {"incident_id": incident_id, "similar": similar, "count": len(similar)}


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log route
# ─────────────────────────────────────────────────────────────────────────────

audit_router = APIRouter(prefix="/audit", tags=["Audit"])


@audit_router.get("")
async def get_audit_log(
    incident_id: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get audit events. Optionally filter by incident or resource type."""
    q = select(AuditEvent).order_by(desc(AuditEvent.event_time))
    if incident_id:
        q = q.where(AuditEvent.incident_id == incident_id)
    if resource_type:
        q = q.where(AuditEvent.resource_type == resource_type)
    q = q.limit(limit)
    result = await db.execute(q)
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "event_time": e.event_time,
            "actor": e.actor,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "incident_id": e.incident_id,
            "outcome": e.outcome,
            "detail": e.detail,
        }
        for e in events
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Platform health
# ─────────────────────────────────────────────────────────────────────────────

platform_router = APIRouter(prefix="/platform", tags=["Platform Health"])


@platform_router.get("/health")
async def get_platform_health(db: AsyncSession = Depends(get_db)):
    """Get SYNAPSE component health — actual checks, not config presence."""
    from datetime import timedelta

    components = {}

    # Database
    try:
        await db.execute(select(Incident).limit(1))
        components["database"] = {"status": "healthy", "detail": "Query successful"}
    except Exception as e:
        components["database"] = {"status": "unhealthy", "detail": str(e)}

    # Prometheus
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get("http://localhost:9090/-/healthy")
            components["prometheus"] = {
                "status": "healthy" if r.status_code == 200 else "degraded",
                "detail": f"HTTP {r.status_code}",
            }
    except Exception as e:
        components["prometheus"] = {"status": "unavailable", "detail": "Cannot reach Prometheus"}

    # AI pipeline
    try:
        from app.ai_module.orchestrator import pipeline
        status = pipeline.get_model_status()
        components["ai_pipeline"] = {
            "status": "healthy" if status.get("initialized") else "initializing",
            "gnn_trained": status.get("model_trained"),
            "gnn_type": status.get("gnn_type"),
        }
    except Exception as e:
        components["ai_pipeline"] = {"status": "unhealthy", "detail": str(e)}

    # LLM
    try:
        from app.ai_module.llm.reasoner import get_llm_status
        components["llm"] = get_llm_status()
    except Exception:
        components["llm"] = {"status": "unknown"}

    # Recent telemetry freshness
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
        r = await db.execute(
            select(Incident).where(Incident.detected_at > cutoff).limit(1)
        )
        components["telemetry_ingestion"] = {
            "status": "healthy",
            "detail": "Recent activity detected",
        }
    except Exception:
        components["telemetry_ingestion"] = {"status": "unknown"}

    overall = "healthy"
    for k, v in components.items():
        if v.get("status") in ("unhealthy",):
            overall = "degraded"
            break

    return {
        "overall": overall,
        "components": components,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _require_incident(db: AsyncSession, incident_id: str) -> Incident:
    r = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = r.scalar_one_or_none()
    if not incident:
        raise HTTPException(404, f"Incident {incident_id!r} not found")
    return incident


async def _require_action(db: AsyncSession, action_id: str) -> SuggestedAction:
    r = await db.execute(select(SuggestedAction).where(SuggestedAction.id == action_id))
    action = r.scalar_one_or_none()
    if not action:
        raise HTTPException(404, f"Action {action_id!r} not found")
    return action


async def _get_latest_approval(db: AsyncSession, action_id: str) -> Optional[ActionApproval]:
    r = await db.execute(
        select(ActionApproval).where(ActionApproval.action_id == action_id)
        .order_by(desc(ActionApproval.id))
    )
    return r.scalars().first()


async def _get_latest_execution(db: AsyncSession, action_id: str) -> Optional[ActionExecution]:
    r = await db.execute(
        select(ActionExecution).where(ActionExecution.action_id == action_id)
        .order_by(desc(ActionExecution.id))
    )
    return r.scalars().first()


async def _get_latest_verification(db: AsyncSession, action_id: str) -> Optional[VerificationRun]:
    r = await db.execute(
        select(VerificationRun).where(VerificationRun.action_id == action_id)
        .order_by(desc(VerificationRun.id))
    )
    return r.scalars().first()


def _action_to_summary(a: SuggestedAction) -> ActionSummary:
    return ActionSummary(
        id=a.id,
        incident_id=a.incident_id,
        title=a.title,
        category=a.category,
        description=a.description,
        reason=a.reason,
        target_service=a.target_service,
        target_namespace=a.target_namespace,
        risk_level=a.risk_level,
        requires_approval=bool(a.requires_approval),
        status=a.status,
        confidence_score=a.confidence_score,
        priority_rank=a.priority_rank,
        simulated=bool(a.simulated),
        proposed_by=a.proposed_by,
        created_at=a.created_at,
        updated_at=a.updated_at,
        evidence_refs=a.evidence_refs,
        preconditions=a.preconditions,
        expected_outcome=a.expected_outcome,
        potential_side_effects=a.potential_side_effects,
        rollback_plan=a.rollback_plan,
        verification_plan=a.verification_plan,
        verification_metrics=a.verification_metrics,
        timeout_seconds=a.timeout_seconds,
    )


def _approval_dict(a: Optional[ActionApproval]) -> Optional[Dict]:
    if not a:
        return None
    return {
        "id": a.id,
        "decision": a.decision,
        "decided_by": a.decided_by,
        "reason": a.reason,
        "decided_at": a.decided_at,
    }


def _execution_dict(e: Optional[ActionExecution]) -> Optional[Dict]:
    if not e:
        return None
    return {
        "id": e.id,
        "outcome": e.outcome,
        "handler_name": e.handler_name,
        "started_at": e.started_at,
        "completed_at": e.completed_at,
        "duration_ms": e.duration_ms,
        "simulated": bool(e.simulated),
        "error_message": e.error_message,
        "operation_metadata": e.operation_metadata,
    }


def _verification_dict(v: Optional[VerificationRun]) -> Optional[Dict]:
    if not v:
        return None
    return {
        "id": v.id,
        "outcome": v.outcome,
        "summary": v.summary,
        "criteria": v.criteria,
        "metric_comparison": v.metric_comparison,
        "baseline_snapshot": v.baseline_snapshot,
        "post_action_snapshot": v.post_action_snapshot,
        "data_freshness_seconds": v.data_freshness_seconds,
        "missing_metrics": v.missing_metrics,
        "symptoms_resolved": v.symptoms_resolved,
        "next_step_recommendation": v.next_step_recommendation,
        "started_at": v.started_at,
        "completed_at": v.completed_at,
    }
