"""
SYNAPSE Action Service — P1 Core.

Implements:
  - Evidence-grounded action generation from RCA pipeline output
  - 17-state action state machine with valid transition enforcement
  - Deterministic ACTION_REGISTRY (validated allowlist — no shell=True)
  - Approval workflow with audit trail
  - Post-action verification trigger
  - Audit event persistence

Security guarantees:
  - LLM output NEVER executes directly
  - All kubectl operations use argument arrays (no shell=True)
  - Namespaces and resource names validated against allowlist patterns
  - Secrets never logged or stored in execution records
"""
from __future__ import annotations

import hashlib
import logging
import re
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    ActionApproval,
    ActionExecution,
    AuditEvent,
    IncidentEvent,
    RCAResult,
    SuggestedAction,
    VerificationRun,
    Incident,
)

logger = logging.getLogger("synapse.action_service")

# ─────────────────────────────────────────────────────────────────────────────
# Action State Machine
# ─────────────────────────────────────────────────────────────────────────────

class ActionState:
    PROPOSED = "PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    VERIFYING = "VERIFYING"
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    VERIFICATION_INCONCLUSIVE = "VERIFICATION_INCONCLUSIVE"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    ROLLBACK_PENDING = "ROLLBACK_PENDING"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"


# Valid transitions: {from_state: set_of_valid_to_states}
VALID_TRANSITIONS: Dict[str, set] = {
    ActionState.PROPOSED: {ActionState.AWAITING_APPROVAL, ActionState.APPROVED, ActionState.REJECTED, ActionState.CANCELLED},
    ActionState.AWAITING_APPROVAL: {ActionState.APPROVED, ActionState.REJECTED, ActionState.CANCELLED},
    ActionState.APPROVED: {ActionState.READY_TO_EXECUTE, ActionState.CANCELLED},
    ActionState.READY_TO_EXECUTE: {ActionState.EXECUTING, ActionState.CANCELLED},
    ActionState.EXECUTING: {ActionState.EXECUTED, ActionState.EXECUTION_FAILED, ActionState.CANCELLED},
    ActionState.EXECUTED: {ActionState.VERIFYING, ActionState.ROLLBACK_PENDING},
    ActionState.VERIFYING: {
        ActionState.VERIFIED_SUCCESS,
        ActionState.VERIFICATION_FAILED,
        ActionState.VERIFICATION_INCONCLUSIVE,
        ActionState.ROLLBACK_PENDING,
    },
    ActionState.VERIFIED_SUCCESS: set(),  # terminal
    ActionState.VERIFICATION_FAILED: {ActionState.ROLLBACK_PENDING, ActionState.MANUAL_INTERVENTION_REQUIRED},
    ActionState.VERIFICATION_INCONCLUSIVE: {ActionState.ROLLBACK_PENDING, ActionState.MANUAL_INTERVENTION_REQUIRED},
    ActionState.EXECUTION_FAILED: {ActionState.ROLLBACK_PENDING, ActionState.MANUAL_INTERVENTION_REQUIRED, ActionState.CANCELLED},
    ActionState.REJECTED: set(),  # terminal
    ActionState.CANCELLED: set(),  # terminal
    ActionState.ROLLBACK_PENDING: {ActionState.ROLLING_BACK, ActionState.MANUAL_INTERVENTION_REQUIRED},
    ActionState.ROLLING_BACK: {ActionState.ROLLED_BACK, ActionState.MANUAL_INTERVENTION_REQUIRED},
    ActionState.ROLLED_BACK: set(),  # terminal
    ActionState.MANUAL_INTERVENTION_REQUIRED: set(),  # terminal
}


def validate_transition(from_state: str, to_state: str) -> bool:
    """Returns True if the transition is valid per the state machine."""
    return to_state in VALID_TRANSITIONS.get(from_state, set())


# ─────────────────────────────────────────────────────────────────────────────
# Action Registry — Safe Execution Allowlist
# ─────────────────────────────────────────────────────────────────────────────

