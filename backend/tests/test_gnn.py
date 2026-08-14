"""
SYNAPSE Tests — GNN model and anomaly detection tests.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch


def test_fallback_anomaly_detector():
    """Test the statistical fallback anomaly detector."""
    from app.ai_module.gnn.model import FallbackAnomalyDetector

    detector = FallbackAnomalyDetector()

    # Create normal baseline data
    normal_data = [
        torch.randn(10, 5) * 0.1 + torch.tensor([10.0, 0.5, 30.0, 40.0, 500.0])
        for _ in range(5)
    ]
    detector.fit(normal_data)

    # Normal input — should have low scores
    normal_input = torch.randn(10, 5) * 0.1 + torch.tensor([10.0, 0.5, 30.0, 40.0, 500.0])
    scores_normal = detector.compute_anomaly_scores(normal_input)
    assert scores_normal.shape == (10,)
    assert all(s < 0.8 for s in scores_normal)

    # Anomalous input — should have higher scores
    anomalous_input = normal_input.clone()
    anomalous_input[3] = torch.tensor([100.0, 15.0, 95.0, 90.0, 50.0])  # Spike node 3
    scores_anomalous = detector.compute_anomaly_scores(anomalous_input)
    assert scores_anomalous[3] > scores_normal[3]


def test_gnn_utils_topk():
    """Test top-k accuracy computation."""
    from app.ai_module.gnn.utils import compute_topk_accuracy

    scores = {
        "database": 0.95,
        "auth-service": 0.78,
        "api-gateway": 0.62,
        "cache-service": 0.3,
    }

    # True root cause is database — should be top 1
    result = compute_topk_accuracy(scores, "database", k_values=[1, 3, 5])
    assert result["top_1"] == 1.0
    assert result["top_3"] == 1.0

    # True root cause is cache-service — should NOT be top 1
    result2 = compute_topk_accuracy(scores, "cache-service", k_values=[1, 3])
    assert result2["top_1"] == 0.0


def test_gnn_utils_precision_recall():
    """Test precision/recall computation."""
    from app.ai_module.gnn.utils import compute_precision_recall

    result = compute_precision_recall(
        predicted_anomalous=["database", "auth-service", "api-gateway"],
        true_affected=["database", "auth-service", "user-service"],
    )
    assert result["precision"] == pytest.approx(2 / 3, rel=1e-3)
    assert result["recall"] == pytest.approx(2 / 3, rel=1e-3)


def test_z_score_normalize():
    """Test z-score normalization."""
    from app.ai_module.gnn.utils import z_score_normalize

    matrix = np.array([[10.0, 0.5, 30.0, 40.0, 500.0],
                        [12.0, 0.6, 32.0, 42.0, 520.0]])

    normalized, mean, std = z_score_normalize(matrix)
    assert normalized.shape == matrix.shape
    # Normalized should be roughly centered at 0
    assert abs(normalized.mean()) < 1.0
