import pytest
from app.services.evaluation.metrics import (
    precision_at_k,
    avg_at_k,
    reciprocal_rank,
    evaluate_single,
    benchmark_summary,
    EvaluationResult
)

def test_precision_at_k():
    preds = ["a", "b", "c", "d", "e"]
    assert precision_at_k(preds, "a", 1) == 1.0
    assert precision_at_k(preds, "c", 3) == 1.0
    assert precision_at_k(preds, "e", 5) == 1.0
    assert precision_at_k(preds, "z", 5) == 0.0
    assert precision_at_k(preds, "e", 3) == 0.0

def test_avg_at_k():
    preds = ["a", "b", "c"]
    assert avg_at_k(preds, "a", 3) == 1.0
    assert avg_at_k(preds, "b", 3) == 0.5
    assert avg_at_k(preds, "c", 3) == 1/3
    assert avg_at_k(preds, "z", 3) == 0.0

def test_reciprocal_rank():
    preds = ["a", "b", "c"]
    assert reciprocal_rank(preds, "a") == 1.0
    assert reciprocal_rank(preds, "b") == 0.5
    assert reciprocal_rank(preds, "c") == 1/3
    assert reciprocal_rank(preds, "z") == 0.0

def test_evaluate_single():
    preds = ["a", "b", "c", "d", "e"]
    res = evaluate_single("inc1", preds, "b")
    assert res.incident_id == "inc1"
    assert res.true_root_cause == "b"
    assert res.pr_at_1 == 0.0
    assert res.pr_at_3 == 1.0
    assert res.pr_at_5 == 1.0
    assert res.rank == 2

def test_benchmark_summary():
    preds1 = ["a", "b", "c"]
    preds2 = ["x", "a", "c"]
    preds3 = ["z", "y", "a"]
    r1 = evaluate_single("1", preds1, "a")
    r2 = evaluate_single("2", preds2, "a")
    r3 = evaluate_single("3", preds3, "a")
    
    summary = benchmark_summary([r1, r2, r3])
    assert summary.total_incidents == 3
    assert summary.avg_pr_at_1 == 1/3
    assert summary.avg_pr_at_3 == 3/3
