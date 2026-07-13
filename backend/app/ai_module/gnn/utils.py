"""
SYNAPSE GNN Utilities — Helpers for normalization, evaluation, and metrics.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np


def z_score_normalize(
    matrix: np.ndarray,
    mean: np.ndarray = None,
    std: np.ndarray = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Z-score normalize a feature matrix.

    Args:
        matrix: [num_nodes, num_features]
        mean: Pre-computed mean (optional)
        std: Pre-computed std (optional)

    Returns:
        Tuple of (normalized_matrix, mean, std)
    """
    if mean is None:
        mean = matrix.mean(axis=0)
    if std is None:
        std = np.maximum(matrix.std(axis=0), 1e-8)

    normalized = (matrix - mean) / std
    return normalized, mean, std


def compute_topk_accuracy(
    predicted_scores: Dict[str, float],
    true_root_cause: str,
    k_values: List[int] = [1, 3, 5],
) -> Dict[str, float]:
    """Compute top-k accuracy for RCA evaluation.

    Args:
        predicted_scores: Dict of service → anomaly_score
        true_root_cause: Ground truth root cause service
        k_values: List of k values to evaluate

    Returns:
        Dict like {"top_1": 1.0, "top_3": 1.0, "top_5": 1.0}
    """
    ranked = sorted(predicted_scores.items(), key=lambda x: x[1], reverse=True)
    ranked_services = [svc for svc, _ in ranked]

    results = {}
    for k in k_values:
        top_k = ranked_services[:k]
        results[f"top_{k}"] = 1.0 if true_root_cause in top_k else 0.0

    return results


def compute_precision_recall(
    predicted_anomalous: List[str],
    true_affected: List[str],
) -> Dict[str, float]:
    """Compute precision and recall for anomaly detection.

    Args:
        predicted_anomalous: Services flagged as anomalous
        true_affected: Services that were actually affected

    Returns:
        Dict with precision, recall, f1
    """
    if not predicted_anomalous or not true_affected:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    pred_set = set(predicted_anomalous)
    true_set = set(true_affected)

    tp = len(pred_set & true_set)
    precision = tp / len(pred_set) if pred_set else 0.0
    recall = tp / len(true_set) if true_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}
