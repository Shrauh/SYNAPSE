"""
SYNAPSE Database Seeder — Pre-populates realistic demo incidents when database is empty.

Provides 5 high-fidelity demo incidents with validated root causes,
causal propagation chains, anomaly score distributions, and RCA reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.db.models import Incident, RCAResult

logger = logging.getLogger("synapse.seed")


def _get_demo_data() -> List[Tuple[Incident, RCAResult]]:
    """Generate demo incidents with relative timestamps so they appear recent."""
    now = datetime.now(timezone.utc)

    # 1. database latency_spike -> root=database, confidence=0.94, chain="database -> auth-service -> api-gateway"
    inc1_id = "inc_demo_01"
    inc1_time = now - timedelta(minutes=25)
    inc1 = Incident(
        id=inc1_id,
        title="Database connection pool exhaustion and query latency spike",
        description=(
            "PostgreSQL connection pool exhausted under heavy analytical load, "
            "causing query delays and cascading timeouts up to auth-service and api-gateway."
        ),
        status="detected",
        severity="critical",
        root_cause_service="database",
        confidence=0.94,
        fault_type="latency_spike",
        affected_services=["database", "auth-service", "order-service", "user-service", "api-gateway"],
        anomaly_scores={
            "database": 0.94,
            "auth-service": 0.68,
            "order-service": 0.52,
            "user-service": 0.44,
            "api-gateway": 0.35,
            "payment-service": 0.12,
            "inventory-service": 0.08,
            "notification-service": 0.05,
            "search-service": 0.03,
            "cache-service": 0.02,
        },
        timeline=[
            {"time": (inc1_time + timedelta(seconds=15)).strftime("%H:%M:%S"), "event": "Database active connection count breached 95% limit", "score": 0.72},
            {"time": (inc1_time + timedelta(seconds=35)).strftime("%H:%M:%S"), "event": "Database p99 query latency spiked to 2,150ms", "score": 0.94},
            {"time": (inc1_time + timedelta(seconds=55)).strftime("%H:%M:%S"), "event": "Auth-service connection acquisition timeouts", "score": 0.68},
            {"time": (inc1_time + timedelta(seconds=75)).strftime("%H:%M:%S"), "event": "API Gateway 504 Gateway Timeout rate exceeded 8%", "score": 0.35},
        ],
        window_start=inc1_time - timedelta(minutes=10),
        window_end=inc1_time + timedelta(minutes=5),
        detected_at=inc1_time,
        resolved_at=None,
    )
    rca1 = RCAResult(
        incident_id=inc1_id,
        root_cause_service="database",
        confidence=0.94,
        fault_type="latency_spike",
        explanation=(
            "Unindexed analytical queries saturated primary PostgreSQL connection slots (100/100 connections). "
            "Auth-service session lookups blocked waiting for connections, propagating latency spikes "
            "directly up to the API Gateway."
        ),
        propagation_chain="database → auth-service → api-gateway",
        metric_deltas={
            "database": {"latency": "+390%", "error_rate": "+12.4%", "cpu": "+48%"},
            "auth-service": {"latency": "+210%", "error_rate": "+7.8%", "cpu": "+16%"},
            "api-gateway": {"latency": "+145%", "error_rate": "+5.2%", "cpu": "+6%"},
        },
        recommended_actions=[
            "Scale database connection pool limits or deploy PgBouncer connection pooling",
            "Kill idle-in-transaction and unindexed queries running > 30 seconds",
            "Enable Redis query caching for frequent auth-service session checks",
        ],
        causal_graph={
            "nodes": [
                {"id": "database", "anomaly_score": 0.94, "is_root": True},
                {"id": "auth-service", "anomaly_score": 0.68, "is_root": False},
                {"id": "api-gateway", "anomaly_score": 0.35, "is_root": False},
            ],
            "edges": [
                {"source": "database", "target": "auth-service", "strength": 0.88},
                {"source": "auth-service", "target": "api-gateway", "strength": 0.76},
            ],
        },
        model_info={
            "gnn_type": "VAE-GNN Autoencoder",
            "maml_adapted": True,
            "adaptation_steps": 3,
            "causal_method": "DECI (Differentiable Causal Discovery)",
            "h_score": 0.0021,
            "drift_score": 0.084,
            "execution_time_ms": 142.5,
            "severity_level": "L2_MEDIUM",
            "recovery_action": "Scale Connection Pool & Kill Stalled Queries",
            "recovery_success": True,
        },
        created_at=inc1_time + timedelta(seconds=80),
    )

    # 2. payment-service error_burst -> root=payment-service, confidence=0.89, chain="payment-service -> order-service -> api-gateway"
    inc2_id = "inc_demo_02"
    inc2_time = now - timedelta(hours=1, minutes=10)
    inc2 = Incident(
        id=inc2_id,
        title="Payment service HTTP 500 error burst during checkout peak",
        description=(
            "Downstream payment gateway throttling triggered unhandled exceptions and thread exhaustion "
            "in payment-service, failing checkout transactions in order-service."
        ),
        status="detected",
        severity="critical",
        root_cause_service="payment-service",
        confidence=0.89,
        fault_type="error_burst",
        affected_services=["payment-service", "order-service", "api-gateway", "notification-service"],
        anomaly_scores={
            "payment-service": 0.89,
            "order-service": 0.62,
            "api-gateway": 0.38,
            "notification-service": 0.22,
            "database": 0.15,
            "inventory-service": 0.09,
            "user-service": 0.05,
            "auth-service": 0.04,
            "search-service": 0.02,
            "cache-service": 0.01,
        },
        timeline=[
            {"time": (inc2_time + timedelta(seconds=10)).strftime("%H:%M:%S"), "event": "Third-party payment gateway handshake timeouts", "score": 0.58},
            {"time": (inc2_time + timedelta(seconds=25)).strftime("%H:%M:%S"), "event": "Payment-service HTTP 500 error rate surged to 35.2%", "score": 0.89},
            {"time": (inc2_time + timedelta(seconds=45)).strftime("%H:%M:%S"), "event": "Order-service checkout rollbacks elevated", "score": 0.62},
            {"time": (inc2_time + timedelta(seconds=60)).strftime("%H:%M:%S"), "event": "API Gateway checkout 500 responses surfacing to clients", "score": 0.38},
        ],
        window_start=inc2_time - timedelta(minutes=10),
        window_end=inc2_time + timedelta(minutes=5),
        detected_at=inc2_time,
        resolved_at=None,
    )
    rca2 = RCAResult(
        incident_id=inc2_id,
        root_cause_service="payment-service",
        confidence=0.89,
        fault_type="error_burst",
        explanation=(
            "External payment gateway rate limits triggered unhandled connection exceptions in payment-service. "
            "Thread pool exhaustion cascaded synchronous checkout failures into order-service."
        ),
        propagation_chain="payment-service → order-service → api-gateway",
        metric_deltas={
            "payment-service": {"error_rate": "+35.2%", "latency": "+195%", "cpu": "+28%"},
            "order-service": {"error_rate": "+21.8%", "latency": "+92%", "cpu": "+12%"},
            "api-gateway": {"error_rate": "+8.4%", "latency": "+45%", "cpu": "+4%"},
        },
        recommended_actions=[
            "Activate circuit breaker and route checkout requests to secondary payment provider",
            "Scale payment-service pods from 3 to 6 to handle asynchronous retry queue",
            "Enable idempotent retry queue in order-service for transient payment drops",
        ],
        causal_graph={
            "nodes": [
                {"id": "payment-service", "anomaly_score": 0.89, "is_root": True},
                {"id": "order-service", "anomaly_score": 0.62, "is_root": False},
                {"id": "api-gateway", "anomaly_score": 0.38, "is_root": False},
            ],
            "edges": [
                {"source": "payment-service", "target": "order-service", "strength": 0.91},
                {"source": "order-service", "target": "api-gateway", "strength": 0.74},
            ],
        },
        model_info={
            "gnn_type": "VAE-GNN Autoencoder",
            "maml_adapted": True,
            "adaptation_steps": 3,
            "causal_method": "DECI (Differentiable Causal Discovery)",
            "h_score": 0.0035,
            "drift_score": 0.112,
            "execution_time_ms": 138.2,
            "severity_level": "L2_MEDIUM",
            "recovery_action": "Enable Fallback Payment Processor",
            "recovery_success": True,
        },
        created_at=inc2_time + timedelta(seconds=65),
    )

    # 3. cache-service resource_exhaustion -> root=cache-service, confidence=0.87, chain="cache-service -> database -> auth-service"
    inc3_id = "inc_demo_03"
    inc3_time = now - timedelta(hours=2, minutes=45)
    inc3 = Incident(
        id=inc3_id,
        title="Cache service Redis memory exhaustion and key eviction storm",
        description=(
            "Redis maxmemory ceiling hit without TTL eviction, forcing cache misses and cascading "
            "query pressure to the persistent database store."
        ),
        status="detected",
        severity="high",
        root_cause_service="cache-service",
        confidence=0.87,
        fault_type="resource_exhaustion",
        affected_services=["cache-service", "database", "auth-service", "inventory-service"],
        anomaly_scores={
            "cache-service": 0.87,
            "database": 0.61,
            "auth-service": 0.49,
            "inventory-service": 0.44,
            "api-gateway": 0.28,
            "order-service": 0.14,
            "user-service": 0.10,
            "payment-service": 0.05,
            "notification-service": 0.02,
            "search-service": 0.01,
        },
        timeline=[
            {"time": (inc3_time + timedelta(seconds=15)).strftime("%H:%M:%S"), "event": "Redis used_memory exceeded 98% (3.92GB / 4.00GB)", "score": 0.65},
            {"time": (inc3_time + timedelta(seconds=30)).strftime("%H:%M:%S"), "event": "Cache-service eviction storm: 45,000 keys evicted/sec", "score": 0.87},
            {"time": (inc3_time + timedelta(seconds=50)).strftime("%H:%M:%S"), "event": "Database read throughput jumped 320% due to cache misses", "score": 0.61},
            {"time": (inc3_time + timedelta(seconds=70)).strftime("%H:%M:%S"), "event": "Auth-service token validation latency elevated", "score": 0.49},
        ],
        window_start=inc3_time - timedelta(minutes=10),
        window_end=inc3_time + timedelta(minutes=5),
        detected_at=inc3_time,
        resolved_at=None,
    )
    rca3 = RCAResult(
        incident_id=inc3_id,
        root_cause_service="cache-service",
        confidence=0.87,
        fault_type="resource_exhaustion",
        explanation=(
            "Redis session cache reached 100% capacity due to session TTL misconfiguration. "
            "Massive key eviction triggered a cache stampede, directing all token and inventory "
            "validation queries directly to the database."
        ),
        propagation_chain="cache-service → database → auth-service",
        metric_deltas={
            "cache-service": {"memory": "+48.5%", "error_rate": "+5.8%", "cpu": "+38%"},
            "database": {"request_rate": "+320%", "latency": "+135%", "cpu": "+42%"},
            "auth-service": {"latency": "+85%", "error_rate": "+2.1%", "cpu": "+11%"},
        },
        recommended_actions=[
            "Increase Redis cluster memory allocation from 4Gi to 8Gi",
            "Configure maxmemory-policy to volatile-lru",
            "Audit session token key generation and enforce mandatory 24h TTL",
        ],
        causal_graph={
            "nodes": [
                {"id": "cache-service", "anomaly_score": 0.87, "is_root": True},
                {"id": "database", "anomaly_score": 0.61, "is_root": False},
                {"id": "auth-service", "anomaly_score": 0.49, "is_root": False},
            ],
            "edges": [
                {"source": "cache-service", "target": "database", "strength": 0.85},
                {"source": "database", "target": "auth-service", "strength": 0.71},
            ],
        },
        model_info={
            "gnn_type": "VAE-GNN Autoencoder",
            "maml_adapted": False,
            "adaptation_steps": 0,
            "causal_method": "DECI (Differentiable Causal Discovery)",
            "h_score": 0.0018,
            "drift_score": 0.065,
            "execution_time_ms": 115.0,
            "severity_level": "L1_SIMPLE",
            "recovery_action": "Flush Cache / Increase Memory",
            "recovery_success": True,
        },
        created_at=inc3_time + timedelta(seconds=75),
    )

    # 4. auth-service latency_spike -> root=auth-service, confidence=0.91, chain="auth-service -> api-gateway"
    inc4_id = "inc_demo_04"
    inc4_time = now - timedelta(hours=4, minutes=15)
    inc4 = Incident(
        id=inc4_id,
        title="Auth service JWT signing key lock contention and latency spike",
        description=(
            "Cryptographic lock contention on asymmetric key signing in auth-service "
            "during high concurrent authentication peak."
        ),
        status="detected",
        severity="high",
        root_cause_service="auth-service",
        confidence=0.91,
        fault_type="latency_spike",
        affected_services=["auth-service", "api-gateway", "user-service"],
        anomaly_scores={
            "auth-service": 0.91,
            "api-gateway": 0.58,
            "user-service": 0.42,
            "order-service": 0.18,
            "database": 0.15,
            "payment-service": 0.08,
            "cache-service": 0.06,
            "inventory-service": 0.04,
            "notification-service": 0.02,
            "search-service": 0.01,
        },
        timeline=[
            {"time": (inc4_time + timedelta(seconds=10)).strftime("%H:%M:%S"), "event": "Auth-service CPU spike from concurrent RSA-2048 signing", "score": 0.68},
            {"time": (inc4_time + timedelta(seconds=25)).strftime("%H:%M:%S"), "event": "Auth-service token issuance p99 latency breached 1,450ms", "score": 0.91},
            {"time": (inc4_time + timedelta(seconds=40)).strftime("%H:%M:%S"), "event": "API Gateway JWT verification middleware queue depth > 500", "score": 0.58},
        ],
        window_start=inc4_time - timedelta(minutes=10),
        window_end=inc4_time + timedelta(minutes=5),
        detected_at=inc4_time,
        resolved_at=None,
    )
    rca4 = RCAResult(
        incident_id=inc4_id,
        root_cause_service="auth-service",
        confidence=0.91,
        fault_type="latency_spike",
        explanation=(
            "Auth service instances experienced heavy mutex contention on the RSA token signing routine "
            "under a 1,200 req/s login surge. Because API Gateway verifies token validity synchronously, "
            "downstream clients experienced request stalls."
        ),
        propagation_chain="auth-service → api-gateway",
        metric_deltas={
            "auth-service": {"latency": "+285%", "cpu": "+62%", "error_rate": "+3.4%"},
            "api-gateway": {"latency": "+115%", "error_rate": "+4.8%", "cpu": "+14%"},
        },
        recommended_actions=[
            "Switch token signing algorithm from RSA-2048 to Ed25519 for 10x faster verification",
            "Scale auth-service replicas from 2 to 5 via Horizontal Pod Autoscaler",
            "Cache public key verification results in API Gateway memory for 5 minutes",
        ],
        causal_graph={
            "nodes": [
                {"id": "auth-service", "anomaly_score": 0.91, "is_root": True},
                {"id": "api-gateway", "anomaly_score": 0.58, "is_root": False},
            ],
            "edges": [
                {"source": "auth-service", "target": "api-gateway", "strength": 0.92},
            ],
        },
        model_info={
            "gnn_type": "VAE-GNN Autoencoder",
            "maml_adapted": True,
            "adaptation_steps": 2,
            "causal_method": "DECI (Differentiable Causal Discovery)",
            "h_score": 0.0029,
            "drift_score": 0.078,
            "execution_time_ms": 128.4,
            "severity_level": "L2_MEDIUM",
            "recovery_action": "HPA Scale Pods",
            "recovery_success": True,
        },
        created_at=inc4_time + timedelta(seconds=45),
    )

    # 5. order-service error_burst -> root=order-service, confidence=0.86, chain="order-service -> api-gateway"
    inc5_id = "inc_demo_05"
    inc5_time = now - timedelta(hours=6, minutes=30)
    inc5 = Incident(
        id=inc5_id,
        title="Order service serialization error burst following schema migration",
        description=(
            "Strict schema parsing failure in order-service handling legacy mobile client checkout requests."
        ),
        status="detected",
        severity="critical",
        root_cause_service="order-service",
        confidence=0.86,
        fault_type="error_burst",
        affected_services=["order-service", "api-gateway", "inventory-service"],
        anomaly_scores={
            "order-service": 0.86,
            "api-gateway": 0.55,
            "inventory-service": 0.32,
            "payment-service": 0.20,
            "database": 0.12,
            "notification-service": 0.08,
            "cache-service": 0.04,
            "auth-service": 0.03,
            "user-service": 0.02,
            "search-service": 0.01,
        },
        timeline=[
            {"time": (inc5_time + timedelta(seconds=10)).strftime("%H:%M:%S"), "event": "Order-service deployment rollout v2.4.1 completed", "score": 0.35},
            {"time": (inc5_time + timedelta(seconds=25)).strftime("%H:%M:%S"), "event": "Order-service deserialization exception rate reached 42%", "score": 0.86},
            {"time": (inc5_time + timedelta(seconds=45)).strftime("%H:%M:%S"), "event": "API Gateway order route returning 500 Bad Gateway", "score": 0.55},
        ],
        window_start=inc5_time - timedelta(minutes=10),
        window_end=inc5_time + timedelta(minutes=5),
        detected_at=inc5_time,
        resolved_at=None,
    )
    rca5 = RCAResult(
        incident_id=inc5_id,
        root_cause_service="order-service",
        confidence=0.86,
        fault_type="error_burst",
        explanation=(
            "A recent order-service release activated strict Pydantic validation that rejected legacy "
            "client checkout payloads with missing billing fields, causing an error burst propagating to API Gateway."
        ),
        propagation_chain="order-service → api-gateway",
        metric_deltas={
            "order-service": {"error_rate": "+42.1%", "cpu": "+19%", "latency": "+35%"},
            "api-gateway": {"error_rate": "+18.7%", "latency": "+42%", "cpu": "+8%"},
        },
        recommended_actions=[
            "Rollback order-service deployment to previous stable revision v2.4.0",
            "Relax schema validation to provide default fallbacks for legacy client requests",
            "Add automated schema regression testing for legacy mobile clients",
        ],
        causal_graph={
            "nodes": [
                {"id": "order-service", "anomaly_score": 0.86, "is_root": True},
                {"id": "api-gateway", "anomaly_score": 0.55, "is_root": False},
            ],
            "edges": [
                {"source": "order-service", "target": "api-gateway", "strength": 0.89},
            ],
        },
        model_info={
            "gnn_type": "VAE-GNN Autoencoder",
            "maml_adapted": True,
            "adaptation_steps": 3,
            "causal_method": "DECI (Differentiable Causal Discovery)",
            "h_score": 0.0031,
            "drift_score": 0.095,
            "execution_time_ms": 134.7,
            "severity_level": "L3_COMPLEX",
            "recovery_action": "Rollback Deployment",
            "recovery_success": True,
        },
        created_at=inc5_time + timedelta(seconds=50),
    )

    return [(inc1, rca1), (inc2, rca2), (inc3, rca3), (inc4, rca4), (inc5, rca5)]


async def seed_demo_data(session: AsyncSession | None = None, force: bool = False) -> int:
    """
    Seed realistic demo incidents if the database is currently empty.

    Args:
        session: Optional existing AsyncSession. If None, creates a new session.
        force: If True, seeds even if database is not empty.

    Returns:
        Number of incidents seeded.
    """
    async def _do_seed(s: AsyncSession) -> int:
        if not force:
            count_result = await s.execute(select(func.count(Incident.id)))
            existing_count = count_result.scalar() or 0
            if existing_count > 0:
                logger.info(f"Database already contains {existing_count} incidents, skipping seed.")
                return 0

        demo_pairs = _get_demo_data()
        for inc, rca in demo_pairs:
            s.add(inc)
            s.add(rca)

        await s.commit()
        logger.info(f"Successfully seeded {len(demo_pairs)} realistic demo incidents.")
        return len(demo_pairs)

    if session is not None:
        return await _do_seed(session)
    else:
        async with async_session() as new_session:
            return await _do_seed(new_session)
