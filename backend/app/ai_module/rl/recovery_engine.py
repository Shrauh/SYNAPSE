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

class ActionType(Enum):
    """Enumeration of possible recovery action types."""
    RESTART_POD = 'restart_pod'
    SCALE_UP = 'scale_up'
    SCALE_DOWN = 'scale_down'
    RATE_LIMIT = 'rate_limit'
    CIRCUIT_BREAK = 'circuit_break'
    DO_NOTHING = 'do_nothing'

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
    FAULT_ACTION_MAP = {
        'latency_spike': ActionType.SCALE_UP,
        'error_spike': ActionType.RESTART_POD,
        'cpu_overload': ActionType.SCALE_UP,
        'memory_leak': ActionType.RESTART_POD,
        'connection_timeout': ActionType.CIRCUIT_BREAK,
        'cascading_failure': ActionType.RATE_LIMIT,
    }
    
    KUBECTL_TEMPLATES = {
        ActionType.RESTART_POD: 'kubectl rollout restart deployment/{service} -n default',
        ActionType.SCALE_UP: 'kubectl scale deployment/{service} --replicas={replicas} -n default',
        ActionType.SCALE_DOWN: 'kubectl scale deployment/{service} --replicas={replicas} -n default',
        ActionType.RATE_LIMIT: 'kubectl apply -f istio-rate-limit-{service}.yaml',
        ActionType.CIRCUIT_BREAK: 'kubectl apply -f istio-circuit-breaker-{service}.yaml',
        ActionType.DO_NOTHING: '# No action taken — confidence too low',
    }
    
    def __init__(self):
        """Initialize the recovery engine."""
        self._action_history: List[ActionResult] = []
        self._confidence_threshold = 0.6
    
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
        # L3/L4: Don't auto-fix
        if severity_level >= 3:
            return RecoveryAction(
                action_type=ActionType.DO_NOTHING, 
                target_service=root_cause_service, 
                confidence=0.0, 
                reason=f'Severity L{severity_level}: Escalating to engineer, auto-fix too risky'
            )
        
        # Low confidence: Don't auto-fix
        if causal_confidence < self._confidence_threshold:
            return RecoveryAction(
                action_type=ActionType.DO_NOTHING, 
                target_service=root_cause_service, 
                confidence=causal_confidence, 
                reason=f'Confidence {causal_confidence:.2f} below threshold {self._confidence_threshold}'
            )
        
        # L1/L2: Select action based on fault type
        action_type = self.FAULT_ACTION_MAP.get(fault_type, ActionType.RESTART_POD)
        
        params = {}
        if action_type in (ActionType.SCALE_UP,):
            params['replicas'] = 4
        elif action_type in (ActionType.SCALE_DOWN,):
            params['replicas'] = 1
        
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
        kubectl_cmd = self.KUBECTL_TEMPLATES.get(action.action_type, '# unknown action').format(
            service=action.target_service, **action.parameters
        )
        
        # Simulate execution
        simulated_success = action.action_type != ActionType.DO_NOTHING
        exec_time = random.uniform(1000, 5000) if simulated_success else 0
        
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
            if target in post_anomaly_scores and post_anomaly_scores[target] < 0.5:
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
