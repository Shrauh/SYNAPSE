"""
Severity classifier for incident management.

Classifies incidents into 4 levels based on the number of anomalous services,
causal confidence, and recurring patterns.

Level definitions (from tests — authoritative spec):
  L1_SIMPLE     : 1 anomalous service, confidence >= 0.5
  L2_CASCADING  : 2-3 anomalous services, confidence >= 0.5
  L3_SYSTEMIC   : 4+ services OR confidence < 0.5 (uncertain root cause)
  L4_DESIGN_FLAW: recurring root cause > 3 times in history
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
            threshold: Anomaly score threshold (default 0.5).

        Returns:
            SeverityResult containing the classification details.

        Specification (from test suite — authoritative):
          L4 triggers only on recurring root cause (> 3 times), not on ratio.
          L3 triggers on >= 4 anomalous services OR causal_confidence < 0.5.
          L2 triggers on 2-3 anomalous services (with confidence >= 0.5).
          L1 is the default (1 anomalous service, good confidence).
        """
        # Count anomalous services above threshold
        num_anomalous = sum(1 for s in anomaly_scores.values() if s > threshold)

        # Check if this root cause is recurring
        is_recurring, recurring_count = self._check_recurring(root_cause_service)

        # L4: Design flaw — recurring root cause only (> 3 times in history).
        # NOTE: High service-ratio alone does NOT trigger L4; use L3 for that.
        if is_recurring and recurring_count > 3:
            return SeverityResult(
                level=SeverityLevel.L4_DESIGN_FLAW,
                reason=(
                    f'DESIGN FLAW: {root_cause_service} has triggered {recurring_count} incidents — '
                    f'indicates systemic architectural vulnerability'
                ),
                num_anomalous=num_anomalous,
                causal_confidence=causal_confidence,
                is_recurring=is_recurring,
                recurring_count=recurring_count,
                response_strategy='recommend'
            )

        # L3: Systemic — 4+ services anomalous OR confidence too low to isolate root cause.
        # Using absolute count (>= 4) so 2-3 service systems do not over-escalate.
        if num_anomalous >= 4 or causal_confidence < 0.5:
            return SeverityResult(
                level=SeverityLevel.L3_SYSTEMIC,
                reason=(
                    f'SYSTEMIC: {num_anomalous} services degraded '
                    f'(confidence={causal_confidence:.2f}) — escalation required'
                ),
                num_anomalous=num_anomalous,
                causal_confidence=causal_confidence,
                is_recurring=is_recurring,
                recurring_count=recurring_count,
                response_strategy='escalate'
            )

        # L2: Cascading — 2-3 services affected with reasonable confidence
        if num_anomalous >= 2:
            max_score_svc = max(anomaly_scores, key=anomaly_scores.get)
            max_score = anomaly_scores[max_score_svc]
            return SeverityResult(
                level=SeverityLevel.L2_CASCADING,
                reason=(
                    f'CASCADING: {num_anomalous} services in failure chain — '
                    f'peak anomaly {max_score:.2f} on {max_score_svc} '
                    f'(confidence={causal_confidence:.2f})'
                ),
                num_anomalous=num_anomalous,
                causal_confidence=causal_confidence,
                is_recurring=is_recurring,
                recurring_count=recurring_count,
                response_strategy='root_first'
            )

        # L1: Simple — single service issue with high confidence
        max_score_svc = max(anomaly_scores, key=anomaly_scores.get) if anomaly_scores else ''
        max_score = anomaly_scores.get(max_score_svc, 0.0)
        return SeverityResult(
            level=SeverityLevel.L1_SIMPLE,
            reason=(
                f'SIMPLE: Single service anomaly on {root_cause_service} — '
                f'anomaly score {max_score:.2f} '
                f'(confidence={causal_confidence:.2f})'
            ),
            num_anomalous=num_anomalous,
            causal_confidence=causal_confidence,
            is_recurring=is_recurring,
            recurring_count=recurring_count,
            response_strategy='auto_fix'
        )

    def record_incident(
        self,
        root_cause_service: str,
        severity_level: Optional[SeverityLevel] = None,
        resolved: bool = False,
        # Alias used by orchestrator.py — accepts severity= as well
        severity: Optional[SeverityLevel] = None,
    ) -> None:
        """Record an incident in the history for recurring pattern detection."""
        # Accept severity= alias (used by orchestrator) or severity_level=
        resolved_severity = severity_level or severity
        self._incident_history.append({
            'root_cause': root_cause_service,
            'severity': resolved_severity,
            'resolved': resolved,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })

    def get_history(self) -> List[dict]:
        """Return the full incident history."""
        return list(self._incident_history)

    def get_patterns(self) -> List[dict]:
        """Detect services with recurring incidents (> 3 times)."""
        from collections import Counter
        counts = Counter(entry['root_cause'] for entry in self._incident_history)
        return [
            {'service': svc, 'count': cnt, 'recurring': cnt > 3}
            for svc, cnt in counts.items()
            if cnt > 1
        ]

    def _check_recurring(self, root_cause_service: Optional[str]) -> Tuple[bool, int]:
        """Check if the given service has been a recurring root cause."""
        if not root_cause_service:
            return False, 0
        count = sum(
            1 for entry in self._incident_history
            if entry.get('root_cause') == root_cause_service
        )
        return count > 3, count



    def get_recurring_patterns(self) -> dict:
        """Return dict of {service_name: occurrence_count} for services seen >= 2 times.
        Used by orchestrator and test suite (expects dict, not list).
        """
        from collections import Counter
        counts = Counter(entry["root_cause"] for entry in self._incident_history)
        return {svc: cnt for svc, cnt in counts.items() if cnt >= 2}

# Module-level singleton — used by orchestrator and other modules
severity_classifier = SeverityClassifier()


