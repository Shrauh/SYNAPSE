"""
SYNAPSE ORM Models — SQLAlchemy table definitions.

Stores incidents, RCA results, service metrics, model metadata,
suggested actions, approvals, executions, verifications, and audit events.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _gen_id() -> str:
    return f"inc_{uuid.uuid4().hex[:8]}"


def _gen_action_id() -> str:
    return f"act_{uuid.uuid4().hex[:10]}"


def _gen_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:8]}"


def _gen_report_id() -> str:
    return f"rpt_{uuid.uuid4().hex[:8]}"


class Incident(Base):
    """A detected or manually created incident."""

    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="analyzing"
    )  # analyzing | detected | resolved
    severity: Mapped[str] = mapped_column(
        String(16), default="medium"
    )  # critical | high | medium | low
    root_cause_service: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    fault_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    affected_services: Mapped[list | None] = mapped_column(JSON, nullable=True)
    anomaly_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeline: Mapped[list | None] = mapped_column(JSON, nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RCAResult(Base):
    """Stored RCA report for an incident."""

    __tablename__ = "rca_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    root_cause_service: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    fault_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    propagation_chain: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metric_deltas: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommended_actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    causal_graph: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class ServiceMetric(Base):
    """Time-series service metric snapshot."""

    __tablename__ = "service_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latency: Mapped[float] = mapped_column(Float, default=0.0)
    error_rate: Mapped[float] = mapped_column(Float, default=0.0)
    cpu: Mapped[float] = mapped_column(Float, default=0.0)
    memory: Mapped[float] = mapped_column(Float, default=0.0)
    request_rate: Mapped[float] = mapped_column(Float, default=0.0)


class RecoveryActionLog(Base):
    """Log of recovery actions taken by the system."""

    __tablename__ = "recovery_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_service: Mapped[str] = mapped_column(String(128), nullable=False)
    kubectl_command: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    success: Mapped[bool] = mapped_column(Integer, default=0)  # SQLite has no bool
    simulated: Mapped[bool] = mapped_column(Integer, default=1)
    severity_level: Mapped[str] = mapped_column(String(32), default="L1_SIMPLE")
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class PatternHistory(Base):
    """Historical record of detected recurring patterns."""

    __tablename__ = "pattern_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    root_cause_service: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    common_fault_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity_trend: Mapped[str] = mapped_column(String(32), default="stable")
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


# ─────────────────────────────────────────────────────────────────────────────
# P1: Action State Machine — 7 new tables (additive, no existing tables changed)
# ─────────────────────────────────────────────────────────────────────────────

class SuggestedAction(Base):
    """
    Evidence-grounded remediation recommendation for an incident.
    State machine: PROPOSED->AWAITING_APPROVAL->APPROVED->READY_TO_EXECUTE
    ->EXECUTING->EXECUTED->VERIFYING->VERIFIED_SUCCESS|VERIFICATION_FAILED
    |VERIFICATION_INCONCLUSIVE|EXECUTION_FAILED|REJECTED|CANCELLED
    ->ROLLBACK_PENDING->ROLLING_BACK->ROLLED_BACK->MANUAL_INTERVENTION_REQUIRED
    """
    __tablename__ = "suggested_actions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_action_id)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    # COLLECT_DIAGNOSTICS|INSPECT_K8S|INSPECT_LOGS|INVESTIGATE_SATURATION
    # |RESTART_WORKLOAD|SCALE_WORKLOAD|ROLLBACK_DEPLOYMENT|APPLY_CONFIG
    # |ESCALATE|MONITOR_ONLY
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    target_service: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_namespace: Mapped[str] = mapped_column(String(64), default="default")
    target_resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), default="medium")
    requires_approval: Mapped[int] = mapped_column(Integer, default=1)
    required_permission: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    preconditions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    expected_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    potential_side_effects: Mapped[list | None] = mapped_column(JSON, nullable=True)
    runbook_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Validated handler name from ACTION_REGISTRY — never raw shell
    action_handler: Mapped[str | None] = mapped_column(String(64), nullable=True)
    execution_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rollback_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_handler: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rollback_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_metrics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_rank: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(48), default="PROPOSED", index=True)
    simulated: Mapped[int] = mapped_column(Integer, default=1)
    proposed_by: Mapped[str] = mapped_column(String(64), default="synapse-ai")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ActionApproval(Base):
    """Approval or rejection record for a suggested action."""
    __tablename__ = "action_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)  # APPROVED|REJECTED
    decided_by: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ActionExecution(Base):
    """Record of an action execution attempt."""
    __tablename__ = "action_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(128), default="operator")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    handler_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sanitized_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    operation_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), default="PENDING")
    # PENDING|SUCCESS|FAILED|TIMEOUT|CANCELLED
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulated: Mapped[int] = mapped_column(Integer, default=1)


class VerificationRun(Base):
    """Post-action verification evidence. Never marks success when telemetry missing."""
    __tablename__ = "verification_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    execution_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), default="PENDING")
    # PENDING|VERIFIED_SUCCESS|VERIFICATION_FAILED|VERIFICATION_INCONCLUSIVE
    criteria: Mapped[list | None] = mapped_column(JSON, nullable=True)
    baseline_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    post_action_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metric_comparison: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_freshness_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_metrics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    symptoms_resolved: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_anomalies_cleared: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_step_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)


class IncidentEvent(Base):
    """Structured timeline event for an incident."""
    __tablename__ = "incident_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_event_id)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    actor: Mapped[str] = mapped_column(String(128), default="system")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)


class ReportArtifact(Base):
    """Metadata for a generated incident report."""
    __tablename__ = "report_artifacts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_report_id)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    report_format: Mapped[str] = mapped_column(String(16), nullable=False)
    # json|markdown|html|pdf|csv|zip
    version: Mapped[int] = mapped_column(Integer, default=1)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    generated_by: Mapped[str] = mapped_column(String(64), default="system")
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    incident_status_at_generation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_references: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEvent(Base):
    """Security and operational audit log. Append-only — never deleted."""
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    incident_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    outcome: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    # SUCCESS|DENIED|FAILED
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # no secrets ever
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
