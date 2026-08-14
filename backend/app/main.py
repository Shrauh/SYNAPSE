"""
SYNAPSE — FastAPI Application Entrypoint.

Root cause analysis for microservice failures using GNN, Causal Inference,
and LLM-powered reasoning with continual learning capabilities.

Startup sequence:
  1. Initialize async SQLite database + create tables
  2. Initialize AI pipeline (GNN + causal + LLM)
  3. Start Kafka consumers (if KAFKA_ENABLED=true)
  4. Start Kafka producer (if KAFKA_ENABLED=true)
  5. Start WebSocket broadcast loop (2s anomaly updates)
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

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

    # 1. Initialize database tables
    await init_db()
    print("[SYNAPSE] Database initialized")

    # 2. Pre-load AI models
    try:
        from app.ai_module.orchestrator import pipeline
        await pipeline.initialize()
        print("[SYNAPSE] AI pipeline initialized")
    except Exception as e:
        print(f"[SYNAPSE] AI pipeline init skipped: {e}")

    # 3. Start Kafka consumers
    try:
        from app.services.kafka_consumer import kafka_consumer
        await kafka_consumer.start()
    except Exception as e:
        print(f"[SYNAPSE] Kafka consumer start skipped: {e}")

    # 4. Start Kafka producer
    try:
        from app.services.kafka_producer import kafka_producer
        await kafka_producer.start()
    except Exception as e:
        print(f"[SYNAPSE] Kafka producer start skipped: {e}")

    # 5. Start WebSocket broadcast loop (every 2 seconds)
    broadcast_task = asyncio.create_task(_broadcast_loop_wrapper())

    print(f"[SYNAPSE] Server started — {settings.app_name} v{settings.app_version}")
    print(f"[SYNAPSE] API docs: http://{settings.host}:{settings.port}/docs")
    print(f"[SYNAPSE] Groq LLM: {'[OK] configured' if settings.groq_api_key else '[NO] not configured (using mock)'}")
    print(f"[SYNAPSE] Kafka: {'[OK] enabled' if settings.kafka_enabled else '[NO] disabled (simulation mode)'}")
    print(f"[SYNAPSE] K8s executor: {'[OK] live' if settings.k8s_enabled else '[NO] simulation mode'}")

    yield

    # Shutdown
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass

    try:
        from app.services.kafka_consumer import kafka_consumer
        await kafka_consumer.stop()
        from app.services.kafka_producer import kafka_producer
        await kafka_producer.stop()
    except Exception:
        pass

    print("[SYNAPSE] Server shutting down cleanly.")


async def _broadcast_loop_wrapper() -> None:
    """Wrapper to run the WebSocket broadcast loop with error recovery."""
    try:
        from app.api.ws import broadcast_loop
        await broadcast_loop()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[SYNAPSE] Broadcast loop crashed: {e}")


app = FastAPI(
    title=settings.app_name,
    description=(
        "AIOps platform for automated Root Cause Analysis of microservice "
        "failures using Graph Neural Networks, Causal Inference, and LLM reasoning.\n\n"
        "**LLM**: Groq llama-3.1-70b-versatile (primary, free) → OpenAI (fallback) → Mock\n"
        "**Causal**: NOTEARS/DECI with W0 prior injection\n"
        "**Remediation**: Conservative Q-Learning (CQL) with K8s executor"
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


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint — API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Self-Evolving Neuro-Symbolic Causal Architecture for AIOps",
        "docs": "/docs",
        "api_prefix": "/api/v1",
        "health": "/api/v1/health",
        "endpoints": {
            "incidents": "/api/v1/incidents",
            "rca": "/api/v1/rca/trigger",
            "graph": "/api/v1/graph/current",
            "remediation": "/api/v1/remediation/execute",
            "feedback": "/api/v1/feedback",
            "learning": "/api/v1/learning/stats",
            "websocket": "/api/v1/live",
        },
    }


@app.get("/health", tags=["Root"], include_in_schema=False)
async def health_shortcut():
    """Convenience shortcut — redirects to /api/v1/health."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/health")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)
