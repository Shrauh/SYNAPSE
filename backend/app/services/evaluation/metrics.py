"""
SYNAPSE Evaluation Metrics — RCAEval-compatible benchmark metrics.

Implements the same evaluation protocol as:
  RCAEval: A Benchmark for Root Cause Analysis (FSE'26, WWW'25, ASE'24)
  https://github.com/phamquiluan/RCAEval

Metrics:
  - Avg@K: Average precision at top-K candidates
  - PR@K:  Precision at K (1 if true root cause in top-K, else 0)
  - MRR:   Mean Reciprocal Rank
  - MAR:   Mean Average Rank
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

logger = logging.getLogger("synapse.evaluation")


@dataclass
class EvaluationResult:
    """Result of evaluating one RCA prediction."""
    incident_id: str
    true_root_cause: str
    predicted_ranking: List[str]  # ordered list, index 0 = top prediction
    pr_at_1: float
    pr_at_3: float
    pr_at_5: float
    avg_at_5: float
    avg_at_10: float
    reciprocal_rank: float
    rank: int  # rank of true root cause (1-based, 0 if not found)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class BenchmarkSummary:
    """Aggregated benchmark results across multiple incidents."""
    total_incidents: int
    avg_pr_at_1: float
    avg_pr_at_3: float
    avg_pr_at_5: float
    avg_at_5: float
    avg_at_10: float
    mrr: float  # Mean Reciprocal Rank
    mar: float  # Mean Average Rank
    synapse_vs_baseline: Dict[str, float]  # comparison to known baselines


def precision_at_k(predicted: List[str], true_root_cause: str, k: int) -> float:
    """PR@K: 1.0 if true root cause appears in top-K predictions, else 0.0."""
    return 1.0 if true_root_cause in predicted[:k] else 0.0


def avg_at_k(predicted: List[str], true_root_cause: str, k: int) -> float:
    """
    Avg@K: Average precision at K.
    Score = (1/rank) if found in top K, else 0.
    This matches RCAEval's Avg@K definition.
    """
    for i, svc in enumerate(predicted[:k]):
        if svc == true_root_cause:
            return 1.0 / (i + 1)
    return 0.0


def reciprocal_rank(predicted: List[str], true_root_cause: str) -> float:
    """1/rank where rank is position of true root cause (1-based)."""
    for i, svc in enumerate(predicted):
        if svc == true_root_cause:
            return 1.0 / (i + 1)
    return 0.0


def get_rank(predicted: List[str], true_root_cause: str) -> int:
    """Position of true root cause in ranking (1-based). 0 if not found."""
    for i, svc in enumerate(predicted):
        if svc == true_root_cause:
            return i + 1
    return 0


def evaluate_single(
    incident_id: str,
    predicted_ranking: List[str],
    true_root_cause: str,
) -> EvaluationResult:
    """Evaluate a single RCA prediction against the ground truth."""
    return EvaluationResult(
        incident_id=incident_id,
        true_root_cause=true_root_cause,
        predicted_ranking=predicted_ranking,
        pr_at_1=precision_at_k(predicted_ranking, true_root_cause, 1),
        pr_at_3=precision_at_k(predicted_ranking, true_root_cause, 3),
        pr_at_5=precision_at_k(predicted_ranking, true_root_cause, 5),
        avg_at_5=avg_at_k(predicted_ranking, true_root_cause, 5),
        avg_at_10=avg_at_k(predicted_ranking, true_root_cause, 10),
        reciprocal_rank=reciprocal_rank(predicted_ranking, true_root_cause),
        rank=get_rank(predicted_ranking, true_root_cause),
    )


# Known RCAEval baseline scores for comparison (from paper Table 2)
# These are Avg@5 scores on Online Boutique dataset
RCAEVAL_BASELINES: Dict[str, float] = {
    "MicroRCA": 0.576,
    "CloudRanger": 0.492,
    "CIRCA": 0.498,
    "CausalRCA": 0.521,
    "RCD": 0.489,
    "E-Diagnosis": 0.463,
    "Nezha": 0.534,
    "DiagFusion": 0.548,
    "BARO": 0.601,
}


def benchmark_summary(
    results: List[EvaluationResult],
    system_name: str = "SYNAPSE",
) -> BenchmarkSummary:
    """Aggregate evaluation results and compare against RCAEval baselines."""
    if not results:
        return BenchmarkSummary(
            total_incidents=0,
            avg_pr_at_1=0.0, avg_pr_at_3=0.0, avg_pr_at_5=0.0,
            avg_at_5=0.0, avg_at_10=0.0,
            mrr=0.0, mar=0.0,
            synapse_vs_baseline={},
        )

    n = len(results)
    avg5 = sum(r.avg_at_5 for r in results) / n

    # Compare against baselines
    comparison = {
        baseline: round(avg5 - score, 4)
        for baseline, score in RCAEVAL_BASELINES.items()
    }
    comparison["rank_vs_baselines"] = sum(1 for s in RCAEVAL_BASELINES.values() if avg5 > s)

    ranks = [r.rank for r in results if r.rank > 0]

    return BenchmarkSummary(
        total_incidents=n,
        avg_pr_at_1=sum(r.pr_at_1 for r in results) / n,
        avg_pr_at_3=sum(r.pr_at_3 for r in results) / n,
        avg_pr_at_5=sum(r.pr_at_5 for r in results) / n,
        avg_at_5=avg5,
        avg_at_10=sum(r.avg_at_10 for r in results) / n,
        mrr=sum(r.reciprocal_rank for r in results) / n,
        mar=sum(ranks) / len(ranks) if ranks else 0.0,
        synapse_vs_baseline=comparison,
    )
