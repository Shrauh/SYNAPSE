"""
Graph endpoint — current service dependency graph.
"""

from fastapi import APIRouter

from app.models.schemas import GraphResponse
from app.services.graph_builder import graph_builder

router = APIRouter(tags=["Graph"])


@router.get("/graph/current", response_model=GraphResponse)
async def get_current_graph():
    """Return the current service dependency graph with live metrics and anomaly scores."""
    return graph_builder.to_api_response()
