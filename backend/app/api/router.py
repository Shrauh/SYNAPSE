from fastapi import APIRouter

from app.api import graph, health, incidents, metrics, model, rca, severity, ws
from app.api import fault_injection, ollama

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

# Severity & Recovery
api_router.include_router(severity.router)

# WebSocket (no prefix — mounted at /api/v1/live)
api_router.include_router(ws.router)

# Fault Injection & Ollama
api_router.include_router(fault_injection.router)
api_router.include_router(ollama.router)

# K8s
from app.api import k8s
api_router.include_router(k8s.router)

from app.api import system
api_router.include_router(system.router)

from app.api import evaluation
api_router.include_router(evaluation.router)

from app.api import logs
api_router.include_router(logs.router)

from app.api import notify
api_router.include_router(notify.router)

from app.api import alerts
api_router.include_router(alerts.router)

from app.api import connect
api_router.include_router(connect.router)

# ── P1: Actions, Reports, Audit, Platform Health ─────────────────────────────
from app.api.actions import (
    incident_actions_router,
    actions_router,
    report_router,
    audit_router,
    platform_router,
)

# Incident-scoped: /api/v1/incidents/{id}/actions, /incidents/{id}/download, etc.
api_router.include_router(incident_actions_router, prefix="/incidents")
api_router.include_router(report_router, prefix="/incidents")

# Standalone: /api/v1/actions/{action_id}
api_router.include_router(actions_router)

# Audit: /api/v1/audit
api_router.include_router(audit_router)

# Platform health: /api/v1/platform/health
api_router.include_router(platform_router)

# ── Authentication ────────────────────────────────────────────────────────────
from app.api.auth import router as auth_router
api_router.include_router(auth_router)
