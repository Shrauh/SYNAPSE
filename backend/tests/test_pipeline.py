"""
SYNAPSE Tests — End-to-end pipeline tests.
"""

from __future__ import annotations

import pytest

from data.simulator import MicroserviceSimulator, SERVICE_NAMES


def test_simulator_normal():
    """Test normal (no-fault) simulation."""
    sim = MicroserviceSimulator(seed=42)
    result = sim.simulate_normal(num_steps=30)

    assert len(result.metrics_df) == 30 * len(SERVICE_NAMES)  # 30 steps × 10 services
    assert result.ground_truth_root == "none"
    assert result.affected_services == []
    assert set(result.metrics_df["service"].unique()) == set(SERVICE_NAMES)


def test_simulator_fault_injection():
    """Test fault-injected simulation."""
    sim = MicroserviceSimulator(seed=42)
    result = sim.simulate_incident(
        root_cause="database",
        fault_type="latency_spike",
        severity=5.0,
        num_steps=60,
    )

    assert result.ground_truth_root == "database"
    assert len(result.affected_services) > 0
    assert "auth-service" in result.affected_services  # auth calls database

    # Database should have higher latency during fault window
    db_data = result.metrics_df[result.metrics_df["service"] == "database"]
    assert db_data["latency"].max() > 20  # Baseline is 5ms, spike should be >20ms


def test_simulator_different_fault_types():
    """Test different fault types produce different patterns."""
    sim = MicroserviceSimulator(seed=42)

    latency = sim.simulate_incident(root_cause="database", fault_type="latency_spike")
    error = sim.simulate_incident(root_cause="database", fault_type="error_burst")
    resource = sim.simulate_incident(root_cause="database", fault_type="resource_exhaustion")

    # Each should have different dominant metric spikes
    db_lat = latency.metrics_df[latency.metrics_df["service"] == "database"]
    db_err = error.metrics_df[error.metrics_df["service"] == "database"]
    db_res = resource.metrics_df[resource.metrics_df["service"] == "database"]

    assert db_lat["latency"].max() > db_lat["error_rate"].max()
    assert db_err["error_rate"].max() > 1.0  # Error burst should spike error rate


def test_simulator_training_set():
    """Test training set generation."""
    sim = MicroserviceSimulator(seed=42)
    results = sim.generate_training_set(num_normal=3, num_faults=5, num_steps=20)

    assert len(results) == 8  # 3 normal + 5 fault
    normal_count = sum(1 for r in results if r.ground_truth_root == "none")
    assert normal_count == 3


def test_ingestion_service():
    """Test feature extraction and normalization."""
    from app.services.ingestion import ingestion_service

    sim = MicroserviceSimulator(seed=42)
    result = sim.simulate_normal(num_steps=30)

    # Fit normalizer
    ingestion_service.fit_normalizer(result.metrics_df)

    # Aggregate
    agg = ingestion_service.aggregate_window(result.metrics_df, window_size=5)
    assert len(agg) == 10  # 10 services

    # Extract feature matrix
    from app.services.graph_builder import graph_builder
    graph_builder.initialize_default()
    matrix = ingestion_service.extract_feature_matrix(
        agg, graph_builder.service_names, normalize=True
    )
    assert matrix.shape == (10, 5)


def test_graph_builder():
    """Test graph builder initialization and API response."""
    from app.services.graph_builder import ServiceGraphBuilder

    gb = ServiceGraphBuilder()
    gb.initialize_default()

    assert len(gb.service_names) == 10
    assert len(gb.get_adjacency_list()) == 15

    # Test API response conversion
    response = gb.to_api_response()
    assert len(response.nodes) == 10
    assert len(response.edges) == 15
    assert response.metadata.total_services == 10

    # Test edge index for PyG
    edge_index, node_map = gb.get_edge_index_tensor()
    assert len(edge_index) == 2
    assert len(edge_index[0]) == 30  # 15 edges × 2 (bidirectional)
    assert len(node_map) == 10


def test_mock_llm_reasoner():
    """Test mock LLM response generation."""
    from app.ai_module.llm.prompt_templates import build_mock_response

    result = build_mock_response(
        root_candidates=[("database", 0.95)],
        anomaly_scores={"database": 0.95, "auth-service": 0.78},
        causal_edges=[("database", "auth-service", 0.85)],
        metric_deltas={"database": {"latency": "+340%"}},
    )

    assert result["root_cause"] == "database"
    assert result["confidence"] > 0.8
    assert "database" in result["explanation"]
    assert len(result["recommended_actions"]) > 0


def test_llm_cache():
    """Test LLM response caching."""
    from app.ai_module.llm.cache import RCACache

    cache = RCACache(max_size=10)

    scores = {"database": 0.95, "auth-service": 0.78}
    edges = [("database", "auth-service", 0.85)]
    response = {"root_cause": "database", "confidence": 0.92}

    # Miss
    assert cache.get(scores, edges) is None
    assert cache.stats["misses"] == 1

    # Store
    cache.put(scores, edges, response)

    # Hit
    cached = cache.get(scores, edges)
    assert cached is not None
    assert cached["root_cause"] == "database"
    assert cache.stats["hits"] == 1


def test_continual_learning_replay_buffer():
    """Test experience replay buffer."""
    import torch
    from app.ai_module.continual.replay_buffer import ReplayBuffer

    buffer = ReplayBuffer(max_size=5)

    for i in range(10):
        buffer.add(
            features=torch.randn(10, 5),
            edge_index=torch.randint(0, 10, (2, 20)),
            metadata={"task_id": f"task_{i}"},
        )

    assert buffer.size == 5  # Max size respected
    assert buffer.total_seen == 10

    samples = buffer.sample(3)
    assert len(samples) == 3
