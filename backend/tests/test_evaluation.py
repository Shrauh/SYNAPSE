"""
SYNAPSE Evaluation Framework Tests
----------------------------------

Tests:
- Metrics
- Benchmark
- Report
- Utilities

"""

import pytest

from app.evaluation.metrics import EvaluationMetrics
from app.evaluation.utils import (
    Timer,
    generate_dummy_incident,
    validate_probability,
)

from app.evaluation.benchmark import SynapseBenchmark
from app.evaluation.report import EvaluationReport


# =====================================================
# Metrics Tests
# =====================================================

def test_accuracy():

    y_true = ["cpu", "db", "network"]
    y_pred = ["cpu", "db", "memory"]

    score = EvaluationMetrics.accuracy(y_true, y_pred)

    assert score == pytest.approx(2 / 3)


def test_precision():

    relevant = ["cpu", "db"]
    retrieved = ["cpu", "memory", "db"]

    score = EvaluationMetrics.precision_at_k(
        relevant,
        retrieved,
        k=3,
    )

    assert score == pytest.approx(2 / 3)


def test_recall():

    relevant = ["cpu", "db"]
    retrieved = ["cpu", "memory", "db"]

    score = EvaluationMetrics.recall_at_k(
        relevant,
        retrieved,
        k=3,
    )

    assert score == 1.0


def test_f1():

    precision = 0.8
    recall = 0.8

    score = EvaluationMetrics.f1_score(
        precision,
        recall,
    )

    assert score == pytest.approx(0.8)


def test_mrr():

    relevant = ["db"]

    retrieved = [
        "cpu",
        "memory",
        "db",
    ]

    score = EvaluationMetrics.mean_reciprocal_rank(
        relevant,
        retrieved,
    )

    assert score == pytest.approx(1 / 3)


def test_confidence():

    confidence = EvaluationMetrics.confidence_score(
        [0.90, 0.95, 0.85]
    )

    assert confidence > 0


def test_latency():

    latency = EvaluationMetrics.average_latency(
        [0.2, 0.3, 0.4]
    )

    assert latency == pytest.approx(0.3)


def test_overall_score():

    score = EvaluationMetrics.overall_ai_score(
        accuracy=0.95,
        precision=0.94,
        recall=0.93,
        latency=0.20,
        confidence=0.96,
    )

    assert score > 80


# =====================================================
# Utility Tests
# =====================================================

def test_timer():

    timer = Timer()

    timer.start()

    elapsed = timer.stop()

    assert elapsed >= 0


def test_probability():

    assert validate_probability(0.5)

    assert validate_probability(1.0)

    assert not validate_probability(1.2)

    assert not validate_probability(-0.2)


def test_dummy_incident():

    incident = generate_dummy_incident()

    assert "incident_id" in incident

    assert "service" in incident

    assert "fault" in incident

    assert "severity" in incident


# =====================================================
# Benchmark Tests
# =====================================================

def test_benchmark():

    benchmark = SynapseBenchmark()

    results = benchmark.run()

    assert isinstance(results, dict)

    assert "metrics" in results

    assert "timestamp" in results


# =====================================================
# Report Tests
# =====================================================

def test_report_generation(tmp_path):

    benchmark = SynapseBenchmark()

    results = benchmark.run()

    report = EvaluationReport(results)

    json_file = tmp_path / "report.json"

    md_file = tmp_path / "report.md"

    report.export_json(str(json_file))

    report.export_markdown(str(md_file))

    assert json_file.exists()

    assert md_file.exists()


# =====================================================
# End-to-End Test
# =====================================================

def test_complete_pipeline():

    benchmark = SynapseBenchmark()

    results = benchmark.run()

    report = EvaluationReport(results)

    report.build_console_report()

    assert results["metrics"]["overall"] > 0