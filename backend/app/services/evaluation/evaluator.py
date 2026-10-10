"""
SYNAPSE RCAEval Evaluator — connects SYNAPSE pipeline output to benchmark metrics.

Usage:
  1. Run SYNAPSE RCA on a dataset
  2. Pass predicted rankings + ground truth to this evaluator
  3. Get RCAEval-compatible scores to compare against published baselines
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from app.services.evaluation.metrics import (
    evaluate_single, benchmark_summary,
    EvaluationResult, BenchmarkSummary, RCAEVAL_BASELINES
)

logger = logging.getLogger("synapse.evaluation")

# In-memory evaluation log
_eval_history: List[EvaluationResult] = []


class SynapseEvaluator:
    """
    Evaluates SYNAPSE RCA output using RCAEval-standard metrics.

    Integrates with the SYNAPSE pipeline:
      - Receives root_cause candidates from orchestrator
      - Compares against ground truth (from fault injection label)
      - Computes PR@K, Avg@K, MRR metrics
      - Stores results for cumulative benchmarking
    """

    def __init__(self):
        self._results: List[EvaluationResult] = []

    def evaluate_prediction(
        self,
        incident_id: str,
        root_candidates: List[tuple],  # [(service, score), ...] from SYNAPSE
        true_root_cause: str,
    ) -> EvaluationResult:
        """
        Evaluate a single SYNAPSE prediction.

        Args:
            incident_id: Unique incident identifier.
            root_candidates: Ordered list of (service, score) from orchestrator.
            true_root_cause: Ground truth root cause service name.

        Returns:
            EvaluationResult with PR@K, Avg@K, MRR scores.
        """
        # Extract ranked service names from SYNAPSE output
        predicted_ranking = [svc for svc, score in root_candidates]

        result = evaluate_single(
            incident_id=incident_id,
            predicted_ranking=predicted_ranking,
            true_root_cause=true_root_cause,
        )
        self._results.append(result)
        _eval_history.append(result)

        logger.info(
            f"[Eval] {incident_id}: true={true_root_cause}, "
            f"rank={result.rank}, PR@1={result.pr_at_1:.2f}, "
            f"Avg@5={result.avg_at_5:.4f}"
        )
        return result

    def evaluate_from_pipeline_result(
        self,
        pipeline_result: Dict[str, Any],
        true_root_cause: str,
    ) -> Optional[EvaluationResult]:
        """
        Evaluate directly from SYNAPSE orchestrator pipeline output dict.

        Extracts the root_cause ranking from pipeline_result and computes metrics.
        """
        try:
            incident_id = pipeline_result.get("incident_id", "unknown")
            # Build ranked list from anomaly_scores (sorted descending)
            anomaly_scores = pipeline_result.get("anomaly_scores", {})
            ranked = sorted(anomaly_scores.items(), key=lambda x: x[1], reverse=True)

            # Ensure the pipeline's top root cause is first
            top_root = pipeline_result.get("root_cause", "")
            names = [svc for svc, _ in ranked]
            if top_root and top_root in names:
                names.remove(top_root)
                names.insert(0, top_root)

            root_candidates = [(n, anomaly_scores.get(n, 0.0)) for n in names]
            return self.evaluate_prediction(incident_id, root_candidates, true_root_cause)
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return None

    def get_benchmark(self) -> BenchmarkSummary:
        """Get cumulative benchmark summary across all evaluated incidents."""
        return benchmark_summary(self._results)

    def get_benchmark_dict(self) -> Dict[str, Any]:
        """Return benchmark as dict for API response."""
        b = self.get_benchmark()
        return {
            "total_incidents_evaluated": b.total_incidents,
            "metrics": {
                "PR@1":   round(b.avg_pr_at_1, 4),
                "PR@3":   round(b.avg_pr_at_3, 4),
                "PR@5":   round(b.avg_pr_at_5, 4),
                "Avg@5":  round(b.avg_at_5, 4),
                "Avg@10": round(b.avg_at_10, 4),
                "MRR":    round(b.mrr, 4),
                "MAR":    round(b.mar, 2),
            },
            "vs_rcaeval_baselines": b.synapse_vs_baseline,
            "rcaeval_baselines": RCAEVAL_BASELINES,
            "interpretation": (
                f"SYNAPSE Avg@5={b.avg_at_5:.4f} beats "
                f"{b.synapse_vs_baseline.get('rank_vs_baselines', 0)}/"
                f"{len(RCAEVAL_BASELINES)} RCAEval baselines"
            ) if b.total_incidents > 0 else "No evaluations yet",
        }

    def get_history(self) -> List[Dict]:
        """Return evaluation history as list of dicts."""
        return [
            {
                "incident_id": r.incident_id,
                "true_root_cause": r.true_root_cause,
                "rank": r.rank,
                "PR@1": r.pr_at_1,
                "PR@3": r.pr_at_3,
                "PR@5": r.pr_at_5,
                "Avg@5": r.avg_at_5,
                "MRR": r.reciprocal_rank,
                "timestamp": r.timestamp,
            }
            for r in self._results
        ]

    def reset(self) -> None:
        """Clear evaluation history."""
        self._results.clear()
        logger.info("Evaluation history reset.")


# Singleton
synapse_evaluator = SynapseEvaluator()
