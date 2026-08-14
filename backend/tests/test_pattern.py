"""
Tests for the Pattern Analyzer module.
"""
import pytest
from app.ai_module.pattern.analyzer import PatternAnalyzer


class TestPatternAnalyzer:
    """Tests for recurring pattern detection."""

    def setup_method(self):
        self.analyzer = PatternAnalyzer()

    def test_record_and_detect(self):
        """Patterns detected after repeated incidents."""
        for _ in range(4):
            self.analyzer.record_incident("cache-service", "latency_spike", 1)
        patterns = self.analyzer.get_recurring_patterns()
        assert len(patterns) > 0
        assert any(p["service"] == "cache-service" for p in patterns)

    def test_no_pattern_for_single_incident(self):
        """Single incidents should not trigger pattern detection."""
        self.analyzer.record_incident("one-time-svc", "error_burst", 1)
        patterns = self.analyzer.get_recurring_patterns()
        assert not any(p["service"] == "one-time-svc" for p in patterns)

    def test_recommendation_generation(self):
        """Recommendations generated for recurring patterns."""
        for _ in range(5):
            self.analyzer.record_incident("db-service", "cpu_overload", 2)
        recs = self.analyzer.get_recommendations()
        assert len(recs) > 0

    def test_multiple_services_tracked(self):
        """Multiple services can have independent patterns."""
        for _ in range(3):
            self.analyzer.record_incident("svc-a", "latency_spike", 1)
            self.analyzer.record_incident("svc-b", "memory_leak", 2)
        patterns = self.analyzer.get_recurring_patterns()
        services = [p["service"] for p in patterns]
        assert "svc-a" in services
        assert "svc-b" in services
