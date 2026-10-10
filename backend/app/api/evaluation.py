"""
Evaluation API — RCAEval-compatible benchmark endpoints.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.evaluation.evaluator import synapse_evaluator
from app.services.evaluation.metrics import RCAEVAL_BASELINES

router = APIRouter(prefix="/eval", tags=["Evaluation (RCAEval)"])


class EvalRequest(BaseModel):
    incident_id: str
    predicted_ranking: List[str]   # ordered service names, top first
    true_root_cause: str


class BatchEvalRequest(BaseModel):
    evaluations: List[EvalRequest]


@router.post("/evaluate")
def evaluate_prediction(req: EvalRequest) -> Dict[str, Any]:
    """
    Evaluate a single RCA prediction using RCAEval-standard metrics.
    Pass predicted ranking (ordered services) and ground truth root cause.
    """
    candidates = [(svc, 1.0 / (i + 1)) for i, svc in enumerate(req.predicted_ranking)]
    result = synapse_evaluator.evaluate_prediction(
        incident_id=req.incident_id,
        root_candidates=candidates,
        true_root_cause=req.true_root_cause,
    )
    return {
        "incident_id": result.incident_id,
        "true_root_cause": result.true_root_cause,
        "rank": result.rank,
        "PR@1": result.pr_at_1,
        "PR@3": result.pr_at_3,
        "PR@5": result.pr_at_5,
        "Avg@5": result.avg_at_5,
        "Avg@10": result.avg_at_10,
        "MRR": result.reciprocal_rank,
    }


@router.post("/evaluate/batch")
def evaluate_batch(req: BatchEvalRequest) -> Dict[str, Any]:
    """Evaluate multiple RCA predictions at once."""
    results = []
    for e in req.evaluations:
        candidates = [(svc, 1.0 / (i + 1)) for i, svc in enumerate(e.predicted_ranking)]
        r = synapse_evaluator.evaluate_prediction(e.incident_id, candidates, e.true_root_cause)
        results.append({"incident_id": r.incident_id, "rank": r.rank, "Avg@5": r.avg_at_5})
    return {"evaluated": len(results), "results": results, "summary": synapse_evaluator.get_benchmark_dict()}


@router.get("/benchmark")
def get_benchmark() -> Dict[str, Any]:
    """
    Get SYNAPSE benchmark summary in RCAEval format.
    Shows PR@K, Avg@K, MRR and comparison against 9 published baselines.
    """
    return synapse_evaluator.get_benchmark_dict()


@router.get("/history")
def get_history() -> List[Dict]:
    """Get full evaluation history."""
    return synapse_evaluator.get_history()


@router.delete("/reset")
def reset_evaluation() -> Dict[str, str]:
    """Reset evaluation history."""
    synapse_evaluator.reset()
    return {"status": "reset", "message": "Evaluation history cleared."}


@router.get("/baselines")
def get_baselines() -> Dict[str, Any]:
    """Return RCAEval published baseline scores for comparison."""
    return {
        "source": "RCAEval: A Benchmark for Root Cause Analysis (FSE'26, WWW'25, ASE'24)",
        "metric": "Avg@5 on Online Boutique dataset",
        "baselines": RCAEVAL_BASELINES,
        "note": "SYNAPSE uses VAE-GNN + DECI causal inference vs these statistical/graph baselines",
    }
