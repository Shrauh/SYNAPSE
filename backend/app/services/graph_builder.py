"""
SYNAPSE Graph Builder — Service Dependency Graph Construction.

Builds and maintains a NetworkX DiGraph representing the microservice
topology. Provides conversion utilities for API responses and
PyTorch Geometric input construction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from app.models.schemas import (
    GraphEdge,
    GraphMetadata,
    GraphNode,
    GraphResponse,
    ServiceMetrics,
)

# ──────────────────────────────────────────────
# Default Topology
# ──────────────────────────────────────────────

DEFAULT_SERVICES = [
    ("api-gateway", "API Gateway", "gateway"),
    ("auth-service", "Auth Service", "service"),
    ("user-service", "User Service", "service"),
    ("payment-service", "Payment Service", "service"),
    ("order-service", "Order Service", "service"),
    ("inventory-service", "Inventory Service", "service"),
    ("notification-service", "Notification Service", "service"),
    ("search-service", "Search Service", "service"),
    ("cache-service", "Cache Service", "infrastructure"),
    ("database", "Database", "infrastructure"),
]

DEFAULT_EDGES: List[Tuple[str, str, str, float, float]] = [
    ("api-gateway", "auth-service", "http", 8.5, 450),
    ("api-gateway", "user-service", "http", 12.0, 300),
    ("api-gateway", "order-service", "http", 15.0, 200),
    ("api-gateway", "search-service", "http", 10.0, 150),
    ("auth-service", "database", "tcp", 5.0, 400),
    ("auth-service", "cache-service", "tcp", 2.0, 380),
    ("user-service", "database", "tcp", 6.0, 280),
    ("order-service", "payment-service", "http", 20.0, 190),
    ("order-service", "inventory-service", "http", 10.0, 185),
    ("order-service", "database", "tcp", 7.0, 195),
    ("payment-service", "database", "tcp", 8.0, 180),
    ("payment-service", "notification-service", "async", 3.0, 170),
    ("inventory-service", "database", "tcp", 5.0, 160),
    ("inventory-service", "cache-service", "tcp", 2.5, 140),
    ("notification-service", "cache-service", "tcp", 1.5, 100),
]


class ServiceGraphBuilder:
    """Builds and manages the service dependency graph."""

    def __init__(self):
        self._graph: nx.DiGraph = nx.DiGraph()
        self._service_info: Dict[str, Dict[str, str]] = {}
        self._node_metrics: Dict[str, Dict[str, float]] = {}
        self._anomaly_scores: Dict[str, float] = {}
        self._last_updated: Optional[datetime] = None
        self._initialized = False

    def initialize_default(self) -> None:
        """Build the default 10-service topology."""
        self._graph.clear()
        self._service_info.clear()
        self._node_metrics.clear()
        self._anomaly_scores.clear()

        for sid, label, stype in DEFAULT_SERVICES:
            self._graph.add_node(sid)
            self._service_info[sid] = {"label": label, "type": stype}
            self._node_metrics[sid] = {
                "latency": 0.0, "error_rate": 0.0,
                "cpu": 0.0, "memory": 0.0, "request_rate": 0.0,
            }
            self._anomaly_scores[sid] = 0.0

        for src, tgt, call_type, latency, freq in DEFAULT_EDGES:
            self._graph.add_edge(
                src, tgt,
                call_type=call_type,
                avg_latency=latency,
                call_frequency=freq,
                weight=round(freq / 500, 2),
            )

        self._last_updated = datetime.now(timezone.utc)
        self._initialized = True

    @property
    def graph(self) -> nx.DiGraph:
        """Get the current NetworkX graph. Initializes if needed."""
        if not self._initialized:
            self.initialize_default()
        return self._graph

    @property
    def service_names(self) -> List[str]:
        """Ordered list of service names (stable ordering for GNN)."""
        return sorted(self.graph.nodes())

    @property
    def node_index_map(self) -> Dict[str, int]:
        """Map service name → integer index (for PyG)."""
        return {name: i for i, name in enumerate(self.service_names)}

    def update_node_metrics(
        self, service: str, metrics: Dict[str, float]
    ) -> None:
        """Update metrics for a single service node."""
        if service in self._node_metrics:
            self._node_metrics[service].update(metrics)
            self._last_updated = datetime.now(timezone.utc)

    def update_all_metrics(
        self, metrics_map: Dict[str, Dict[str, float]]
    ) -> None:
        """Bulk-update metrics for multiple services."""
        for svc, metrics in metrics_map.items():
            self.update_node_metrics(svc, metrics)

    def update_anomaly_scores(
        self, scores: Dict[str, float]
    ) -> None:
        """Update anomaly scores from GNN inference."""
        self._anomaly_scores.update(scores)
        self._last_updated = datetime.now(timezone.utc)

    def get_upstream_callers(self, service: str) -> List[str]:
        """Get services that call this service (predecessors)."""
        return list(self.graph.predecessors(service))

    def get_downstream_callees(self, service: str) -> List[str]:
        """Get services this service calls (successors)."""
        return list(self.graph.successors(service))

    def get_adjacency_list(self) -> List[Tuple[str, str]]:
        """Get edges as (source, target) pairs."""
        return list(self.graph.edges())

    def get_edge_index_tensor(self) -> Tuple[List[List[int]], Dict[str, int]]:
        """Get edge index in COO format for PyTorch Geometric.

        Returns:
            Tuple of (edge_index as [[src_indices], [tgt_indices]], node_index_map)
        """
        idx_map = self.node_index_map
        sources = []
        targets = []
        for src, tgt in self.graph.edges():
            sources.append(idx_map[src])
            targets.append(idx_map[tgt])
            # Add reverse edges for undirected message passing
            sources.append(idx_map[tgt])
            targets.append(idx_map[src])
        return [sources, targets], idx_map

    def to_api_response(self) -> GraphResponse:
        """Convert current graph state to API response schema."""
        if not self._initialized:
            self.initialize_default()

        nodes = []
        for sid in self.service_names:
            info = self._service_info.get(sid, {"label": sid, "type": "service"})
            m = self._node_metrics.get(sid, {})
            score = self._anomaly_scores.get(sid, 0.0)

            status = "healthy"
            if score > 0.8:
                status = "critical"
            elif score > 0.6:
                status = "warning"
            elif score > 0.4:
                status = "degraded"

            nodes.append(GraphNode(
                id=sid,
                label=info["label"],
                type=info["type"],
                metrics=ServiceMetrics(
                    latency=m.get("latency", 0.0),
                    error_rate=m.get("error_rate", 0.0),
                    cpu=m.get("cpu", 0.0),
                    memory=m.get("memory", 0.0),
                    request_rate=m.get("request_rate", 0.0),
                ),
                anomaly_score=score,
                status=status,
            ))

        edges = []
        for src, tgt, data in self.graph.edges(data=True):
            edges.append(GraphEdge(
                source=src,
                target=tgt,
                call_type=data.get("call_type", "http"),
                avg_latency=data.get("avg_latency", 0.0),
                call_frequency=data.get("call_frequency", 0.0),
                weight=data.get("weight", 0.0),
            ))

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(
                total_services=len(nodes),
                total_edges=len(edges),
                last_updated=self._last_updated,
            ),
        )


# Module-level singleton
graph_builder = ServiceGraphBuilder()
