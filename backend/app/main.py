"""
SYNAPSE — FastAPI Application Entrypoint.

Root cause analysis for microservice failures using GNN, Causal Inference,
and LLM-powered reasoning with continual learning capabilities.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Configure structured logging for production
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("synapse")

# Ensure backend root directory is in sys.path for Windows spawned workers
_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.k8s import router as k8s_router
from app.config import settings
from app.db.database import init_db

from app.utils.uptime import set_start_time, get_uptime  # noqa: F401 (re-exported)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    set_start_time()

    # Initialize database tables
    await init_db()

    # Seed demo incidents if database is empty
    try:
        from app.db.seed import seed_demo_data
        seeded_count = await seed_demo_data()
        if seeded_count > 0:
            logger.info(f"Database seeded with {seeded_count} realistic demo incidents.")
    except Exception as e:
        logger.warning(f"Database seeding skipped: {e}")

    # Pre-load AI models if available
    try:
        from app.ai_module.orchestrator import pipeline
        await pipeline.initialize()
        # Pre-train on minimal data so first simulate is fast
        if not pipeline._model_trained:
            logger.info("Pre-training GNN baseline (5 scenarios, 10 epochs)...")
            await pipeline.train_on_normal_data(num_scenarios=5, epochs=10)
            logger.info("GNN pre-training complete.")
        logger.info("AI pipeline initialized successfully.")
    except Exception as e:
        logger.warning(f"AI pipeline init skipped: {e}")

    # Start periodic background task for WebSocket anomaly updates
    from app.api.ws import periodic_anomaly_broadcast
    anomaly_broadcast_task = asyncio.create_task(periodic_anomaly_broadcast())

    logger.info(f"Server started — {settings.app_name} v{settings.app_version}")

    yield

    # Shutdown cleanup
    logger.info("Server shutting down.")
    anomaly_broadcast_task.cancel()
    try:
        await anomaly_broadcast_task
    except asyncio.CancelledError:
        pass
    from app.db.database import shutdown_db
    await shutdown_db()


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
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:80",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes under /api/v1
app.include_router(api_router)
app.include_router(k8s_router, prefix="/api/v1")

@app.get("/health", tags=["Root"], include_in_schema=False)
async def health_shortcut():
    """Convenience shortcut — redirects to /api/v1/health."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/health")


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
        # Add no-cache headers for index.html so browser always gets latest build
        from starlette.responses import HTMLResponse
        index_path = _frontend_dist / "index.html"
        html_content = index_path.read_text()
        return HTMLResponse(
            content=html_content,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
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


