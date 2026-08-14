"""
API Router — aggregates all sub-routers into a single v1 router.
"""

from fastapi import APIRouter

from app.api import graph, health, incidents, metrics, model, rca, ws
from app.api import remediation, feedback, learning

api_router = APIRouter(prefix="/api/v1")

# System
api_router.include_router(health.router)
api_router.include_router(metrics.router)

# Service graph
api_router.include_router(graph.router)

# Incidents & RCA
api_router.include_router(incidents.router)
api_router.include_router(rca.router)

# Auto-remediation
api_router.include_router(remediation.router)

# Feedback loop & learning
api_router.include_router(feedback.router)
api_router.include_router(learning.router)

# Model introspection
api_router.include_router(model.router)

# WebSocket (no prefix — mounted at /api/v1/live)
api_router.include_router(ws.router)
