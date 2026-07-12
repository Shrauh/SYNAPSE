"""
API Router — aggregates all sub-routers into a single v1 router.
"""

from fastapi import APIRouter

from app.api import graph, health, incidents, metrics, model, rca, ws

api_router = APIRouter(prefix="/api/v1")

# System
api_router.include_router(health.router)
api_router.include_router(metrics.router)

# Service graph
api_router.include_router(graph.router)

# Incidents & RCA
api_router.include_router(incidents.router)
api_router.include_router(rca.router)

# Model introspection
api_router.include_router(model.router)

# WebSocket (no prefix — mounted at /api/v1/live)
api_router.include_router(ws.router)
