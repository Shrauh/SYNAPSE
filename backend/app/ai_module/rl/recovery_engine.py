"""
Recovery execution engine for automated remediation.

Selects and executes (simulated) recovery actions based on severity level
and fault types.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import random

# ──────────────────────────────────────────────
# Remediation Constants & Thresholds
# ──────────────────────────────────────────────

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.3
"""Confidence threshold below which recovery action is flagged as low-confidence best-effort mitigation."""

ESCALATION_SEVERITY_LEVEL: int = 4
"""Severity level threshold at or above which automated remediation escalates to SRE."""

DEFAULT_SCALE_UP_REPLICAS: int = 4
"""Default target replica count for SCALE_UP remediation action."""

DEFAULT_SCALE_DOWN_REPLICAS: int = 1
"""Default target replica count for SCALE_DOWN remediation action."""

DEFAULT_FALLBACK_REPLICAS: int = 2
"""Safe fallback replica count when executing scaled commands without specified parameter."""

SIMULATED_EXEC_TIME_MIN_MS: float = 1000.0
"""Minimum simulated execution duration in milliseconds for realistic latency modeling."""

SIMULATED_EXEC_TIME_MAX_MS: float = 5000.0
"""Maximum simulated execution duration in milliseconds for realistic latency modeling."""

RECOVERY_VERIFICATION_THRESHOLD: float = 0.5
"""Post-action anomaly score threshold below which a service is considered successfully recovered."""

DEFAULT_K8S_NAMESPACE: str = "default"
"""Default Kubernetes namespace used in remediation commands."""


class ActionType(Enum):
    """Enumeration of possible recovery action types."""
    RESTART_POD = 'restart_pod'
    SCALE_UP = 'scale_up'
    SCALE_DOWN = 'scale_down'
    RATE_LIMIT = 'rate_limit'
    CIRCUIT_BREAK = 'circuit_break'
    DO_NOTHING = 'do_nothing'


# Complete fault type to action mapping (learned rules)
DEFAULT_FAULT_ACTION_MAP: Dict[str, ActionType] = {
    'latency_spike': ActionType.RESTART_POD,
    'error_spike': ActionType.RESTART_POD,
    'error_burst': ActionType.SCALE_UP,
    'cpu_overload': ActionType.SCALE_UP,
    'memory_leak': ActionType.RESTART_POD,
    'connection_timeout': ActionType.CIRCUIT_BREAK,
    'disk_pressure': ActionType.RESTART_POD,
    'network_partition': ActionType.CIRCUIT_BREAK,
    'cascading_failure': ActionType.RATE_LIMIT,
    'resource_exhaustion': ActionType.SCALE_UP,
}
"""Mapping of incident fault types to their automated remediation action types."""

DEFAULT_KUBECTL_TEMPLATES: Dict[ActionType, str] = {
    ActionType.RESTART_POD: 'kubectl rollout restart deployment/{service} -n {namespace}',
    ActionType.SCALE_UP: 'kubectl scale deployment/{service} --replicas={replicas} -n {namespace}',
    ActionType.SCALE_DOWN: 'kubectl scale deployment/{service} --replicas={replicas} -n {namespace}',
    ActionType.RATE_LIMIT: 'kubectl apply -f istio-rate-limit-{service}.yaml -n {namespace}',
    ActionType.CIRCUIT_BREAK: 'kubectl apply -f istio-circuit-breaker-{service}.yaml -n {namespace}',
    ActionType.DO_NOTHING: '# No action taken — confidence too low',
}
"""Kubectl CLI command templates for simulated remediation actions."""


@dataclass
class RecoveryAction:
    """Represents a selected recovery action to execute."""
    action_type: ActionType
    target_service: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    reason: str = ''

@dataclass 
class ActionResult:
    """Represents the result of an executed recovery action."""
    action: RecoveryAction
    success: bool
    execution_time_ms: float
    message: str
    simulated: bool = True
    kubectl_command: str = ''
    timestamp: str = ''

class RecoveryEngine:
    """Selects and executes (simulated) recovery actions based on severity level."""
    
    # Fault type to action mapping (learned rules)
    FAULT_ACTION_MAP = DEFAULT_FAULT_ACTION_MAP
    
    KUBECTL_TEMPLATES = DEFAULT_KUBECTL_TEMPLATES
    
    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD):
        """Initialize the recovery engine."""
        self._action_history: List[ActionResult] = []
        self._confidence_threshold = confidence_threshold
    
    def select_action(
        self, 
        severity_level: int, 
        root_cause_service: str, 
        fault_type: Optional[str] = None, 
        causal_confidence: float = 0.0, 
        propagation_chain: Optional[List[str]] = None
    ) -> RecoveryAction:
        """Select appropriate recovery action based on context.
        
        Args:
            severity_level: The classified severity level.
            root_cause_service: The identified root cause service.
            fault_type: The type of fault detected.
            causal_confidence: Confidence score of the root cause.
            propagation_chain: List of services in the propagation chain.
            
        Returns:
            Selected RecoveryAction.
        """
        # L4 only: Don't auto-fix catastrophic / design-flaw issues
        if severity_level >= ESCALATION_SEVERITY_LEVEL:
            return RecoveryAction(
                action_type=ActionType.RESTART_POD, 
                target_service=root_cause_service, 
                confidence=causal_confidence, 
                reason=f'Severity L{severity_level}: Escalating to SRE — applying conservative restart_pod as interim mitigation'
            )
        
        # Low confidence: still suggest an action but note the low confidence
        if causal_confidence < self._confidence_threshold:
            action_type = self.FAULT_ACTION_MAP.get(fault_type, ActionType.RESTART_POD)
            return RecoveryAction(
                action_type=action_type, 
                target_service=root_cause_service, 
                confidence=causal_confidence, 
                reason=f'Low confidence ({causal_confidence:.2f}) — applying {action_type.value} as best-effort mitigation'
            )
        
        # L1/L2: Select action based on fault type
        action_type = self.FAULT_ACTION_MAP.get(fault_type, ActionType.RESTART_POD)
        
        params = {}
        if action_type in (ActionType.SCALE_UP,):
            params['replicas'] = DEFAULT_SCALE_UP_REPLICAS
        elif action_type in (ActionType.SCALE_DOWN,):
            params['replicas'] = DEFAULT_SCALE_DOWN_REPLICAS
        
        return RecoveryAction(
            action_type=action_type, 
            target_service=root_cause_service, 
            parameters=params, 
            confidence=causal_confidence, 
            reason=f'L{severity_level} fault: {fault_type} → {action_type.value}'
        )
    
    def execute_action(self, action: RecoveryAction) -> ActionResult:
        """Execute a recovery action (SIMULATED — prints kubectl command).
        
        Args:
            action: The recovery action to execute.
            
        Returns:
            ActionResult indicating success or failure.
        """
        safe_params = {
            "replicas": DEFAULT_FALLBACK_REPLICAS,
            "namespace": DEFAULT_K8S_NAMESPACE,
            **action.parameters,
        }
        kubectl_cmd = self.KUBECTL_TEMPLATES.get(action.action_type, '# unknown action').format(
            service=action.target_service, **safe_params
        )
        
        # Simulate execution
        simulated_success = action.action_type != ActionType.DO_NOTHING
        exec_time = random.uniform(SIMULATED_EXEC_TIME_MIN_MS, SIMULATED_EXEC_TIME_MAX_MS) if simulated_success else 0.0
        
        result = ActionResult(
            action=action,
            success=simulated_success,
            execution_time_ms=round(exec_time, 1),
            message=f'[SIMULATED] {kubectl_cmd}' if simulated_success else 'No action executed',
            simulated=True,
            kubectl_command=kubectl_cmd,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        self._action_history.append(result)
        print(f'[Recovery] {result.message}')
        return result
    
    def verify_recovery(self, action_result: ActionResult, post_anomaly_scores: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Verify if recovery action resolved the issue.
        
        Args:
            action_result: The result of the executed action.
            post_anomaly_scores: Anomaly scores after the action was taken.
            
        Returns:
            Dictionary containing verification result and reason.
        """
        if not action_result.success:
            return {'recovered': False, 'reason': 'No action was executed'}
        
        if post_anomaly_scores:
            target = action_result.action.target_service
            if target in post_anomaly_scores and post_anomaly_scores[target] < RECOVERY_VERIFICATION_THRESHOLD:
                return {'recovered': True, 'reason': f'{target} anomaly score dropped to {post_anomaly_scores[target]:.2f}'}
            else:
                return {'recovered': False, 'reason': f'{target} still anomalous after action'}
        
        # If no post-scores, assume simulated success
        return {'recovered': True, 'reason': 'Simulated recovery successful'}
    
    def get_action_history(self) -> List[Dict[str, Any]]:
        """Get the history of executed actions.
        
        Returns:
            List of action dictionaries.
        """
        return [{
            'action': r.action.action_type.value, 
            'service': r.action.target_service, 
            'success': r.success, 
            'kubectl': r.kubectl_command, 
            'time_ms': r.execution_time_ms, 
            'timestamp': r.timestamp
        } for r in self._action_history]
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the recovery engine.
        
        Returns:
            Dictionary with status details.
        """
        return {
            'total_actions': len(self._action_history), 
            'successful': sum(1 for r in self._action_history if r.success), 
            'confidence_threshold': self._confidence_threshold, 
            'supported_actions': [a.value for a in ActionType]
        }

# Module-level singleton
recovery_engine = RecoveryEngine()
