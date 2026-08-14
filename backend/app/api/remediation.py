"""
SYNAPSE Remediation API — Auto-remediation control endpoints.

Endpoints:
    POST /remediation/execute     — CQL selects + executes action for an incident
    POST /remediation/approve/{action_id}  — Human approves pending action
    GET  /remediation/history     — List past remediation actions
    GET  /remediation/actions     — List all available actions
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_module.remediation.action_space import ACTION_REGISTRY, ALL_ACTIONS
from app.ai_module.remediation.cql_agent import cql_agent
from app.ai_module.remediation.k8s_executor import k8s_executor
from app.db.database import get_db
from app.db.models import Incident, RemediationRecord
from app.models.schemas import (
    RemediationExecuteRequest,
    RemediationExecuteResponse,
    RemediationHistoryResponse,
    RemediationActionInfo,
)

router = APIRouter(prefix="/remediation", tags=["Auto-Remediation"])


@router.get("/actions", response_model=List[RemediationActionInfo])
async def list_actions():
    """List all available remediation actions with metadata."""
    return [
        RemediationActionInfo(
            action_id=a.action_id,
            name=a.name,
            description=a.description,
            applicable_faults=a.applicable_faults,
            auto_execute_threshold=a.auto_execute_threshold,
            always_require_approval=a.always_require_approval,
            risk_level=a.risk_level,
        )
        for a in ALL_ACTIONS
    ]


@router.post("/execute", response_model=RemediationExecuteResponse)
async def execute_remediation(
    req: RemediationExecuteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Select and execute a remediation action for an incident.

    Uses the CQL agent to select the best action based on:
    - Detected fault type
    - Root cause service
    - Current anomaly scores

    Auto-executes if CQL confidence > action threshold.
    Otherwise returns recommended action for human approval.
    """
    # Load incident
    result = await db.execute(select(Incident).where(Incident.id == req.incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Get fault info
    fault_type = req.fault_type or incident.fault_type or "unknown"
    root_cause = req.root_cause_service or incident.root_cause_service or "unknown"
    anomaly_scores = req.anomaly_scores or incident.anomaly_scores or {}

    # CQL agent selects action
    action, confidence, should_auto_execute = cql_agent.select_action(
        fault_type=fault_type,
        root_cause_service=root_cause,
        anomaly_scores=anomaly_scores,
        metric_deltas=req.metric_deltas,
    )

    # All action scores for UI
    all_scores = cql_agent.get_all_action_scores(
        fault_type=fault_type,
        root_cause_service=root_cause,
        anomaly_scores=anomaly_scores,
    )

    record_id = f"rem_{uuid.uuid4().hex[:8]}"

    if should_auto_execute and not req.dry_run:
        # Execute in background
        background_tasks.add_task(
            _execute_and_record,
            record_id=record_id,
            action=action,
            service=root_cause,
            confidence=confidence,
            incident_id=req.incident_id,
        )
        status = "executing"
        message = (
            f"Auto-executing {action.name} on '{root_cause}' "
            f"(confidence: {confidence:.0%})"
        )
    else:
        status = "pending_approval" if action.always_require_approval else "recommended"
        message = (
            f"Confidence {confidence:.0%} — "
            + ("Human approval required." if action.always_require_approval
               else f"Below threshold ({action.auto_execute_threshold:.0%}). Recommend only.")
        )

    return RemediationExecuteResponse(
        record_id=record_id,
        incident_id=req.incident_id,
        action_id=action.action_id,
        action_name=action.name,
        service=root_cause,
        confidence=confidence,
        status=status,
        message=message,
        auto_executed=should_auto_execute and not req.dry_run,
        requires_approval=action.always_require_approval,
        all_action_scores=all_scores,
        command=action.command_template.format(
            service=root_cause, namespace="default", node=root_cause
        ),
    )


@router.post("/approve/{record_id}", response_model=RemediationExecuteResponse)
async def approve_remediation(
    record_id: str,
    action_id: str,
    service: str,
    background_tasks: BackgroundTasks,
):
    """Human approves a pending remediation action."""
    action = ACTION_REGISTRY.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")

    background_tasks.add_task(
        _execute_and_record,
        record_id=record_id,
        action=action,
        service=service,
        confidence=1.0,  # Human approved = max confidence
        incident_id="manual",
    )

    return RemediationExecuteResponse(
        record_id=record_id,
        incident_id="manual",
        action_id=action_id,
        action_name=action.name,
        service=service,
        confidence=1.0,
        status="executing",
        message=f"Human-approved {action.name} executing on '{service}'",
        auto_executed=False,
        requires_approval=False,
        all_action_scores=[],
        command=action.command_template.format(
            service=service, namespace="default", node=service
        ),
    )


@router.get("/history", response_model=RemediationHistoryResponse)
async def get_remediation_history():
    """Get recent remediation execution history."""
    log = k8s_executor.get_execution_log(limit=50)
    return RemediationHistoryResponse(
        executions=log,
        total=len(log),
        executor_status=k8s_executor.get_status(),
    )


async def _execute_and_record(
    record_id: str,
    action,
    service: str,
    confidence: float,
    incident_id: str,
) -> None:
    """Background task: execute action and broadcast result via WebSocket."""
    result = await k8s_executor.execute(action, service, confidence)
    result["record_id"] = record_id

    # Broadcast to WebSocket clients
    try:
        from app.api.ws import manager
        await manager.broadcast({
            "type": "remediation_executed",
            "data": {
                "record_id": record_id,
                "incident_id": incident_id,
                "action_id": action.action_id,
                "action_name": action.name,
                "service": service,
                "confidence": confidence,
                "status": result.get("status"),
                "message": result.get("message"),
            }
        })
    except Exception as e:
        pass  # WebSocket broadcast is best-effort
