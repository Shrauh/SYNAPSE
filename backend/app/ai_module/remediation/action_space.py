"""
SYNAPSE Remediation — Action Space Definition.

Defines all 6 auto-remediation actions with metadata:
  - when to use (fault types)
  - confidence threshold for auto-execution
  - whether human approval is always required
  - kubectl command or equivalent
  - estimated remediation time in seconds
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class RemediationAction:
    """A single auto-remediation action definition."""

    action_id: str              # Unique identifier
    name: str                   # Human-readable name
    description: str            # What this action does
    command_template: str       # kubectl/k8s command template
    applicable_faults: List[str]  # Fault types this action handles
    auto_execute_threshold: float  # CQL confidence required for auto-exec
    always_require_approval: bool  # If True, always ask human regardless of confidence
    estimated_time_sec: int     # Estimated time to complete
    risk_level: str             # "low" | "medium" | "high"


# ── Action Definitions (from Section 8 of project spec) ──────────────────

SCALE_UP = RemediationAction(
    action_id="SCALE_UP",
    name="Scale Up Deployment",
    description="Increase replica count to 3 to handle higher load",
    command_template="kubectl scale deployment/{service} --replicas=3 -n {namespace}",
    applicable_faults=["cpu_stress", "retry_storm", "high_throughput"],
    auto_execute_threshold=0.85,
    always_require_approval=False,
    estimated_time_sec=30,
    risk_level="low",
)

RESTART_POD = RemediationAction(
    action_id="RESTART_POD",
    name="Restart Pod",
    description="Rolling restart of the deployment to clear bad state",
    command_template="kubectl rollout restart deployment/{service} -n {namespace}",
    applicable_faults=["oom_kill", "memory_leak", "pod_crash"],
    auto_execute_threshold=0.85,
    always_require_approval=False,
    estimated_time_sec=45,
    risk_level="low",
)

ROLLBACK = RemediationAction(
    action_id="ROLLBACK",
    name="Rollback Deployment",
    description="Roll back to previous stable deployment revision",
    command_template="kubectl rollout undo deployment/{service} -n {namespace}",
    applicable_faults=["config_error", "bad_deploy"],
    auto_execute_threshold=0.90,   # Higher confidence required
    always_require_approval=False,
    estimated_time_sec=60,
    risk_level="medium",
)

CIRCUIT_BREAK = RemediationAction(
    action_id="CIRCUIT_BREAK",
    name="Enable Circuit Breaker",
    description="Update ConfigMap to enable circuit breaker pattern",
    command_template=(
        "kubectl patch configmap/{service}-config -n {namespace} "
        "--patch '{\"data\":{\"circuit_breaker_enabled\":\"true\"}}'"
    ),
    applicable_faults=["cascade_failure", "retry_storm"],
    auto_execute_threshold=1.1,   # > 1.0 = never auto-execute (always approval)
    always_require_approval=True,
    estimated_time_sec=15,
    risk_level="high",
)

DRAIN_TRAFFIC = RemediationAction(
    action_id="DRAIN_TRAFFIC",
    name="Drain Node Traffic",
    description="Cordon and drain the failing node to migrate workloads",
    command_template="kubectl cordon node/{node} -n {namespace}",
    applicable_faults=["node_failure", "hardware_failure"],
    auto_execute_threshold=1.1,   # Always requires approval
    always_require_approval=True,
    estimated_time_sec=120,
    risk_level="high",
)

INCREASE_POOL = RemediationAction(
    action_id="INCREASE_POOL",
    name="Increase DB Connection Pool",
    description="Update DB connection pool size via ConfigMap",
    command_template=(
        "kubectl patch configmap/{service}-config -n {namespace} "
        "--patch '{\"data\":{\"db_pool_size\":\"50\"}}'"
    ),
    applicable_faults=["db_exhaustion"],
    auto_execute_threshold=0.85,
    always_require_approval=False,
    estimated_time_sec=10,
    risk_level="low",
)


# ── Registry ───────────────────────────────────────────────────────────────

ALL_ACTIONS: List[RemediationAction] = [
    SCALE_UP,
    RESTART_POD,
    ROLLBACK,
    CIRCUIT_BREAK,
    DRAIN_TRAFFIC,
    INCREASE_POOL,
]

ACTION_REGISTRY = {action.action_id: action for action in ALL_ACTIONS}

# Fault → best action mapping (used by rule-based fallback)
FAULT_TO_ACTION = {
    "cpu_stress":       SCALE_UP,
    "retry_storm":      CIRCUIT_BREAK,
    "high_throughput":  SCALE_UP,
    "oom_kill":         RESTART_POD,
    "memory_leak":      RESTART_POD,
    "pod_crash":        RESTART_POD,
    "config_error":     ROLLBACK,
    "bad_deploy":       ROLLBACK,
    "cascade_failure":  CIRCUIT_BREAK,
    "db_exhaustion":    INCREASE_POOL,
    "node_failure":     DRAIN_TRAFFIC,
    "dns_failure":      RESTART_POD,
    "network_latency":  SCALE_UP,
    "latency_spike":    SCALE_UP,
    "error_burst":      RESTART_POD,
    "resource_exhaustion": RESTART_POD,
}
