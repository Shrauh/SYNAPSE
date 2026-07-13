"""
SYNAPSE AI Evaluation Metrics
-----------------------------

This module provides reusable evaluation metrics for:

• Classification Accuracy
• Precision@K
• Recall@K
• F1 Score
• Mean Reciprocal Rank (MRR)
• Average Latency
• Confidence Aggregation


"""

from __future__ import annotations

from statistics import mean
from typing import Iterable, List, Sequence


class EvaluationMetrics:
    """
    Collection of static evaluation methods.
    """

    @staticmethod
    def accuracy(
        y_true: Sequence[str],
        y_pred: Sequence[str]
    ) -> float:
        """
        Calculate classification accuracy.
        """

        if len(y_true) == 0:
            return 0.0

        correct = sum(
            t == p
            for t, p in zip(y_true, y_pred)
        )

        return correct / len(y_true)

    @staticmethod
    def precision_at_k(
        relevant: Sequence[str],
        retrieved: Sequence[str],
        k: int = 3
    ) -> float:
        """
        Precision@K
        """

        retrieved = retrieved[:k]

        if len(retrieved) == 0:
            return 0.0

        hits = len(
            set(retrieved).intersection(relevant)
        )

        return hits / len(retrieved)

    @staticmethod
    def recall_at_k(
        relevant: Sequence[str],
        retrieved: Sequence[str],
        k: int = 3
    ) -> float:
        """
        Recall@K
        """

        if len(relevant) == 0:
            return 0.0

        retrieved = retrieved[:k]

        hits = len(
            set(retrieved).intersection(relevant)
        )

        return hits / len(relevant)

    @staticmethod
    def f1_score(
        precision: float,
        recall: float
    ) -> float:
        """
        Harmonic mean.
        """

        if precision + recall == 0:
            return 0.0

        return (
            2 * precision * recall
            / (precision + recall)
        )

    @staticmethod
    def mean_reciprocal_rank(
        relevant: Sequence[str],
        retrieved: Sequence[str]
    ) -> float:
        """
        Mean Reciprocal Rank.
        """

        for index, item in enumerate(retrieved):

            if item in relevant:
                return 1 / (index + 1)

        return 0.0

    @staticmethod
    def average_latency(
        latencies: Iterable[float]
    ) -> float:
        """
        Average execution latency.
        """

        values = list(latencies)

        if len(values) == 0:
            return 0.0

        return mean(values)

    @staticmethod
    def confidence_score(
        probabilities: Sequence[float]
    ) -> float:
        """
        Average confidence.
        """

        if len(probabilities) == 0:
            return 0.0

        return mean(probabilities)

    @staticmethod
    def overall_ai_score(
        accuracy: float,
        precision: float,
        recall: float,
        latency: float,
        confidence: float
    ) -> float:
        """
        Composite evaluation score.

        Higher is better.
        """

        latency_score = max(
            0.0,
            1 - latency
        )

        score = (
            0.30 * accuracy +
            0.20 * precision +
            0.20 * recall +
            0.15 * confidence +
            0.15 * latency_score
        )

        return round(score * 100, 2)


if __name__ == "__main__":

    y_true = [
        "database",
        "cpu",
        "network"
    ]

    y_pred = [
        "database",
        "cpu",
        "memory"
    ]

    retrieved = [
        "database",
        "memory",
        "cpu"
    ]

    accuracy = EvaluationMetrics.accuracy(
        y_true,
        y_pred
    )

    precision = EvaluationMetrics.precision_at_k(
        y_true,
        retrieved,
        k=3
    )

    recall = EvaluationMetrics.recall_at_k(
        y_true,
        retrieved,
        k=3
    )

    f1 = EvaluationMetrics.f1_score(
        precision,
        recall
    )

    mrr = EvaluationMetrics.mean_reciprocal_rank(
        y_true,
        retrieved
    )

    confidence = EvaluationMetrics.confidence_score(
        [0.91, 0.96, 0.89]
    )

    latency = EvaluationMetrics.average_latency(
        [0.18, 0.20, 0.19]
    )

    overall = EvaluationMetrics.overall_ai_score(
        accuracy,
        precision,
        recall,
        latency,
        confidence
    )

    print("\nSYNAPSE Evaluation Metrics\n")

    print(f"Accuracy      : {accuracy:.2f}")
    print(f"Precision@3   : {precision:.2f}")
    print(f"Recall@3      : {recall:.2f}")
    print(f"F1 Score      : {f1:.2f}")
    print(f"MRR           : {mrr:.2f}")
    print(f"Latency       : {latency:.2f}s")
    print(f"Confidence    : {confidence:.2f}")
    print(f"Overall Score : {overall}")