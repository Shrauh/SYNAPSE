"""
Tests for the Multi-Root-Cause Detector module.
"""
import pytest
from app.ai_module.causal.multi_root import MultiRootCauseDetector


class TestMultiRootCause:
    """Tests for L3 systemic multi-root-cause detection."""

    def setup_method(self):
        self.detector = MultiRootCauseDetector()

    def test_single_cluster(self):
        """Single cluster of anomalous services."""
        anomalous = {"svc-a": 0.9, "svc-b": 0.7, "svc-c": 0.6}
        topology = {"svc-a": ["svc-b"], "svc-b": ["svc-c"]}
        result = self.detector.detect(anomalous, topology)
        assert len(result["clusters"]) >= 1

    def test_multiple_clusters(self):
        """Independent failure clusters detected."""
        anomalous = {
            "svc-a": 0.9, "svc-b": 0.8,
            "svc-x": 0.85, "svc-y": 0.7,
        }
        topology = {
            "svc-a": ["svc-b"],
            "svc-x": ["svc-y"],
        }
        result = self.detector.detect(anomalous, topology)
        assert len(result["clusters"]) >= 2

    def test_empty_input(self):
        """No anomalous services returns empty result."""
        result = self.detector.detect({}, {})
        assert len(result["clusters"]) == 0

    def test_root_identification(self):
        """Root cause identified per cluster."""
        anomalous = {"root": 0.95, "child1": 0.6, "child2": 0.5}
        topology = {"root": ["child1", "child2"]}
        result = self.detector.detect(anomalous, topology)
        assert result["clusters"][0]["root"] == "root"