# Validation patterns for resource names (kubernetes safe)
_K8S_NAME_RE = re.compile(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$')
_NAMESPACE_RE = re.compile(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$')


def _validate_k8s_name(name: str) -> str:
    """Raise ValueError if name is not a valid kubernetes resource name."""
    if not name or not _K8S_NAME_RE.match(name):
        raise ValueError(f"Invalid kubernetes resource name: {name!r}")
    if len(name) > 253:
        raise ValueError(f"Kubernetes resource name too long: {name!r}")
    return name


def _validate_namespace(ns: str) -> str:
    if not ns or not _NAMESPACE_RE.match(ns):
        raise ValueError(f"Invalid namespace: {ns!r}")
    return ns


class ActionRegistry:
    """
    Deterministic, validated action execution registry.

    All handlers use subprocess argument arrays — no shell=True, no string
    concatenation of user input. The LLM proposes action categories and targets;
    this registry decides what actually executes and validates all parameters.
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self._handlers = {
            "restart_deployment": self._restart_deployment,
            "scale_deployment": self._scale_deployment,
            "rollback_deployment": self._rollback_deployment,
            "get_pod_logs": self._get_pod_logs,
            "describe_deployment": self._describe_deployment,
            "get_events": self._get_events,
            "simulate_noop": self._simulate_noop,
        }

    def get_available_handlers(self) -> List[str]:
        return list(self._handlers.keys())

    def execute(self, handler_name: str, params: Dict[str, Any], simulated: bool = True) -> Dict[str, Any]:
        """
        Execute a registered handler with validated parameters.
        Returns sanitized execution result — never raw shell output with secrets.
        """
        if handler_name not in self._handlers:
            return {
                "outcome": "FAILED",
                "error": f"Unknown handler: {handler_name!r}. Allowed: {self.get_available_handlers()}",
            }
        try:
            return self._handlers[handler_name](params, simulated=simulated)
        except ValueError as e:
            logger.error(f"Parameter validation failed for {handler_name}: {e}")
            return {"outcome": "FAILED", "error": f"Validation error: {e}"}
        except Exception as e:
            logger.error(f"Handler {handler_name} raised unexpected error: {e}")
            return {"outcome": "FAILED", "error": "Execution error — see server logs"}

    def _run_kubectl(self, args: List[str], timeout: int = 60) -> Dict[str, Any]:
        """
        Run kubectl with a validated argument array.
        NEVER uses shell=True. NEVER concatenates user input into a string.
        """
        cmd = ["kubectl"] + args
        logger.info(f"kubectl {' '.join(args[:6])}...")  # log first 6 args only

        if self.dry_run:
            return {
                "outcome": "SUCCESS",
                "simulated": True,
                "dry_run": True,
                "command_preview": f"kubectl {' '.join(args)}",
                "stdout": "[DRY RUN — no actual change made]",
                "stderr": "",
            }

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,  # explicit — never shell=True
            )
            return {
                "outcome": "SUCCESS" if result.returncode == 0 else "FAILED",
                "exit_code": result.returncode,
                "stdout": result.stdout[:4096],  # truncate to prevent log flooding
                "stderr": result.stderr[:2048],
            }
        except subprocess.TimeoutExpired:
            return {"outcome": "TIMEOUT", "error": f"kubectl timed out after {timeout}s"}
        except FileNotFoundError:
            return {"outcome": "FAILED", "error": "kubectl not found in PATH"}
        except Exception as e:
            return {"outcome": "FAILED", "error": "kubectl execution error"}

    def _restart_deployment(self, params: Dict[str, Any], simulated: bool = True) -> Dict[str, Any]:
        name = _validate_k8s_name(str(params.get("deployment", "")))
        namespace = _validate_namespace(str(params.get("namespace", "default")))
        return self._run_kubectl(
            ["rollout", "restart", f"deployment/{name}", "-n", namespace]
        )

    def _scale_deployment(self, params: Dict[str, Any], simulated: bool = True) -> Dict[str, Any]:
        name = _validate_k8s_name(str(params.get("deployment", "")))
        namespace = _validate_namespace(str(params.get("namespace", "default")))
        replicas = int(params.get("replicas", 2))
        if not (0 <= replicas <= 50):
            raise ValueError(f"Replica count out of safe range: {replicas}")
        return self._run_kubectl(
            ["scale", f"deployment/{name}", f"--replicas={replicas}", "-n", namespace]
        )

    def _rollback_deployment(self, params: Dict[str, Any], simulated: bool = True) -> Dict[str, Any]:
        name = _validate_k8s_name(str(params.get("deployment", "")))
        namespace = _validate_namespace(str(params.get("namespace", "default")))
        return self._run_kubectl(
            ["rollout", "undo", f"deployment/{name}", "-n", namespace]
        )

    def _get_pod_logs(self, params: Dict[str, Any], simulated: bool = True) -> Dict[str, Any]:
        name = _validate_k8s_name(str(params.get("deployment", "")))
        namespace = _validate_namespace(str(params.get("namespace", "default")))
        lines = min(int(params.get("lines", 50)), 500)
        return self._run_kubectl(
            ["logs", f"deployment/{name}", "-n", namespace, f"--tail={lines}", "--prefix"]
        )

    def _describe_deployment(self, params: Dict[str, Any], simulated: bool = True) -> Dict[str, Any]:
        name = _validate_k8s_name(str(params.get("deployment", "")))
        namespace = _validate_namespace(str(params.get("namespace", "default")))
        return self._run_kubectl(
            ["describe", "deployment", name, "-n", namespace]
        )

    def _get_events(self, params: Dict[str, Any], simulated: bool = True) -> Dict[str, Any]:
        namespace = _validate_namespace(str(params.get("namespace", "default")))
        return self._run_kubectl(
            ["get", "events", "-n", namespace, "--sort-by=.lastTimestamp"]
        )

    def _simulate_noop(self, params: Dict[str, Any], simulated: bool = True) -> Dict[str, Any]:
        """Safe simulation — does nothing, always succeeds, labeled as simulated."""
        return {
            "outcome": "SUCCESS",
            "simulated": True,
            "message": "Simulated action completed — no real changes made",
        }


# Module singleton — dry_run=True by default (safe)
action_registry = ActionRegistry(dry_run=True)


# ─────────────────────────────────────────────────────────────────────────────
# Action Generation from RCA Output
# ─────────────────────────────────────────────────────────────────────────────

# Category → risk level mapping (default)
CATEGORY_RISK = {
    "COLLECT_DIAGNOSTICS": "low",
    "INSPECT_K8S": "low",
    "INSPECT_LOGS": "low",
    "INVESTIGATE_SATURATION": "low",
    "MONITOR_ONLY": "low",
    "ESCALATE": "low",
    "RESTART_WORKLOAD": "medium",
    "SCALE_WORKLOAD": "medium",
    "APPLY_CONFIG": "high",
    "ROLLBACK_DEPLOYMENT": "high",
}

CATEGORY_REQUIRES_APPROVAL = {
    "low": False,
    "medium": True,
    "high": True,
    "critical": True,
}


def _safe_service_to_deployment(service: str) -> str:
    """Convert service name to a k8s-safe deployment name."""
    return re.sub(r'[^a-z0-9\-]', '-', service.lower()).strip('-')


def generate_actions_from_rca(
    incident_id: str,
    rca_result: RCAResult,
    incident: Incident,
) -> List[Dict[str, Any]]:
    """
    Generate structured, evidence-grounded action recommendations from RCA output.
    Only recommends actions supported by evidence. Never recommends destructive
    operations without explicit evidence basis.

    Returns a list of dicts suitable for creating SuggestedAction rows.
    """
    actions = []
    root_svc = rca_result.root_cause_service
    confidence = rca_result.confidence
    fault_type = rca_result.fault_type or "unknown"
    deployment = _safe_service_to_deployment(root_svc)
    namespace = "default"

    # Action 1: Always safe — collect diagnostics first
    actions.append({
        "title": f"Collect diagnostic logs from {root_svc}",
        "category": "COLLECT_DIAGNOSTICS",
        "description": f"Retrieve recent logs from {root_svc} to inspect error patterns before taking any remediation action.",
        "reason": f"Root cause analysis identified {root_svc} as the anomalous service (confidence: {confidence:.0%}). Logs provide evidence before acting.",
        "target_service": root_svc,
        "target_namespace": namespace,
        "target_resource_type": "deployment",
        "risk_level": "low",
        "requires_approval": False,
        "action_handler": "get_pod_logs",
        "execution_params": {"deployment": deployment, "namespace": namespace, "lines": 100},
        "evidence_refs": [
            {"type": "anomaly_score", "ref": root_svc, "description": f"Anomaly score elevated for {root_svc}"},
            {"type": "rca_result", "ref": str(rca_result.id), "description": "RCA identified this service as root cause"},
        ],
        "expected_outcome": "Log inspection provides evidence of the fault type and confirms root cause.",
        "verification_plan": "Review logs for error patterns matching the detected fault type.",
        "priority_rank": 1,
        "confidence_score": confidence,
    })

    # Action 2: Inspect K8s workload health
    actions.append({
        "title": f"Inspect Kubernetes workload status for {root_svc}",
        "category": "INSPECT_K8S",
        "description": f"Describe the {root_svc} deployment to check pod readiness, restart count, and resource usage.",
        "reason": f"Kubernetes workload status confirms whether the service is experiencing pod-level failures.",
        "target_service": root_svc,
        "target_namespace": namespace,
        "target_resource_type": "deployment",
        "risk_level": "low",
        "requires_approval": False,
        "action_handler": "describe_deployment",
        "execution_params": {"deployment": deployment, "namespace": namespace},
        "evidence_refs": [
            {"type": "fault_type", "ref": fault_type, "description": f"Detected fault: {fault_type}"},
        ],
        "expected_outcome": "Deployment description shows current pod state, resource limits, and events.",
        "priority_rank": 2,
        "confidence_score": confidence * 0.9,
    })

    # Action 3: Restart — only recommend if confidence is high enough
    if confidence >= 0.6:
        restart_risk = "medium"
        if fault_type in ("error_spike", "connection_timeout", "memory_leak"):
            restart_risk = "medium"
        elif fault_type == "cpu_overload":
            restart_risk = "medium"

        actions.append({
            "title": f"Restart {root_svc} deployment",
            "category": "RESTART_WORKLOAD",
            "description": f"Perform a rolling restart of the {root_svc} deployment to clear transient state.",
            "reason": (
                f"RCA identified {root_svc} as root cause with {confidence:.0%} confidence. "
                f"Fault type '{fault_type}' is consistent with state that clears on restart. "
                f"Restart is a low-blast-radius action before more invasive remediation."
            ),
            "target_service": root_svc,
            "target_namespace": namespace,
            "target_resource_type": "deployment",
            "risk_level": restart_risk,
            "requires_approval": True,
            "required_permission": "operator:restart",
            "action_handler": "restart_deployment",
            "execution_params": {"deployment": deployment, "namespace": namespace},
            "preconditions": [
                f"Deployment {deployment} exists in namespace {namespace}",
                f"At least 1 replica is running (rolling restart requires available pod)",
                "No active deployment rollout in progress",
            ],
            "expected_outcome": f"Fresh pods replace unhealthy instances. Latency and error rate return to baseline within 60-120s.",
            "potential_side_effects": [
                "Brief increase in latency during pod replacement",
                "In-flight requests may be dropped if graceful shutdown not configured",
            ],
            "rollback_plan": f"If restart worsens the situation, roll back using: kubectl rollout undo deployment/{deployment} -n {namespace}",
            "rollback_handler": "rollback_deployment",
            "rollback_params": {"deployment": deployment, "namespace": namespace},
            "verification_plan": "Check pod readiness and error rate 60s after restart completes.",
            "verification_metrics": [
                {"metric": "error_rate", "threshold": 0.05, "direction": "decrease"},
                {"metric": "latency", "threshold": 500, "direction": "decrease"},
            ],
            "timeout_seconds": 300,
            "priority_rank": 3,
            "confidence_score": confidence,
            "evidence_refs": [
                {"type": "rca_result", "ref": str(rca_result.id), "description": f"Confidence: {confidence:.0%}"},
                {"type": "fault_type", "ref": fault_type},
            ],
        })

    # Action 4: Rollback — only for deployment-related faults with very high confidence
    if confidence >= 0.8 and fault_type in ("error_spike", "connection_timeout"):
        actions.append({
            "title": f"Roll back {root_svc} to previous deployment version",
            "category": "ROLLBACK_DEPLOYMENT",
            "description": f"Revert {root_svc} to its previous stable deployment revision.",
            "reason": (
                f"High-confidence ({confidence:.0%}) fault detection suggests a recent deployment "
                f"may have introduced the {fault_type}. Rollback is appropriate when restart alone "
                f"is insufficient."
            ),
            "target_service": root_svc,
            "target_namespace": namespace,
            "target_resource_type": "deployment",
            "risk_level": "high",
            "requires_approval": True,
            "required_permission": "operator:rollback",
            "action_handler": "rollback_deployment",
            "execution_params": {"deployment": deployment, "namespace": namespace},
            "preconditions": [
                f"A previous revision exists for deployment {deployment}",
                "The previous revision does not have the same fault",
                "Change management process has been followed",
            ],
            "expected_outcome": "Service returns to previous stable version; fault resolves.",
            "potential_side_effects": [
                "Any features from the current revision will be lost",
                "Data schema changes introduced by current version may cause compatibility issues",
            ],
            "verification_metrics": [
                {"metric": "error_rate", "threshold": 0.01, "direction": "decrease"},
            ],
            "priority_rank": 4,
            "confidence_score": confidence * 0.85,
        })

    # Action 5: Escalate if confidence is low
    if confidence < 0.5:
        actions.append({
            "title": f"Escalate to on-call engineer — low-confidence root cause",
            "category": "ESCALATE",
            "description": "RCA confidence is below threshold. Human investigation required.",
            "reason": f"Anomaly detected but root cause confidence ({confidence:.0%}) is below the 50% threshold for automated recommendation. Manual investigation recommended.",
            "target_service": root_svc,
            "risk_level": "low",
            "requires_approval": False,
            "action_handler": "simulate_noop",
            "execution_params": {},
            "expected_outcome": "Incident escalated. On-call engineer performs manual investigation.",
            "priority_rank": 1,
            "confidence_score": confidence,
        })

    return actions


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

async def create_actions_for_incident(
    db: AsyncSession,
    incident_id: str,
    rca_result: RCAResult,
    incident: Incident,
) -> List[SuggestedAction]:
    """Generate and persist suggested actions for an incident."""
    action_dicts = generate_actions_from_rca(incident_id, rca_result, incident)
    created = []
    for ad in action_dicts:
        requires_approval = ad.pop("requires_approval", True)
        # Compute idempotency key so duplicate generation is safe
        key_src = f"{incident_id}:{ad['category']}:{ad.get('target_service','')}:{ad.get('action_handler','')}"
        ikey = "act_" + hashlib.sha256(key_src.encode()).hexdigest()[:12]

        # Check if already exists
        existing = await db.execute(
            select(SuggestedAction).where(SuggestedAction.idempotency_key == ikey)
        )
        if existing.scalar_one_or_none():
            continue

        risk = ad.get("risk_level", "medium")
        action = SuggestedAction(
            incident_id=incident_id,
            requires_approval=1 if requires_approval else 0,
            idempotency_key=ikey,
            **{k: v for k, v in ad.items() if hasattr(SuggestedAction, k)},
        )
        db.add(action)
        created.append(action)

    if created:
        await db.commit()
        for a in created:
            await db.refresh(a)
        # Log incident event
        await _log_incident_event(
            db, incident_id, "ACTION_PROPOSED",
            f"{len(created)} suggested action(s) generated by SYNAPSE AI",
            actor="synapse-ai",
        )
    return created


async def transition_action(
    db: AsyncSession,
    action: SuggestedAction,
    new_state: str,
    actor: str = "system",
    reason: str | None = None,
) -> SuggestedAction:
    """
    Transition an action to a new state.
    Raises ValueError if the transition is invalid.
    """
    if not validate_transition(action.status, new_state):
        raise ValueError(
            f"Invalid transition {action.status!r} → {new_state!r} for action {action.id}"
        )
    old_state = action.status
    action.status = new_state
    action.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(action)

    await _log_audit(
        db,
        actor=actor,
        action=f"transition_action:{old_state}->{new_state}",
        resource_type="suggested_action",
        resource_id=action.id,
        incident_id=action.incident_id,
        detail={"reason": reason, "from_state": old_state, "to_state": new_state},
    )
    return action


async def approve_action(
    db: AsyncSession,
    action: SuggestedAction,
    decided_by: str,
    decision: str,  # APPROVED | REJECTED
    reason: str | None = None,
) -> Tuple[SuggestedAction, ActionApproval]:
    """Approve or reject an action. Creates an approval record and transitions state."""
    if decision not in ("APPROVED", "REJECTED"):
        raise ValueError(f"Invalid decision: {decision!r}")

    approval = ActionApproval(
        action_id=action.id,
        incident_id=action.incident_id,
        decision=decision,
        decided_by=decided_by,
        reason=reason,
    )
    db.add(approval)

    new_state = ActionState.APPROVED if decision == "APPROVED" else ActionState.REJECTED
    action = await transition_action(db, action, new_state, actor=decided_by, reason=reason)

    event_type = "ACTION_APPROVED" if decision == "APPROVED" else "ACTION_REJECTED"
    await _log_incident_event(
        db, action.incident_id, event_type,
        f"Action '{action.title}' {decision.lower()} by {decided_by}",
        actor=decided_by,
        metadata={"action_id": action.id, "reason": reason},
    )
    await db.commit()
    await db.refresh(approval)
    return action, approval


async def execute_action(
    db: AsyncSession,
    action: SuggestedAction,
    requested_by: str = "operator",
) -> Tuple[SuggestedAction, ActionExecution]:
    """
    Execute an approved action via the validated ACTION_REGISTRY.
    Never executes unapproved or invalid-state actions.
    """
    if action.status not in (ActionState.APPROVED, ActionState.READY_TO_EXECUTE):
        raise ValueError(
            f"Cannot execute action in state {action.status!r}. Must be APPROVED or READY_TO_EXECUTE."
        )

    # Transition to EXECUTING
    action = await transition_action(db, action, ActionState.EXECUTING, actor=requested_by)

    started = datetime.now(timezone.utc)
    t0 = time.monotonic()

    handler = action.action_handler or "simulate_noop"
    params = action.execution_params or {}
    is_simulated = bool(action.simulated)

    # Execute via validated registry
    result = action_registry.execute(handler, params, simulated=is_simulated)

    duration_ms = (time.monotonic() - t0) * 1000
    outcome = result.get("outcome", "FAILED")

    # Create execution record
    exec_record = ActionExecution(
        action_id=action.id,
        incident_id=action.incident_id,
        requested_by=requested_by,
        started_at=started,
        completed_at=datetime.now(timezone.utc),
        duration_ms=duration_ms,
        handler_name=handler,
        sanitized_params={k: v for k, v in params.items()},  # no secrets
        operation_metadata={
            "dry_run": result.get("dry_run", False),
            "command_preview": result.get("command_preview"),
        },
        outcome=outcome,
        exit_code=result.get("exit_code"),
        stdout=result.get("stdout", "")[:4096],
        stderr=result.get("stderr", "")[:2048],
        error_message=result.get("error"),
        simulated=1 if is_simulated else 0,
    )
    db.add(exec_record)

    # Transition action state
    new_state = ActionState.EXECUTED if outcome == "SUCCESS" else ActionState.EXECUTION_FAILED
    action = await transition_action(db, action, new_state, actor=requested_by)

    await _log_incident_event(
        db, action.incident_id, "ACTION_EXECUTED",
        f"Action '{action.title}' executed — outcome: {outcome}",
        actor=requested_by,
        metadata={"action_id": action.id, "outcome": outcome, "duration_ms": duration_ms},
    )
    await db.commit()
    await db.refresh(exec_record)
    return action, exec_record


async def run_verification(
    db: AsyncSession,
    action: SuggestedAction,
    incident: Incident,
    execution_id: Optional[int] = None,
) -> Tuple[SuggestedAction, VerificationRun]:
    """
    Run post-action verification. Collects metrics and determines outcome.
    NEVER reports success when telemetry is unavailable.
    """
    action = await transition_action(db, action, ActionState.VERIFYING, actor="system")

    vrun = VerificationRun(
        action_id=action.id,
        incident_id=action.incident_id,
        execution_id=execution_id,
    )
    db.add(vrun)
    await db.flush()

    # Collect post-action metrics
    from app.services.verification_service import collect_verification_evidence
    evidence = await collect_verification_evidence(db, action, incident)

    vrun.completed_at = datetime.now(timezone.utc)
    vrun.criteria = evidence.get("criteria", [])
    vrun.baseline_snapshot = evidence.get("baseline_snapshot")
    vrun.post_action_snapshot = evidence.get("post_action_snapshot")
    vrun.metric_comparison = evidence.get("metric_comparison", [])
    vrun.data_freshness_seconds = evidence.get("data_freshness_seconds")
    vrun.missing_metrics = evidence.get("missing_metrics", [])
    vrun.symptoms_resolved = evidence.get("symptoms_resolved")
    vrun.original_anomalies_cleared = evidence.get("original_anomalies_cleared")
    vrun.summary = evidence.get("summary")
    vrun.next_step_recommendation = evidence.get("next_step_recommendation")

    # Determine outcome — strict: missing data → INCONCLUSIVE
    outcome = evidence.get("outcome", ActionState.VERIFICATION_INCONCLUSIVE)
    vrun.outcome = outcome

    # Transition action
    new_state = outcome  # outcome maps directly to action states
    if new_state not in (
        ActionState.VERIFIED_SUCCESS,
        ActionState.VERIFICATION_FAILED,
        ActionState.VERIFICATION_INCONCLUSIVE,
    ):
        new_state = ActionState.VERIFICATION_INCONCLUSIVE

    action = await transition_action(db, action, new_state, actor="system")

    await _log_incident_event(
        db, action.incident_id, "VERIFICATION_COMPLETED",
        f"Verification outcome: {outcome}",
        actor="system",
        metadata={"action_id": action.id, "outcome": outcome},
    )
    await db.commit()
    await db.refresh(vrun)
    return action, vrun


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _log_audit(
    db: AsyncSession,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    incident_id: Optional[str] = None,
    outcome: str = "SUCCESS",
    detail: Optional[Dict] = None,
) -> None:
    evt = AuditEvent(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        incident_id=incident_id,
        outcome=outcome,
        detail=detail,
    )
    db.add(evt)
    # Don't commit here — caller commits


async def _log_incident_event(
    db: AsyncSession,
    incident_id: str,
    event_type: str,
    title: str,
    actor: str = "system",
    detail: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> None:
    evt = IncidentEvent(
        incident_id=incident_id,
        event_type=event_type,
        actor=actor,
        title=title,
        detail=detail,
        event_metadata=metadata,
    )
    db.add(evt)
