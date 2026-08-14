"""
API Router — aggregates all sub-routers into a single v1 router.
"""

from fastapi import APIRouter

from app.api import continual, graph, health, incidents, metrics, model, rca, severity, ws

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

# Continual Learning
api_router.include_router(continual.router)

# Severity & Recovery
api_router.include_router(severity.router)

# WebSocket (no prefix — mounted at /api/v1/live)
api_router.include_router(ws.router)

