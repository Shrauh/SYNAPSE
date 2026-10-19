"""
SYNAPSE Demo Data Seeding Script.

Seeds 10 diverse, realistic pre-existing incidents across 4 microservice topologies:
- default (SYNAPSE Simulator - 10 services)
- healthcare (HealthCare Stack - 4 services)
- fintech (FinTech Stack - 4 services)
- online-boutique (Google Online Boutique - 10 services)

Each incident includes:
- Distinct fault types: latency_spike, error_burst, cpu_overload, memory_leak, connection_timeout
- Realistic confidence scores (0.85 - 0.99)
- Multi-node propagation chains matching topology dependency DAGs
- Multi-tier severity levels (L1_MINOR, L2_CASCADING, L3_CRITICAL, L4_CATASTROPHIC)
- SRE concept-rich explanations (SLO/SLA, Golden Signals, cgroups, circuit breakers, backpressure)
- Spread across the last 7 days
- Multiple statuses: resolved, investigating, mitigated
- Full RCA result DAGs, metric deltas, recommended actions, recovery action logs, and pattern history

Usage:
    cd d:\\Codes\\SYNAPSE\\backend
    .\\venv\\Scripts\\activate
    python seed_demo_data.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure backend root directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import func, select, delete
from app.db.database import async_session, init_db, engine
from app.db.models import Base, Incident, RCAResult, RecoveryActionLog, PatternHistory


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────
# Incident Dataset (10 diverse incidents)
# ─────────────────────────────────────────────────────────────

DEMO_INCIDENTS = [
    # ── 1. Default Topology: PostgreSQL Connection Exhaustion ──
    {
        "id": "inc_db_conn_01",
        "title": "PostgreSQL Primary Connection Pool Starvation & Cascading Saturation",
        "description": "HikariCP connection pool on core postgres cluster exhausted due to unindexed table scan queries, generating cascading HTTP 504 gateway timeouts.",
        "topology": "default",
        "status": "resolved",
        "severity": "L3_CRITICAL",
        "fault_type": "connection_timeout",
        "root_cause_service": "database",
        "confidence": 0.96,
        "days_ago": 6.2,
        "duration_hours": 4.5,
        "affected_services": ["database", "order-service", "auth-service", "user-service", "api-gateway"],
        "anomaly_scores": {
            "database": 0.98,
            "order-service": 0.89,
            "auth-service": 0.81,
            "user-service": 0.76,
            "api-gateway": 0.69,
            "payment-service": 0.32,
            "inventory-service": 0.28,
            "search-service": 0.15,
            "notification-service": 0.12,
            "cache-service": 0.09,
        },
        "propagation_chain": "database → order-service → api-gateway",
        "explanation": (
            "Golden Signals analysis detected severe saturation on database connection pool (max_connections=200 exhausted). "
            "Cascading backpressure propagated upstream to order-service and auth-service as thread pools blocked waiting for available sockets. "
            "P99 latency breached the 250ms SLO target, rising to 4,200ms before Envoy circuit breaker tripped at api-gateway to shed non-critical traffic."
        ),
        "metric_deltas": {
            "database": {"active_connections": "+380%", "wait_queue": "+520%", "cpu": "+64%", "query_latency": "+410%"},
            "order-service": {"p99_latency": "+340%", "http_504_errors": "+18.4%", "thread_pool_active": "+95%"},
            "api-gateway": {"p99_latency": "+190%", "http_5xx_rate": "+8.2%"}
        },
        "recommended_actions": [
            "Scale PostgreSQL read replicas and configure PgBouncer connection pooling with max_client_conn=1000.",
            "Add composite index on orders(user_id, status, created_at) to eliminate sequential table scans.",
            "Tune Envoy circuit breaker timeout to 1200ms and max_pending_requests to 50 on order-service egress."
        ],
        "recovery": {
            "action_type": "scale_replica",
            "target": "database",
            "kubectl_command": "kubectl scale statefulset/postgres-replica --replicas=3 -n default",
            "success": True,
            "severity_level": "L3_SYSTEMIC"
        },
        "causal_graph": {
            "nodes": [
                {"id": "database", "anomaly_score": 0.98, "is_root": True},
                {"id": "order-service", "anomaly_score": 0.89, "is_root": False},
                {"id": "auth-service", "anomaly_score": 0.81, "is_root": False},
                {"id": "user-service", "anomaly_score": 0.76, "is_root": False},
                {"id": "api-gateway", "anomaly_score": 0.69, "is_root": False},
            ],
            "edges": [
                {"source": "database", "target": "order-service", "strength": 0.94},
                {"source": "database", "target": "auth-service", "strength": 0.88},
                {"source": "database", "target": "user-service", "strength": 0.82},
                {"source": "order-service", "target": "api-gateway", "strength": 0.91},
                {"source": "auth-service", "target": "api-gateway", "strength": 0.79},
            ]
        }
    },

    # ── 2. Online Boutique: Redis Cart Cache Memory Leak ──
    {
        "id": "inc_redis_leak_02",
        "title": "Redis Cart Stateful Store Memory Leak under Flash Traffic",
        "description": "cartservice state store redis-cart encountered gradual RSS memory leakage caused by unexpired session keys, resulting in Linux cgroup OOMKilled evictions.",
        "topology": "online-boutique",
        "status": "resolved",
        "severity": "L2_CASCADING",
        "fault_type": "memory_leak",
        "root_cause_service": "redis-cart",
        "confidence": 0.94,
        "days_ago": 5.4,
        "duration_hours": 3.2,
        "affected_services": ["redis-cart", "cartservice", "checkoutservice", "frontend"],
        "anomaly_scores": {
            "redis-cart": 0.97,
            "cartservice": 0.88,
            "checkoutservice": 0.74,
            "frontend": 0.68,
            "currencyservice": 0.14,
            "productcatalogservice": 0.11,
            "shippingservice": 0.08,
            "paymentservice": 0.12,
            "recommendationservice": 0.09,
            "emailservice": 0.05,
        },
        "propagation_chain": "redis-cart → cartservice → checkoutservice → frontend",
        "explanation": (
            "Memory saturation alert triggered when redis-cart memory hit 98% cgroup limit. "
            "Key eviction policy was improperly set to 'noeviction', causing OOMKilled loop. "
            "cartservice gRPC connection pool entered CrashLoopBackOff retry storms, elevating checkout failure rate and burning 42% of the 30-day error budget within 45 minutes."
        ),
        "metric_deltas": {
            "redis-cart": {"memory_rss": "+240%", "evicted_keys": "0 (blocked)", "oom_kills": "+4"},
            "cartservice": {"grpc_unavailable_rate": "+24.5%", "p99_latency": "+280%"},
            "checkoutservice": {"failed_checkouts": "+14.2%"}
        },
        "recommended_actions": [
            "Update Redis eviction policy to allkeys-lru with maxmemory 2Gi flag in ConfigMap.",
            "Implement TTL expiration (ex=86400) on cart session keys generated by cartservice.",
            "Configure Kubernetes memory limit requests to 2Gi with HPA memory trigger at 80%."
        ],
        "recovery": {
            "action_type": "restart_pod",
            "target": "redis-cart",
            "kubectl_command": "kubectl rollout restart statefulset/redis-cart -n online-boutique",
            "success": True,
            "severity_level": "L2_CASCADING"
        },
        "causal_graph": {
            "nodes": [
                {"id": "redis-cart", "anomaly_score": 0.97, "is_root": True},
                {"id": "cartservice", "anomaly_score": 0.88, "is_root": False},
                {"id": "checkoutservice", "anomaly_score": 0.74, "is_root": False},
                {"id": "frontend", "anomaly_score": 0.68, "is_root": False},
            ],
            "edges": [
                {"source": "redis-cart", "target": "cartservice", "strength": 0.96},
                {"source": "cartservice", "target": "checkoutservice", "strength": 0.89},
                {"source": "checkoutservice", "target": "frontend", "strength": 0.92},
            ]
        }
    },

    # ── 3. HealthCare: FHIR Records Batch Processing CPU Overload ──
    {
        "id": "inc_fhir_cpu_03",
        "title": "FHIR Health Records Processing CPU Throttling on Batch Sync",
        "description": "records-service experienced 100% CPU CFS throttling during daily batch XML/FHIR patient health records sync, blocking clinical appointment lookups.",
        "topology": "healthcare",
        "status": "resolved",
        "severity": "L2_CASCADING",
        "fault_type": "cpu_overload",
        "root_cause_service": "records-service",
        "confidence": 0.91,
        "days_ago": 4.6,
        "duration_hours": 2.1,
        "affected_services": ["records-service", "appointment-service", "patient-gateway"],
        "anomaly_scores": {
            "records-service": 0.95,
            "appointment-service": 0.82,
            "patient-gateway": 0.67,
            "notification-service": 0.15,
        },
        "propagation_chain": "records-service → appointment-service → patient-gateway",
        "explanation": (
            "Spike in Linux cfs_throttled_periods (>65%) on records-service worker pods caused severe thread starvation while decompressing gzip HL7/FHIR payload bundles. "
            "Downstream appointment-service synchronous validation calls timed out after 3000ms, impairing doctor appointment booking portals across 3 regional health centers."
        ),
        "metric_deltas": {
            "records-service": {"cpu_utilization": "+310%", "throttled_time": "+72%", "p99_latency": "+390%"},
            "appointment-service": {"read_timeout_rate": "+16.8%", "latency": "+220%"},
            "patient-gateway": {"http_502_rate": "+7.4%"}
        },
        "recommended_actions": [
            "Decouple bulk FHIR ingest pipeline to an asynchronous Celery/RabbitMQ worker queue.",
            "Increase Kubernetes CPU quota from 1000m to 4000m with HPA scaling trigger at 70% CPU.",
            "Apply stream-based XML SAX parsing instead of buffering entire DOM documents in memory."
        ],
        "recovery": {
            "action_type": "scale_deployment",
            "target": "records-service",
            "kubectl_command": "kubectl scale deployment/records-service --replicas=5 -n healthcare",
            "success": True,
            "severity_level": "L2_CASCADING"
        },
        "causal_graph": {
            "nodes": [
                {"id": "records-service", "anomaly_score": 0.95, "is_root": True},
                {"id": "appointment-service", "anomaly_score": 0.82, "is_root": False},
                {"id": "patient-gateway", "anomaly_score": 0.67, "is_root": False},
            ],
            "edges": [
                {"source": "records-service", "target": "appointment-service", "strength": 0.93},
                {"source": "appointment-service", "target": "patient-gateway", "strength": 0.87},
            ]
        }
    },

    # ── 4. FinTech: Fraud Detection Real-Time Scoring Latency Spike ──
    {
        "id": "inc_fraud_lat_04",
        "title": "Fraud Detection Inference Engine Latency Spike & Queue Stagnation",
        "description": "fraud-detection scoring pipeline suffered vector index lock contention during blacklist hot-reload, pushing p99 latency from 15ms to 850ms.",
        "topology": "fintech",
        "status": "resolved",
        "severity": "L2_CASCADING",
        "fault_type": "latency_spike",
        "root_cause_service": "fraud-detection",
        "confidence": 0.97,
        "days_ago": 3.8,
        "duration_hours": 1.8,
        "affected_services": ["fraud-detection", "transaction-service", "api-gateway"],
        "anomaly_scores": {
            "fraud-detection": 0.99,
            "transaction-service": 0.86,
            "api-gateway": 0.71,
            "account-service": 0.19,
        },
        "propagation_chain": "fraud-detection → transaction-service → api-gateway",
        "explanation": (
            "Model scoring pipeline degraded when external sanctions blacklist embedding index experienced thread contention during hourly hot-reload. "
            "Transaction authorization requires sub-50ms SLA; delayed fraud responses caused transaction-service to buffer transactions in memory, consuming socket descriptors and degrading API gateway ingress."
        ),
        "metric_deltas": {
            "fraud-detection": {"p99_latency": "+520%", "cpu_utilization": "+88%", "scoring_qps": "-45%"},
            "transaction-service": {"authorization_wait_ms": "+420%", "socket_usage": "+110%"},
            "api-gateway": {"p99_latency": "+230%"}
        },
        "recommended_actions": [
            "Introduce warm dual-buffer swap for vector blacklist model weights without locking read threads.",
            "Configure fallback circuit breaker: skip non-critical fraud heuristics if latency exceeds 60ms.",
            "Provision dedicated GPU/Triton inference pod pool with horizontal scaling."
        ],
        "recovery": {
            "action_type": "restart_pod",
            "target": "fraud-detection",
            "kubectl_command": "kubectl rollout restart deployment/fraud-detection -n fintech",
            "success": True,
            "severity_level": "L2_CASCADING"
        },
        "causal_graph": {
            "nodes": [
                {"id": "fraud-detection", "anomaly_score": 0.99, "is_root": True},
                {"id": "transaction-service", "anomaly_score": 0.86, "is_root": False},
                {"id": "api-gateway", "anomaly_score": 0.71, "is_root": False},
            ],
            "edges": [
                {"source": "fraud-detection", "target": "transaction-service", "strength": 0.97},
                {"source": "transaction-service", "target": "api-gateway", "strength": 0.89},
            ]
        }
    },

    # ── 5. Default Topology: Cache Service Stampede & Memory Leak ──
    {
        "id": "inc_cache_stampede_05",
        "title": "Auth Token Cache Eviction & Thundering Herd Stampede",
        "description": "cache-service key TTL expiration coincided with token refresh spike, generating a thundering herd on PostgreSQL user tables and auth-service socket exhaustion.",
        "topology": "default",
        "status": "mitigated",
        "severity": "L2_CASCADING",
        "fault_type": "memory_leak",
        "root_cause_service": "cache-service",
        "confidence": 0.88,
        "days_ago": 2.9,
        "duration_hours": 3.0,
        "affected_services": ["cache-service", "auth-service", "database", "api-gateway"],
        "anomaly_scores": {
            "cache-service": 0.92,
            "auth-service": 0.85,
            "database": 0.78,
            "api-gateway": 0.65,
            "user-service": 0.25,
            "order-service": 0.22,
            "payment-service": 0.18,
            "search-service": 0.12,
            "inventory-service": 0.10,
            "notification-service": 0.08,
        },
        "propagation_chain": "cache-service → auth-service → api-gateway",
        "explanation": (
            "Cache hit ratio plummeted from 96.4% to 28.1% due to sudden eviction of OAuth2 bearer tokens following an RSS memory saturation spike. "
            "The resulting thundering herd overwhelmed auth-service connection pools. SRE team activated token validation bypass cache with jittered TTL to stabilize authentication latency."
        ),
        "metric_deltas": {
            "cache-service": {"hit_rate": "-68%", "eviction_rate": "+340%", "memory_fragmentation": "+45%"},
            "auth-service": {"token_verification_ms": "+310%", "db_queries_per_sec": "+480%"},
            "api-gateway": {"http_401_rate": "+12.1%"}
        },
        "recommended_actions": [
            "Implement probabilistic early expiration (XFetch algorithm) to prevent cache stampedes.",
            "Add Redis sentinel cluster with 4GB persistent memory allocation.",
            "Enable local in-memory L1 cache with 30s TTL inside auth-service instances."
        ],
        "recovery": {
            "action_type": "scale_deployment",
            "target": "cache-service",
            "kubectl_command": "kubectl scale deployment/cache-service --replicas=3 -n default",
            "success": True,
            "severity_level": "L2_CASCADING"
        },
        "causal_graph": {
            "nodes": [
                {"id": "cache-service", "anomaly_score": 0.92, "is_root": True},
                {"id": "auth-service", "anomaly_score": 0.85, "is_root": False},
                {"id": "database", "anomaly_score": 0.78, "is_root": False},
                {"id": "api-gateway", "anomaly_score": 0.65, "is_root": False},
            ],
            "edges": [
                {"source": "cache-service", "target": "auth-service", "strength": 0.92},
                {"source": "auth-service", "target": "database", "strength": 0.81},
                {"source": "auth-service", "target": "api-gateway", "strength": 0.85},
            ]
        }
    },

    # ── 6. Online Boutique: Payment Service Catastrophic Error Burst ──
    {
        "id": "inc_pay_burst_06",
        "title": "Payment Service 503 Outage Cascading Through Checkout Funnel",
        "description": "Third-party credit card gateway provider dropped connection, triggering unhandled gRPC deadline timeouts across checkoutservice and the web frontend.",
        "topology": "online-boutique",
        "status": "resolved",
        "severity": "L4_CATASTROPHIC",
        "fault_type": "error_burst",
        "root_cause_service": "paymentservice",
        "confidence": 0.98,
        "days_ago": 2.1,
        "duration_hours": 5.0,
        "affected_services": ["paymentservice", "checkoutservice", "frontend", "emailservice", "shippingservice"],
        "anomaly_scores": {
            "paymentservice": 0.99,
            "checkoutservice": 0.93,
            "frontend": 0.89,
            "shippingservice": 0.72,
            "emailservice": 0.68,
            "cartservice": 0.35,
            "currencyservice": 0.22,
            "productcatalogservice": 0.18,
            "recommendationservice": 0.15,
            "redis-cart": 0.10,
        },
        "propagation_chain": "paymentservice → checkoutservice → frontend",
        "explanation": (
            "Catastrophic failure: blast radius exceeded 60% of microservice mesh. "
            "Upstream payment aggregator returned HTTP 503, and paymentservice lacked backoff/circuit-breaker logic. "
            "All checkout worker threads blocked awaiting 30s TCP timeouts, cascading upstream and freezing customer frontend checkout workflows entirely. Error budget depleted by 94%."
        ),
        "metric_deltas": {
            "paymentservice": {"grpc_internal_errors": "+82%", "p99_latency": "+820%", "outbound_timeout_rate": "+64%"},
            "checkoutservice": {"failure_rate": "+78%", "goroutine_leak": "+1400"},
            "frontend": {"order_completion_drop": "-94%"}
        },
        "recommended_actions": [
            "Implement Envoy mesh circuit breaker with max 3 retries and exponential jitter backoff.",
            "Add asynchronous order checkout queue to process payments in background with webhook callback.",
            "Configure automated synthetic payment health check probing to trip circuit breakers before traffic piles up."
        ],
        "recovery": {
            "action_type": "apply_circuit_breaker",
            "target": "paymentservice",
            "kubectl_command": "kubectl apply -f k8s/circuit-breaker-paymentservice.yaml -n online-boutique",
            "success": True,
            "severity_level": "L4_DESIGN_FLAW"
        },
        "causal_graph": {
            "nodes": [
                {"id": "paymentservice", "anomaly_score": 0.99, "is_root": True},
                {"id": "checkoutservice", "anomaly_score": 0.93, "is_root": False},
                {"id": "frontend", "anomaly_score": 0.89, "is_root": False},
                {"id": "shippingservice", "anomaly_score": 0.72, "is_root": False},
                {"id": "emailservice", "anomaly_score": 0.68, "is_root": False},
            ],
            "edges": [
                {"source": "paymentservice", "target": "checkoutservice", "strength": 0.98},
                {"source": "checkoutservice", "target": "frontend", "strength": 0.95},
                {"source": "checkoutservice", "target": "shippingservice", "strength": 0.76},
                {"source": "checkoutservice", "target": "emailservice", "strength": 0.72},
            ]
        }
    },

    # ── 7. FinTech: Transaction Ledger Deadlock & Error Burst ──
    {
        "id": "inc_ledger_deadlock_07",
        "title": "Transaction Ledger Deadlock & Account Mutation Error Burst",
        "description": "transaction-service double-entry accounting worker executed concurrent unbalanced writes, inducing PostgreSQL row-level locks and transaction rollback bursts.",
        "topology": "fintech",
        "status": "mitigated",
        "severity": "L3_CRITICAL",
        "fault_type": "error_burst",
        "root_cause_service": "transaction-service",
        "confidence": 0.93,
        "days_ago": 1.3,
        "duration_hours": 2.4,
        "affected_services": ["transaction-service", "api-gateway", "account-service"],
        "anomaly_scores": {
            "transaction-service": 0.96,
            "api-gateway": 0.84,
            "account-service": 0.77,
            "fraud-detection": 0.24,
        },
        "propagation_chain": "transaction-service → api-gateway",
        "explanation": (
            "High concurrency settlement batch triggered distributed PostgreSQL deadlocks on account_balances rows. "
            "Transaction abort rate spiked to 38.6%, creating systemic backpressure on API Gateway. "
            "Automated remediation paused the background batch runner and drained in-flight idempotent requests."
        ),
        "metric_deltas": {
            "transaction-service": {"deadlock_count": "+42/min", "abort_rate": "+38.6%", "p99_latency": "+290%"},
            "account-service": {"lock_wait_timeout": "+24%"},
            "api-gateway": {"http_500_rate": "+15.2%"}
        },
        "recommended_actions": [
            "Enforce strict alphabetical account ID ordering in balance transfers to eliminate cyclical deadlocks.",
            "Adopt optimistic concurrency control (OCC) with version columns for ledger account balance mutations.",
            "Implement partitioned sharding by customer tenant ID to isolate ledger table locks."
        ],
        "recovery": {
            "action_type": "restart_pod",
            "target": "transaction-service",
            "kubectl_command": "kubectl rollout restart deployment/transaction-service -n fintech",
            "success": True,
            "severity_level": "L3_SYSTEMIC"
        },
        "causal_graph": {
            "nodes": [
                {"id": "transaction-service", "anomaly_score": 0.96, "is_root": True},
                {"id": "api-gateway", "anomaly_score": 0.84, "is_root": False},
                {"id": "account-service", "anomaly_score": 0.77, "is_root": False},
            ],
            "edges": [
                {"source": "transaction-service", "target": "api-gateway", "strength": 0.93},
                {"source": "transaction-service", "target": "account-service", "strength": 0.86},
            ]
        }
    },

    # ── 8. Default Topology: Payment Service Webhook Latency Spike ──
    {
        "id": "inc_pay_lat_08",
        "title": "Payment Service Thread Pool Starvation & Webhook Latency Spike",
        "description": "Payment gateway integration experienced thread pool exhaustion due to slow synchronous banking webhooks, slowing order checkout confirmation.",
        "topology": "default",
        "status": "resolved",
        "severity": "L1_MINOR",
        "fault_type": "latency_spike",
        "root_cause_service": "payment-service",
        "confidence": 0.87,
        "days_ago": 0.8,
        "duration_hours": 1.5,
        "affected_services": ["payment-service", "order-service"],
        "anomaly_scores": {
            "payment-service": 0.89,
            "order-service": 0.62,
            "api-gateway": 0.35,
            "database": 0.28,
            "auth-service": 0.12,
            "inventory-service": 0.14,
            "notification-service": 0.11,
            "user-service": 0.08,
            "cache-service": 0.05,
            "search-service": 0.04,
        },
        "propagation_chain": "payment-service → order-service",
        "explanation": (
            "Isolated single-service fault. Payment gateway webhook acknowledgment latencies rose from 80ms to 950ms. "
            "Order service gracefully queued orders into fallback Kafka topic, keeping blast radius strictly confined to payment-service without affecting user catalog browsing."
        ),
        "metric_deltas": {
            "payment-service": {"active_threads": "+120%", "p99_latency": "+310%"},
            "order-service": {"delayed_orders": "+8.4%"}
        },
        "recommended_actions": [
            "Increase payment worker thread pool size from 40 to 120 in application properties.",
            "Adopt asynchronous non-blocking WebClient (Netty) for outgoing bank webhook calls."
        ],
        "recovery": {
            "action_type": "restart_pod",
            "target": "payment-service",
            "kubectl_command": "kubectl rollout restart deployment/payment-service -n default",
            "success": True,
            "severity_level": "L1_SIMPLE"
        },
        "causal_graph": {
            "nodes": [
                {"id": "payment-service", "anomaly_score": 0.89, "is_root": True},
                {"id": "order-service", "anomaly_score": 0.62, "is_root": False},
            ],
            "edges": [
                {"source": "payment-service", "target": "order-service", "strength": 0.88},
            ]
        }
    },

    # ── 9. HealthCare: Hospital PACS Imaging Connection Timeout ──
    {
        "id": "inc_pacs_timeout_09",
        "title": "Hospital PACS Imaging Integration Connection Timeout",
        "description": "appointment-service radiology scheduling integration hung due to TCP keepalive dropped connections on the legacy DICOM/PACS gateway.",
        "topology": "healthcare",
        "status": "investigating",
        "severity": "L3_CRITICAL",
        "fault_type": "connection_timeout",
        "root_cause_service": "appointment-service",
        "confidence": 0.89,
        "days_ago": 0.2,  # ~4.8 hours ago
        "duration_hours": None,
        "affected_services": ["appointment-service", "patient-gateway", "notification-service"],
        "anomaly_scores": {
            "appointment-service": 0.94,
            "patient-gateway": 0.81,
            "notification-service": 0.64,
            "records-service": 0.38,
        },
        "propagation_chain": "appointment-service → patient-gateway",
        "explanation": (
            "Persistent TCP SYN retransmissions to on-premise PACS storage server exceeding 15,000ms socket timeouts. "
            "Patient gateway reporting 504 Gateway Timeouts for outpatient clinic scheduling. Incident currently under active investigation by SRE on-call rotation."
        ),
        "metric_deltas": {
            "appointment-service": {"tcp_retransmissions": "+450%", "active_requests": "+280%", "error_rate": "+21.4%"},
            "patient-gateway": {"p99_latency": "+460%", "http_504": "+16.8%"}
        },
        "recommended_actions": [
            "Verify network policy and firewall NAT egress rules between Kubernetes cluster and on-premise PACS VLAN.",
            "Deploy Envoy proxy with active health checking and TCP keepalive tuning (keepalive_time=60s)."
        ],
        "recovery": {
            "action_type": "restart_pod",
            "target": "appointment-service",
            "kubectl_command": "kubectl rollout restart deployment/appointment-service -n healthcare",
            "success": False,
            "severity_level": "L3_SYSTEMIC"
        },
        "causal_graph": {
            "nodes": [
                {"id": "appointment-service", "anomaly_score": 0.94, "is_root": True},
                {"id": "patient-gateway", "anomaly_score": 0.81, "is_root": False},
                {"id": "notification-service", "anomaly_score": 0.64, "is_root": False},
            ],
            "edges": [
                {"source": "appointment-service", "target": "patient-gateway", "strength": 0.91},
                {"source": "appointment-service", "target": "notification-service", "strength": 0.77},
            ]
        }
    },

    # ── 10. Online Boutique: Product Catalog Vector Search CPU Overload ──
    {
        "id": "inc_catalog_cpu_10",
        "title": "Product Catalog Vector Embedding Index CPU Overload",
        "description": "productcatalogservice CPU utilization pinned at 100% due to unthrottled similarity search calculations on unindexed catalog embeddings.",
        "topology": "online-boutique",
        "status": "investigating",
        "severity": "L1_MINOR",
        "fault_type": "cpu_overload",
        "root_cause_service": "productcatalogservice",
        "confidence": 0.86,
        "days_ago": 0.08,  # ~2 hours ago
        "duration_hours": None,
        "affected_services": ["productcatalogservice", "recommendationservice", "frontend"],
        "anomaly_scores": {
            "productcatalogservice": 0.91,
            "recommendationservice": 0.72,
            "frontend": 0.58,
            "checkoutservice": 0.22,
            "cartservice": 0.15,
            "currencyservice": 0.08,
            "paymentservice": 0.07,
            "shippingservice": 0.06,
            "redis-cart": 0.05,
            "emailservice": 0.04,
        },
        "propagation_chain": "productcatalogservice → recommendationservice → frontend",
        "explanation": (
            "SRE monitors alerted on productcatalogservice CPU utilization exceeding 92% sustained threshold for 10 minutes. "
            "Exact nearest-neighbor cosine similarity queries running on main application threads without HNSW index caching. On-call engineer currently profiling Go pprof goroutine flamegraphs."
        ),
        "metric_deltas": {
            "productcatalogservice": {"cpu_utilization": "+280%", "p99_latency": "+210%"},
            "recommendationservice": {"fallback_responses": "+35%"}
        },
        "recommended_actions": [
            "Build pre-computed HNSW vector index using FAISS or Qdrant for semantic product searches.",
            "Scale productcatalogservice deployment replicas from 2 to 6 to absorb peak traffic."
        ],
        "recovery": {
            "action_type": "scale_deployment",
            "target": "productcatalogservice",
            "kubectl_command": "kubectl scale deployment/productcatalogservice --replicas=6 -n online-boutique",
            "success": False,
            "severity_level": "L1_SIMPLE"
        },
        "causal_graph": {
            "nodes": [
                {"id": "productcatalogservice", "anomaly_score": 0.91, "is_root": True},
                {"id": "recommendationservice", "anomaly_score": 0.72, "is_root": False},
                {"id": "frontend", "anomaly_score": 0.58, "is_root": False},
            ],
            "edges": [
                {"source": "productcatalogservice", "target": "recommendationservice", "strength": 0.89},
                {"source": "recommendationservice", "target": "frontend", "strength": 0.82},
            ]
        }
    },
]


async def seed_data() -> None:
    """Seed the database with rich demo incidents, RCA reports, and recovery logs."""
    print("Initializing database tables...")
    await init_db()

    now = utc_now()

    async with async_session() as db:
        print("Cleaning up old demo seed data...")
        # Delete existing incidents matching our demo IDs or seed prefix
        demo_ids = [item["id"] for item in DEMO_INCIDENTS]
        await db.execute(delete(Incident).where(Incident.id.in_(demo_ids)))
        await db.execute(delete(RCAResult).where(RCAResult.incident_id.in_(demo_ids)))
        await db.execute(delete(RecoveryActionLog).where(RecoveryActionLog.incident_id.in_(demo_ids)))
        await db.commit()

        print(f"Seeding {len(DEMO_INCIDENTS)} realistic incidents across 4 topologies...")

        for data in DEMO_INCIDENTS:
            detected_at = now - timedelta(days=data["days_ago"])
            resolved_at = (
                detected_at + timedelta(hours=data["duration_hours"])
                if data["duration_hours"] is not None
                else None
            )

            # Build timeline
            timeline = [
                {
                    "time": detected_at.isoformat(),
                    "event": f"Anomaly detected in {data['root_cause_service']} ({data['fault_type']})",
                    "score": round(data["anomaly_scores"][data["root_cause_service"]], 2),
                },
                {
                    "time": (detected_at + timedelta(minutes=1)).isoformat(),
                    "event": f"GNN VAE-Autoencoder flagged {len(data['affected_services'])} anomalous nodes in topology graph",
                    "score": 0.84,
                },
                {
                    "time": (detected_at + timedelta(minutes=2)).isoformat(),
                    "event": f"DECI Causal Discovery identified root cause: {data['root_cause_service']}",
                    "score": round(data["confidence"], 2),
                },
                {
                    "time": (detected_at + timedelta(minutes=3)).isoformat(),
                    "event": f"Severity classified as {data['severity']}",
                    "score": 1.0,
                },
            ]

            if resolved_at:
                timeline.append({
                    "time": resolved_at.isoformat(),
                    "event": f"Remediation verified: {data['recovery']['action_type']} executed on {data['root_cause_service']}",
                    "score": 0.05,
                })

            incident = Incident(
                id=data["id"],
                title=data["title"],
                description=data["description"],
                status=data["status"],
                severity=data["severity"],
                root_cause_service=data["root_cause_service"],
                confidence=data["confidence"],
                fault_type=data["fault_type"],
                affected_services=data["affected_services"],
                anomaly_scores=data["anomaly_scores"],
                timeline=timeline,
                window_start=detected_at - timedelta(minutes=15),
                window_end=resolved_at or (detected_at + timedelta(minutes=45)),
                detected_at=detected_at,
                resolved_at=resolved_at,
            )
            db.add(incident)

            # Model info dictionary
            model_info = {
                "gnn_type": "VAE-GNN Autoencoder",
                "maml_adapted": True,
                "adaptation_steps": 3,
                "causal_method": "DECI (Differentiable Causal Discovery)",
                "h_score": round(0.001 + (1.0 - data["confidence"]) * 0.01, 5),
                "drift_score": round(0.02 + (1.0 - data["confidence"]) * 0.05, 4),
                "execution_time_ms": round(120.0 + (data["confidence"] * 35.0), 1),
                "severity_level": data["severity"],
                "recovery_action": data["recovery"]["action_type"],
                "recovery_success": data["recovery"]["success"],
                "topology": data["topology"],
                "severity": {
                    "level": data["severity"].split("_")[0],  # L1, L2, L3, L4
                    "reason": data["explanation"][:120] + "...",
                    "response_strategy": "root_first" if "L2" in data["severity"] else ("auto_fix" if "L1" in data["severity"] else "escalate"),
                    "is_recurring": data["severity"] == "L4_CATASTROPHIC",
                    "recurring_count": 4 if data["severity"] == "L4_CATASTROPHIC" else 1,
                },
                "recovery": {
                    "action": data["recovery"]["action_type"],
                    "action_type": data["recovery"]["action_type"],
                    "target": data["recovery"]["target"],
                    "kubectl_command": data["recovery"]["kubectl_command"],
                    "success": data["recovery"]["success"],
                    "simulated": True,
                }
            }

            rca_result = RCAResult(
                incident_id=data["id"],
                root_cause_service=data["root_cause_service"],
                confidence=data["confidence"],
                fault_type=data["fault_type"],
                explanation=data["explanation"],
                propagation_chain=data["propagation_chain"],
                metric_deltas=data["metric_deltas"],
                recommended_actions=data["recommended_actions"],
                causal_graph=data["causal_graph"],
                model_info=model_info,
                created_at=detected_at + timedelta(minutes=3),
            )
            db.add(rca_result)

            # Recovery action log
            recovery_log = RecoveryActionLog(
                incident_id=data["id"],
                action_type=data["recovery"]["action_type"],
                target_service=data["recovery"]["target"],
                kubectl_command=data["recovery"]["kubectl_command"],
                confidence=data["confidence"],
                success=1 if data["recovery"]["success"] else 0,
                simulated=1,
                severity_level=data["recovery"]["severity_level"],
                execution_time_ms=round(85.0 + data["confidence"] * 40.0, 1),
                created_at=detected_at + timedelta(minutes=4),
            )
            db.add(recovery_log)

        # Seed pattern history for recurring analysis
        patterns = [
            PatternHistory(
                root_cause_service="paymentservice",
                occurrence_count=4,
                common_fault_type="error_burst",
                severity_trend="escalating",
                recommendation="Deploy asynchronous checkout queuing and robust third-party circuit breaking.",
                priority="critical",
                first_seen=now - timedelta(days=25),
                last_seen=now - timedelta(days=2),
            ),
            PatternHistory(
                root_cause_service="database",
                occurrence_count=3,
                common_fault_type="connection_timeout",
                severity_trend="stable",
                recommendation="Introduce PgBouncer connection multiplexing and read-replica offloading.",
                priority="high",
                first_seen=now - timedelta(days=20),
                last_seen=now - timedelta(days=6),
            ),
            PatternHistory(
                root_cause_service="redis-cart",
                occurrence_count=2,
                common_fault_type="memory_leak",
                severity_trend="improving",
                recommendation="Enforce strict allkeys-lru memory policy and verify key TTL expiration.",
                priority="medium",
                first_seen=now - timedelta(days=14),
                last_seen=now - timedelta(days=5),
            ),
        ]
        db.add_all(patterns)

        await db.commit()
        print("Data committed successfully!")

    # Verify count
    async with async_session() as db:
        res = await db.execute(select(func.count(Incident.id)))
        total_incidents = res.scalar() or 0

        rca_res = await db.execute(select(func.count(RCAResult.id)))
        total_rca = rca_res.scalar() or 0

        rec_res = await db.execute(select(func.count(RecoveryActionLog.id)))
        total_rec = rec_res.scalar() or 0

        print("\n" + "=" * 80)
        print("  DATABASE VERIFICATION REPORT")
        print("=" * 80)
        print(f"Total Incidents:         {total_incidents}")
        print(f"Total RCA Results:       {total_rca}")
        print(f"Total Recovery Logs:     {total_rec}")
        print("-" * 80)

        # Print seeded incidents overview
        rows = await db.execute(select(Incident).order_by(Incident.detected_at.desc()))
        all_incidents = rows.scalars().all()

        header = f"{'ID':<22} | {'Topology':<16} | {'Fault':<18} | {'Root Cause':<20} | {'Sev':<15} | {'Conf':<6} | {'Status'}"
        print(header)
        print("-" * len(header))

        for inc in all_incidents:
            # find topology from model_info or lookup
            topo = "unknown"
            for d in DEMO_INCIDENTS:
                if d["id"] == inc.id:
                    topo = d["topology"]
                    break

            conf_str = f"{(inc.confidence * 100):.0f}%" if inc.confidence else "N/A"
            print(
                f"{inc.id:<22} | {topo:<16} | {(inc.fault_type or ''):<18} | "
                f"{(inc.root_cause_service or ''):<20} | {(inc.severity or ''):<15} | "
                f"{conf_str:<6} | {inc.status}"
            )
        print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(seed_data())
