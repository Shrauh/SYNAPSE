"""
Severity classifier for incident management.

Classifies incidents into 4 levels based on the number of anomalous services,
causal confidence, and recurring patterns.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime, timezone

class SeverityLevel(Enum):
    """Enumeration of incident severity levels."""
    L1_SIMPLE = 1        # Single service, known pattern, high confidence
    L2_CASCADING = 2     # 2-3 services, cascading chain, good confidence
    L3_SYSTEMIC = 3      # 4+ services, low confidence OR unknown pattern
    L4_DESIGN_FLAW = 4   # Recurring pattern (same root cause > 3 times in 30 days)

@dataclass
class SeverityResult:
    """Represents the outcome of a severity classification."""
    level: SeverityLevel
    reason: str
    num_anomalous: int
    causal_confidence: float
    is_recurring: bool
    recurring_count: int
    response_strategy: str  # 'auto_fix', 'root_first', 'escalate', 'recommend'

class SeverityClassifier:
    """Classifies the severity of incidents and tracks history."""
    def __init__(self):
        """Initialize the severity classifier with an empty incident history."""
        self._incident_history: List[dict] = []  # In-memory for now
    
    def classify(
        self, 
        anomaly_scores: Dict[str, float], 
        causal_confidence: float, 
        root_cause_service: Optional[str] = None, 
        threshold: float = 0.5
    ) -> SeverityResult:
        """Classify an incident into a SeverityLevel.
        
        Args:
            anomaly_scores: Dictionary mapping service names to anomaly scores.
            causal_confidence: Confidence score of the root cause.
            root_cause_service: The identified root cause service.
            threshold: Anomaly score threshold.
            
        Returns:
            SeverityResult containing the classification details.
        """
        # Count anomalous services
        num_anomalous = sum(1 for s in anomaly_scores.values() if s > threshold)
        
        # Check if this root cause is recurring
        is_recurring, recurring_count = self._check_recurring(root_cause_service)
        
        # L4: Recurring design flaw (same root cause > 3 times)
        if is_recurring and recurring_count > 3:
            return SeverityResult(
                level=SeverityLevel.L4_DESIGN_FLAW, 
                reason=f'Root cause {root_cause_service} has recurred {recurring_count} times', 
                num_anomalous=num_anomalous, 
                causal_confidence=causal_confidence, 
                is_recurring=True, 
                recurring_count=recurring_count, 
                response_strategy='recommend'
            )
        
        # L3: Systemic (4+ services OR low confidence)
        if num_anomalous >= 4 or causal_confidence < 0.5:
            return SeverityResult(
                level=SeverityLevel.L3_SYSTEMIC, 
                reason=f'{num_anomalous} services anomalous, confidence={causal_confidence:.2f}', 
                num_anomalous=num_anomalous, 
                causal_confidence=causal_confidence, 
                is_recurring=is_recurring, 
                recurring_count=recurring_count, 
                response_strategy='escalate'
            )
        
        # L2: Cascading (2-3 services)
        if num_anomalous >= 2:
            return SeverityResult(
                level=SeverityLevel.L2_CASCADING, 
                reason=f'{num_anomalous} services in cascade, confidence={causal_confidence:.2f}', 
                num_anomalous=num_anomalous, 
                causal_confidence=causal_confidence, 
                is_recurring=is_recurring, 
                recurring_count=recurring_count, 
                response_strategy='root_first'
            )
        
        # L1: Simple (1 service, high confidence)
        return SeverityResult(
            level=SeverityLevel.L1_SIMPLE, 
            reason=f'Single service fault, confidence={causal_confidence:.2f}', 
            num_anomalous=num_anomalous, 
            causal_confidence=causal_confidence, 
            is_recurring=is_recurring, 
            recurring_count=recurring_count, 
            response_strategy='auto_fix'
        )
    
    def record_incident(self, root_cause_service: str, severity: SeverityLevel, resolved: bool = False) -> None:
        """Record an incident in the history.
        
        Args:
            root_cause_service: The identified root cause service.
            severity: The classified severity level.
            resolved: Whether the incident is resolved.
        """
        self._incident_history.append({
            'root_cause': root_cause_service, 
            'severity': severity.value, 
            'timestamp': datetime.now(timezone.utc).isoformat(), 
            'resolved': resolved
        })
    
    def _check_recurring(self, root_cause_service: Optional[str]) -> Tuple[bool, int]:
        """Check if a root cause is recurring.
        
        Args:
            root_cause_service: The service to check.
            
        Returns:
            Tuple containing boolean indicating recurrence and the total count.
        """
        if not root_cause_service:
            return False, 0
        count = sum(1 for h in self._incident_history if h['root_cause'] == root_cause_service)
        return count >= 2, count
    
    def get_history(self) -> List[dict]:
        """Get a copy of the incident history.
        
        Returns:
            List of incident records.
        """
        return self._incident_history.copy()
    
    def get_recurring_patterns(self) -> Dict[str, int]:
        """Get recurring root cause patterns.
        
        Returns:
            Dictionary mapping service names to their occurrence counts.
        """
        from collections import Counter
        counts = Counter(h['root_cause'] for h in self._incident_history)
        return {svc: cnt for svc, cnt in counts.items() if cnt >= 2}

# Module-level singleton
severity_classifier = SeverityClassifier()
