"""
SYNAPSE Tests — Causal inference engine tests.
"""

from __future__ import annotations

import numpy as np
import pytest


def test_causal_discovery_fallback():
    """Test correlation-based causal discovery (fallback)."""
    from app.ai_module.causal.discovery import CausalDiscoveryEngine

    engine = CausalDiscoveryEngine(alpha=0.05)

    # Simulate: service A causes service B (A leads B by 1 step)
    np.random.seed(42)
    n = 50
    a = np.cumsum(np.random.randn(n))
    b = np.zeros(n)
    b[1:] = a[:-1] * 0.8 + np.random.randn(n - 1) * 0.2  # B follows A

    matrix = np.column_stack([a, b])
    result = engine.discover(matrix, ["service-a", "service-b"])

    assert "edges" in result
    assert "dag" in result
    assert "nodes" in result
    assert len(result["nodes"]) == 2


def test_causal_single_node():
    """Test causal discovery with a single anomalous node."""
    from app.ai_module.causal.discovery import CausalDiscoveryEngine

    engine = CausalDiscoveryEngine()
    result = engine.discover(
        np.random.randn(20, 1),
        ["database"],
    )
    assert result["nodes"] == ["database"]
    assert result["edges"] == []


def test_dag_root_extraction():
    """Test root cause extraction from a causal DAG."""
    from app.ai_module.causal.dag_utils import get_root_nodes

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
    from app.ai_module.causal.dag_utils import get_propagation_chain

    dag = {
        "database": ["auth-service"],
        "auth-service": ["api-gateway"],
        "api-gateway": [],
    }

    chain = get_propagation_chain(dag, "database")
    assert chain == ["database", "auth-service", "api-gateway"]


def test_cycle_detection():
    """Test cycle detection in a DAG."""
    from app.ai_module.causal.dag_utils import detect_cycles

    # DAG with a cycle
    dag_with_cycle = {
        "a": ["b"],
        "b": ["c"],
        "c": ["a"],  # cycle!
    }
    cycles = detect_cycles(dag_with_cycle)
    assert len(cycles) > 0

    # Clean DAG
    clean_dag = {
        "a": ["b"],
        "b": ["c"],
        "c": [],
    }
    cycles = detect_cycles(clean_dag)
    assert len(cycles) == 0


def test_causal_graph_json():
    """Test conversion to JSON format."""
    from app.ai_module.causal.dag_utils import to_causal_graph_json

    dag = {"database": ["auth-service"], "auth-service": []}
    edges = [("database", "auth-service", 0.85)]
    scores = {"database": 0.95, "auth-service": 0.7}
    roots = [("database", 0.95)]

    result = to_causal_graph_json(dag, edges, scores, roots)
    assert "nodes" in result
    assert "edges" in result
    assert any(n["is_root"] for n in result["nodes"])
