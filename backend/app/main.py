"""
SYNAPSE — FastAPI Application Entrypoint.

Root cause analysis for microservice failures using GNN, Causal Inference,
and LLM-powered reasoning with continual learning capabilities.
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend root directory is in sys.path for Windows spawned workers
_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.db.database import init_db

# Track application startup time for health checks
_start_time: float = 0.0


def get_uptime() -> float:
    """Return seconds since application startup."""
    return time.time() - _start_time


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    global _start_time
    _start_time = time.time()

    # Initialize database tables
    await init_db()

    # Pre-load AI models if available
    try:
        from app.ai_module.orchestrator import pipeline
        await pipeline.initialize()
        print("[SYNAPSE] AI pipeline initialized successfully.")
    except Exception as e:
        print(f"[SYNAPSE] AI pipeline init skipped: {e}")

    print(f"[SYNAPSE] Server started — {settings.app_name} v{settings.app_version}")

    yield

    # Shutdown cleanup
    print("[SYNAPSE] Server shutting down.")


app = FastAPI(
    title=settings.app_name,
    description=(
        "AIOps platform for automated Root Cause Analysis of microservice "
        "failures using Graph Neural Networks, Causal Inference, and LLM reasoning."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS — allow frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes under /api/v1
app.include_router(api_router)

# Mount built React frontend if available
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists() and (_frontend_dist / "index.html").exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    if (_frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        fav = _frontend_dist / "favicon.svg"
        if fav.exists():
            return FileResponse(str(fav))
        from fastapi.responses import Response
        return Response(status_code=204)

    # Catch-all route to serve React SPA (Dashboard, Graph, Incidents, Simulate, Model Status)
    from fastapi import Request

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str, request: Request):
        # Allow /docs, /redoc, /openapi.json, /api to pass through
        if full_path.startswith(("docs", "redoc", "openapi.json", "api")):
            return {"detail": "Not Found"}
        # If client explicitly requests application/json on root, return API JSON info
        accept = request.headers.get("accept", "")
        if full_path == "" and "text/html" not in accept and ("application/json" in accept or "*/*" in accept):
            return {
                "name": settings.app_name,
                "version": settings.app_version,
                "description": "Microservice RCA using GNN + Causal Inference + LLM",
                "docs": "/docs",
                "api_prefix": "/api/v1",
                "health": "/api/v1/health",
            }
        target = _frontend_dist / full_path
        if full_path and target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(_frontend_dist / "index.html"))
else:
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint — API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "description": "Microservice RCA using GNN + Causal Inference + LLM",
            "docs": "/docs",
            "api_prefix": "/api/v1",
            "health": "/api/v1/health",
        }

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon_fallback():
        from fastapi.responses import Response
        return Response(status_code=204)

@app.get("/health", tags=["Root"], include_in_schema=False)
async def health_shortcut():
    """Convenience shortcut — redirects to /api/v1/health."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/health")

