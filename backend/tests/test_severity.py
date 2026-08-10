"""
Tests for the Severity Classifier module.
"""
import pytest
from app.ai_module.severity.classifier import (
    SeverityClassifier, SeverityLevel, SeverityResult,
)


class TestSeverityClassifier:
    """Tests for the 4-level severity classification."""

    def setup_method(self):
        self.classifier = SeverityClassifier()

    def test_l1_simple_single_service(self):
        """L1: Single service anomaly with high confidence."""
        result = self.classifier.classify(
            anomaly_scores={"svc-a": 0.9, "svc-b": 0.2},
            causal_confidence=0.85,
            root_cause_service="svc-a",
        )
        assert result.level == SeverityLevel.L1_SIMPLE
        assert result.response_strategy == "auto_fix"
        assert result.num_anomalous == 1

    def test_l2_cascading_multiple_services(self):
        """L2: 2-3 services anomalous."""
        result = self.classifier.classify(
            anomaly_scores={"svc-a": 0.8, "svc-b": 0.7, "svc-c": 0.3},
            causal_confidence=0.75,
            root_cause_service="svc-a",
        )
        assert result.level == SeverityLevel.L2_CASCADING
        assert result.response_strategy == "root_first"
        assert result.num_anomalous == 2

    def test_l3_systemic_many_services(self):
        """L3: 4+ services anomalous."""
        scores = {f"svc-{i}": 0.8 for i in range(5)}
        result = self.classifier.classify(
            anomaly_scores=scores,
            causal_confidence=0.6,
            root_cause_service="svc-0",
        )
        assert result.level == SeverityLevel.L3_SYSTEMIC
        assert result.response_strategy == "escalate"

    def test_l3_low_confidence(self):
        """L3: Low confidence triggers systemic classification."""
        result = self.classifier.classify(
            anomaly_scores={"svc-a": 0.9},
            causal_confidence=0.3,
            root_cause_service="svc-a",
        )
        assert result.level == SeverityLevel.L3_SYSTEMIC

    def test_l4_recurring_pattern(self):
        """L4: Recurring root cause detected."""
        # Record 4 past incidents for same service
        for _ in range(4):
            self.classifier.record_incident("db-service", SeverityLevel.L1_SIMPLE)
        result = self.classifier.classify(
            anomaly_scores={"db-service": 0.9},
            causal_confidence=0.85,
            root_cause_service="db-service",
        )
        assert result.level == SeverityLevel.L4_DESIGN_FLAW
        assert result.response_strategy == "recommend"
        assert result.is_recurring is True

    def test_incident_history_tracking(self):
        """Verify incidents are recorded and retrievable."""
        self.classifier.record_incident("svc-a", SeverityLevel.L1_SIMPLE, resolved=True)
        self.classifier.record_incident("svc-b", SeverityLevel.L2_CASCADING)
        history = self.classifier.get_history()
        assert len(history) == 2
        assert history[0]["root_cause"] == "svc-a"

    def test_recurring_patterns_detection(self):
        """Verify recurring patterns are detected correctly."""
        for _ in range(3):
            self.classifier.record_incident("leaky-svc", SeverityLevel.L1_SIMPLE)
        self.classifier.record_incident("other-svc", SeverityLevel.L1_SIMPLE)
        patterns = self.classifier.get_recurring_patterns()
        assert "leaky-svc" in patterns
        assert patterns["leaky-svc"] == 3
        assert "other-svc" not in patterns
