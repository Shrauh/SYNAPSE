"""
Graph endpoint — current service dependency graph.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.schemas import (
    GraphEdge,
    GraphMetadata,
    GraphNode,
    GraphResponse,
    ServiceMetrics,
)

router = APIRouter(tags=["Graph"])


def _build_default_graph() -> GraphResponse:
    """Build the default 10-service topology for demo/dev.

    This will be replaced by the live graph_builder service in Phase 2.
    """
    services = [
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

    edges_def = [
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

    nodes = [
        GraphNode(
            id=sid,
            label=label,
            type=stype,
            metrics=ServiceMetrics(),
            anomaly_score=0.0,
            status="healthy",
        )
        for sid, label, stype in services
    ]

    edges = [
        GraphEdge(
            source=src,
            target=tgt,
            call_type=ct,
            avg_latency=lat,
            call_frequency=freq,
            weight=round(freq / 500, 2),
        )
        for src, tgt, ct, lat, freq in edges_def
    ]

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        metadata=GraphMetadata(
            total_services=len(nodes),
            total_edges=len(edges),
            last_updated=datetime.now(timezone.utc),
        ),
    )


# Module-level cached graph (replaced by graph_builder in Phase 2)
_current_graph = _build_default_graph()


@router.get("/graph/current", response_model=GraphResponse)
async def get_current_graph():
    """Return the current service dependency graph."""
    return _current_graph
