"""
SYNAPSE Tests — DECI Causal Discovery Engine tests.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.ai_module.causal.deci import DECIEngine
from app.ai_module.causal.discovery import CausalDiscoveryEngine
from app.ai_module.causal.dag_utils import (
    break_cycles,
    detect_cycles,
    get_propagation_chain,
    get_root_nodes,
    to_causal_graph_json,
)


def test_deci_causal_discovery():
    """Test DECI non-linear differentiable causal discovery."""
    engine = DECIEngine(max_iter=80, edge_threshold=0.2)

    np.random.seed(42)
    n = 60
    # True causal mechanism: A -> B -> C (non-linear propagation)
    a = np.cumsum(np.random.randn(n))
    b = np.sin(a) + 0.1 * np.random.randn(n)
    c = np.tanh(b) + 0.1 * np.random.randn(n)

    matrix = np.column_stack([a, b, c])
    names = ["service-a", "service-b", "service-c"]

    result = engine.discover(matrix, names)

    assert "edges" in result
    assert "dag" in result
    assert "nodes" in result
    assert "h_score" in result
    assert len(result["nodes"]) == 3
    # NOTEARS acyclicity constraint check
    assert result["h_score"] < 0.1


def test_deci_with_prior_w0():
    """Test DECI with LLM-RAG prior matrix W0 injection."""
    engine = DECIEngine(max_iter=60, lambda_prior=3.0)

    np.random.seed(42)
    n = 50
    x = np.random.randn(n, 2)
    names = ["payment", "checkout"]

    # Provide prior: payment -> checkout (w0[0, 1] = 0.9)
    w0 = np.array([[0.0, 0.9], [0.0, 0.0]], dtype=np.float32)

    result = engine.discover(x, names, w0_prior=w0)
    assert "edges" in result
    assert result["nodes"] == names


def test_causal_discovery_wrapper():
    """Test CausalDiscoveryEngine top-level class with DECI."""
    engine = CausalDiscoveryEngine()

    np.random.seed(42)
    matrix = np.random.randn(40, 2)
    result = engine.discover(matrix, ["auth", "frontend"])

    assert "edges" in result
    assert "dag" in result
    assert len(result["nodes"]) == 2


def test_causal_single_node():
    """Test causal discovery with a single anomalous node."""
    engine = CausalDiscoveryEngine()
    result = engine.discover(
        np.random.randn(20, 1),
        ["database"],
    )
    assert result["nodes"] == ["database"]
    assert result["edges"] == []


def test_dag_root_extraction():
    """Test root cause extraction from a causal DAG."""
    dag = {
        "database": ["auth-service", "user-service"],
        "auth-service": ["api-gateway"],
        "user-service": [],
        "api-gateway": [],
    }
    scores = {
        "database": 0.95,
        "auth-service": 0.78,
        "user-service": 0.65,
        "api-gateway": 0.55,
    }

    roots = get_root_nodes(dag, scores)
    # database has no incoming edges — it should be the root
    assert roots[0][0] == "database"
    assert roots[0][1] == 0.95


def test_propagation_chain():
    """Test BFS propagation chain computation."""
    dag = {
        "database": ["auth-service"],
        "auth-service": ["api-gateway"],
        "api-gateway": [],
    }

    chain = get_propagation_chain(dag, "database")
    assert chain == ["database", "auth-service", "api-gateway"]


def test_cycle_detection_and_breaking():
    """Test cycle detection and cycle breaking in a DAG."""
    dag_with_cycle = {
        "a": ["b"],
        "b": ["c"],
        "c": ["a"],
    }
    cycles = detect_cycles(dag_with_cycle)
    assert len(cycles) > 0

    scores = {"a": 0.9, "b": 0.7, "c": 0.5}
    clean_dag = break_cycles(dag_with_cycle, scores)
    assert len(detect_cycles(clean_dag)) == 0


def test_causal_graph_json():
    """Test conversion to JSON format."""
    dag = {"database": ["auth-service"], "auth-service": []}
    edges = [("database", "auth-service", 0.85)]
    scores = {"database": 0.95, "auth-service": 0.7}
    roots = [("database", 0.95)]

    result = to_causal_graph_json(dag, edges, scores, roots)
    assert "nodes" in result
    assert "edges" in result
    assert any(n["is_root"] for n in result["nodes"])


def test_root_extraction_filters_isolated_nodes():
    """Isolated nodes with no outgoing edges should not be picked as root cause."""
    dag = {
        "isolated-service": [],  # in-degree 0, out-degree 0
        "database": ["backend"],  # in-degree 0, out-degree 1
        "backend": [],
    }
    scores = {
        "isolated-service": 0.99,  # Higher score but isolated
        "database": 0.80,
        "backend": 0.70,
    }

    roots = get_root_nodes(dag, scores)
    # database should be the primary root cause because it has outgoing edges
    root_names = [r[0] for r in roots]
    assert "database" in root_names
    assert "isolated-service" not in root_names


def test_cycle_breaking_weakest_edge():
    """Cycle breaking should remove the edge with lowest causal strength."""
    dag = {
        "a": ["b"],
        "b": ["c"],
        "c": ["a"],
    }
    # Edge c -> a has the lowest weight (0.15)
    edges = [
        {"source": "a", "target": "b", "weight": 0.85},
        {"source": "b", "target": "c", "weight": 0.75},
        {"source": "c", "target": "a", "weight": 0.15},
    ]
    scores = {"a": 0.1, "b": 0.9, "c": 0.9}

    clean_dag = break_cycles(dag, anomaly_scores=scores, edges=edges)
    assert len(detect_cycles(clean_dag)) == 0
    # c -> a should be removed, while a -> b and b -> c should remain
    assert "b" in clean_dag["a"]
    assert "c" in clean_dag["b"]
    assert "a" not in clean_dag["c"]

