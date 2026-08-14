"""
SYNAPSE Demo Microservice — Base Template.

Generic FastAPI service that exposes Prometheus metrics,
OpenTelemetry traces, and structured logs for SYNAPSE to consume.
"""
import asyncio
import logging
import os
import random
import time
import psutil
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import (
    CollectorRegistry, Counter, Gauge, Histogram,
    generate_latest, CONTENT_TYPE_LATEST,
)

# ── Config ──
SERVICE_NAME = os.getenv("SERVICE_NAME", "unknown-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8080"))
DOWNSTREAM = os.getenv("DOWNSTREAM_SERVICES", "").split(",") if os.getenv("DOWNSTREAM_SERVICES") else []

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","service":"' + SERVICE_NAME + '","level":"%(levelname)s","message":"%(message)s"}',
)
logger = logging.getLogger(SERVICE_NAME)

# ── Prometheus Metrics ──
registry = CollectorRegistry()

REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP requests',
    ['service', 'method', 'endpoint', 'status'],
    registry=registry,
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'Request latency in seconds',
    ['service', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)
ERROR_COUNT = Counter(
    'http_errors_total', 'Total HTTP errors',
    ['service', 'error_type'],
    registry=registry,
)
CPU_USAGE = Gauge('process_cpu_percent', 'CPU usage percent', ['service'], registry=registry)
MEMORY_USAGE = Gauge('process_memory_mb', 'Memory usage in MB', ['service'], registry=registry)
ACTIVE_REQUESTS = Gauge('active_requests', 'Currently active requests', ['service'], registry=registry)

# ── Fault injection state ──
fault_state = {
    "latency_ms": 0,         # Extra latency to add (ms)
    "error_rate": 0.0,       # Probability of returning 500
    "cpu_burn": False,       # Whether to burn CPU
    "memory_leak_mb": 0,     # MB of memory to leak
}
_leaked_memory = []


async def _update_system_metrics():
    """Background task to update CPU/memory gauges every 2s."""
    while True:
        try:
            proc = psutil.Process()
            CPU_USAGE.labels(service=SERVICE_NAME).set(proc.cpu_percent())
            MEMORY_USAGE.labels(service=SERVICE_NAME).set(proc.memory_info().rss / 1024 / 1024)
        except Exception:
            pass
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background metric updater."""
    task = asyncio.create_task(_update_system_metrics())
    logger.info(f"{SERVICE_NAME} started on port {SERVICE_PORT}")
    yield
    task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        ACTIVE_REQUESTS.labels(service=SERVICE_NAME).inc()
        start = time.time()

        # Inject fault: extra latency
        if fault_state["latency_ms"] > 0:
            await asyncio.sleep(fault_state["latency_ms"] / 1000)

        # Inject fault: random errors
        if fault_state["error_rate"] > 0 and random.random() < fault_state["error_rate"]:
            ERROR_COUNT.labels(service=SERVICE_NAME, error_type="injected_500").inc()
            REQUEST_COUNT.labels(service=SERVICE_NAME, method=request.method,
                                endpoint=request.url.path, status="500").inc()
            ACTIVE_REQUESTS.labels(service=SERVICE_NAME).dec()
            logger.error(f"Injected fault: 500 error on {request.url.path}")
            return Response(content="Injected fault", status_code=500)

        try:
            response = await call_next(request)
            duration = time.time() - start
            REQUEST_COUNT.labels(service=SERVICE_NAME, method=request.method,
                                endpoint=request.url.path, status=str(response.status_code)).inc()
            REQUEST_LATENCY.labels(service=SERVICE_NAME, endpoint=request.url.path).observe(duration)
            return response
        except Exception as e:
            ERROR_COUNT.labels(service=SERVICE_NAME, error_type=type(e).__name__).inc()
            logger.error(f"Unhandled error: {e}")
            raise
        finally:
            ACTIVE_REQUESTS.labels(service=SERVICE_NAME).dec()

    @app.get("/metrics")
    async def prometheus_metrics():
        return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": SERVICE_NAME}

    @app.get("/")
    async def root():
        # Simulate some work
        await asyncio.sleep(random.uniform(0.01, 0.05))
        return {"service": SERVICE_NAME, "status": "ok"}

    @app.post("/fault")
    async def inject_fault(
        latency_ms: int = 0,
        error_rate: float = 0.0,
        cpu_burn: bool = False,
        memory_leak_mb: int = 0,
    ):
        """Inject a fault into this service for testing."""
        fault_state["latency_ms"] = latency_ms
        fault_state["error_rate"] = min(error_rate, 1.0)
        fault_state["cpu_burn"] = cpu_burn
        fault_state["memory_leak_mb"] = memory_leak_mb

        if memory_leak_mb > 0:
            _leaked_memory.append(bytearray(memory_leak_mb * 1024 * 1024))

        logger.warning(f"Fault injected: latency={latency_ms}ms, error_rate={error_rate}, cpu_burn={cpu_burn}")
        return {"status": "fault_injected", "state": fault_state}

    @app.post("/fault/clear")
    async def clear_fault():
        """Clear all injected faults."""
        fault_state["latency_ms"] = 0
        fault_state["error_rate"] = 0.0
        fault_state["cpu_burn"] = False
        fault_state["memory_leak_mb"] = 0
        _leaked_memory.clear()
        logger.info("All faults cleared")
        return {"status": "cleared"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
