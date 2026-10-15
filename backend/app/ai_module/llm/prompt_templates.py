"""
SYNAPSE LLM Prompt Templates — SRE Assistant Prompting.

Defines the system prompt, user prompt template, and few-shot examples
for generating human-readable RCA explanations from GNN + causal output.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) assistant working for an AIOps platform called SYNAPSE. Your role is to analyze microservice incidents and produce clear, actionable Root Cause Analysis (RCA) reports.

You will be given structured data containing:
1. **Anomaly scores** — per-service anomaly scores from a Graph Neural Network (higher = more anomalous)
2. **Causal graph** — directed edges showing cause-effect relationships between services
3. **Root cause candidates** — services identified as likely root causes (no incoming causal edges)
4. **Metric deltas** — percentage changes in key metrics (latency, error_rate, cpu, memory) vs baseline

Your task is to:
1. Identify the most likely root cause service and explain WHY
2. Describe the failure propagation chain
3. Assess confidence based on the strength of evidence
4. Provide specific, actionable remediation steps

IMPORTANT: Always respond with valid JSON matching the required output format. Do not include any text outside the JSON object."""


# ──────────────────────────────────────────────
# User Prompt Template
# ──────────────────────────────────────────────

USER_PROMPT_TEMPLATE = """Analyze the following microservice incident and provide a Root Cause Analysis:

## Incident Data

**Anomaly Scores** (0.0 = normal, 1.0 = highly anomalous):
{anomaly_scores}

**Causal Graph** (directed edges: source caused target's anomaly):
{causal_edges}

**Root Cause Candidates** (services with no incoming causal edges):
{root_candidates}

**Metric Deltas** (percentage change from baseline):
{metric_deltas}

**Service Dependency Topology**:
{dependency_info}

## Required Output Format

Respond with a JSON object containing:
{{
    "root_cause": "service-name",
    "confidence": 0.0-1.0,
    "fault_type": "latency_spike|error_burst|resource_exhaustion|unknown",
    "explanation": "2-3 sentence explanation of what happened and why",
    "propagation_chain": "service-a → service-b → service-c",
    "affected_services": ["list", "of", "affected", "services"],
    "recommended_actions": [
        "Specific action 1",
        "Specific action 2",
        "Specific action 3"
    ]
}}"""


# ──────────────────────────────────────────────
# Few-Shot Examples
# ──────────────────────────────────────────────

FEW_SHOT_EXAMPLES = [
    {
        "input": {
            "anomaly_scores": {"database": 0.95, "auth-service": 0.78, "api-gateway": 0.62},
            "causal_edges": [("database", "auth-service", 0.89), ("auth-service", "api-gateway", 0.72)],
            "root_candidates": [("database", 0.95)],
            "metric_deltas": {
                "database": {"latency": "+340%", "cpu": "+85%"},
                "auth-service": {"latency": "+180%", "error_rate": "+150%"},
            },
        },
        "output": {
            "root_cause": "database",
            "confidence": 0.92,
            "fault_type": "latency_spike",
            "explanation": "The database service experienced a severe latency spike (+340%) with high CPU utilization (+85%), indicating either a slow query, lock contention, or resource exhaustion. This caused auth-service (direct dependent) to see cascading latency (+180%) and elevated error rates (+150%), which further propagated to api-gateway.",
            "propagation_chain": "database → auth-service → api-gateway",
            "affected_services": ["auth-service", "api-gateway"],
            "recommended_actions": [
                "Check database slow query logs for long-running queries",
                "Verify database connection pool utilization and increase if near capacity",
                "Review recent database schema changes or index modifications",
                "Scale database compute resources if CPU is consistently high",
            ],
        },
    }
]


# ──────────────────────────────────────────────
# Prompt Builder
# ──────────────────────────────────────────────

def build_rca_prompt(
    anomaly_scores: Dict[str, float],
    causal_edges: List[Tuple[str, str, float]],
    root_candidates: List[Tuple[str, float]],
    metric_deltas: Dict[str, Dict[str, str]],
    dependency_edges: Optional[List[Tuple[str, str]]] = None,
) -> str:
    """Build the complete user prompt for RCA analysis.

    Args:
        anomaly_scores: {service: score}
        causal_edges: [(source, target, strength), ...]
        root_candidates: [(service, score), ...]
        metric_deltas: {service: {metric: "delta%"}}
        dependency_edges: [(src, tgt), ...] from the service topology

    Returns:
        Formatted user prompt string.
    """
    # Format anomaly scores
    scores_str = "\n".join(
        f"  - {svc}: {score:.3f}" for svc, score in
        sorted(anomaly_scores.items(), key=lambda x: x[1], reverse=True)
    )

    # Format causal edges
    if causal_edges:
        edges_str = "\n".join(
            f"  - {src} → {tgt} (strength: {s:.3f})"
            for src, tgt, s in causal_edges
        )
    else:
        edges_str = "  No causal edges discovered."

    # Format root candidates
    roots_str = "\n".join(
        f"  - {svc} (anomaly score: {score:.3f})"
        for svc, score in root_candidates
    )

    # Format metric deltas
    if metric_deltas:
        deltas_parts = []
        for svc, deltas in metric_deltas.items():
            delta_items = ", ".join(f"{k}: {v}" for k, v in deltas.items())
            deltas_parts.append(f"  - {svc}: {delta_items}")
        deltas_str = "\n".join(deltas_parts)
    else:
        deltas_str = "  No significant metric changes detected."

    # Format dependency info
    if dependency_edges:
        dep_str = "\n".join(
            f"  - {src} → {tgt}" for src, tgt in dependency_edges
        )
    else:
        dep_str = "  Topology information not available."

    return USER_PROMPT_TEMPLATE.format(
        anomaly_scores=scores_str,
        causal_edges=edges_str,
        root_candidates=roots_str,
        metric_deltas=deltas_str,
        dependency_info=dep_str,
    )


def build_mock_response(
    root_candidates: List[Tuple[str, float]],
    anomaly_scores: Dict[str, float],
    causal_edges: List[Tuple[str, str, float]],
    metric_deltas: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:
    """Generate a deterministic mock LLM response (for development).

    Uses heuristics to produce a reasonable RCA without calling an LLM.
    """
    if not root_candidates:
        # Fallback: use highest anomaly score
        if anomaly_scores:
            sorted_scores = sorted(anomaly_scores.items(), key=lambda x: x[1], reverse=True)
            root_candidates = [sorted_scores[0]]
        else:
            return {
                "root_cause": "unknown",
                "confidence": 0.0,
                "fault_type": "unknown",
                "explanation": "Insufficient data to determine root cause.",
                "propagation_chain": "",
                "affected_services": [],
                "recommended_actions": ["Collect more monitoring data"],
            }

    root_svc = root_candidates[0][0]
    root_score = root_candidates[0][1]

    # Determine fault type from metric deltas
    root_deltas = metric_deltas.get(root_svc, {})
    fault_type = _infer_fault_type(root_deltas)

    # Build propagation chain from causal edges
    chain = _build_chain(root_svc, causal_edges)
    chain_str = " → ".join(chain) if chain else root_svc

    # Affected services (everything except root)
    affected = [svc for svc, score in anomaly_scores.items()
                if svc != root_svc and score > 0.4]

    # Generate explanation
    explanation = _generate_explanation(root_svc, fault_type, root_deltas, affected)

    # Generate recommendations
    actions = _generate_recommendations(root_svc, fault_type)

    return {
        "root_cause": root_svc,
        "confidence": float(round(min(root_score * 1.1, 0.99), 2)),
        "fault_type": fault_type,
        "explanation": explanation,
        "propagation_chain": chain_str,
        "affected_services": affected,
        "recommended_actions": actions,
    }


def _infer_fault_type(deltas: Dict[str, str]) -> str:
    """Infer fault type from metric deltas."""
    if not deltas:
        return "unknown"

    lat = _parse_delta(deltas.get("latency", "0%"))
    err = _parse_delta(deltas.get("error_rate", "0%"))
    cpu = _parse_delta(deltas.get("cpu", "0%"))
    mem = _parse_delta(deltas.get("memory", "0%"))

    if cpu > 50 or mem > 50:
        return "resource_exhaustion"
    if err > lat:
        return "error_burst"
    return "latency_spike"


def _parse_delta(s: str) -> float:
    """Parse a delta string like '+340%' to a float."""
    try:
        return abs(float(s.replace("%", "").replace("+", "")))
    except (ValueError, AttributeError):
        return 0.0


def _build_chain(root: str, edges: List[Tuple[str, str, float]]) -> List[str]:
    """Build propagation chain via BFS from root along causal edges."""
    adj = {}
    for src, tgt, _ in edges:
        adj.setdefault(src, []).append(tgt)

    chain = [root]
    visited = {root}
    queue = [root]
    while queue:
        node = queue.pop(0)
        for tgt in adj.get(node, []):
            if tgt not in visited:
                visited.add(tgt)
                chain.append(tgt)
                queue.append(tgt)
    return chain


def _generate_explanation(
    root: str, fault_type: str, deltas: Dict[str, str], affected: List[str]
) -> str:
    """Generate a rich, human-readable SRE incident analysis explanation."""
    lat_delta = deltas.get("latency")
    err_delta = deltas.get("error_rate")
    cpu_delta = deltas.get("cpu")
    mem_delta = deltas.get("memory")
    req_delta = deltas.get("request_rate")

    # Format specific metrics
    metric_fragments = []
    if lat_delta:
        metric_fragments.append(f"latency escalated by {lat_delta}")
    if err_delta:
        metric_fragments.append(f"error rates surged by {err_delta}")
    if cpu_delta:
        metric_fragments.append(f"CPU utilization spiked by {cpu_delta}")
    if mem_delta:
        metric_fragments.append(f"memory footprint expanded by {mem_delta}")
    if req_delta:
        metric_fragments.append(f"throughput shifted by {req_delta}")

    delta_str = ", ".join(metric_fragments) if metric_fragments else "severe metric anomalies detected"

    # Deterministic rotation for varied sentence structures
    h = sum(ord(c) for c in root) % 3

    if fault_type == "latency_spike":
        if h == 0:
            s1 = f"Automated telemetry analysis identified an acute latency regression in '{root}', where response times surged ({delta_str})."
        elif h == 1:
            s1 = f"Real-time anomaly scoring localized primary system degradation to '{root}', driven by a critical latency inflation ({delta_str})."
        else:
            s1 = f"Diagnostic telemetry detected substantial response queue delays in '{root}', registering severe latency inflation ({delta_str})."

        if "database" in root or "db" in root:
            s2 = "Unindexed query execution and uncommitted lock contention exhausted the active connection pool, starving caller threads and inducing severe pipeline stalls."
        elif "cache" in root or "redis" in root:
            s2 = "Cache key eviction cascades and concurrent cache misses triggered thundering herd lookups to persistent storage, resulting in worker thread starvation."
        elif "payment" in root:
            s2 = "Outbound payment gateway socket timeouts and synchronous TLS handshakes blocked worker goroutines, triggering connection pool exhaustion."
        elif "auth" in root:
            s2 = "Cryptographic token verification backlogs and session state lock contention caused inbound authentication requests to queue up indefinitely."
        elif "order" in root or "checkout" in root:
            s2 = "Downstream inventory and transaction coordinator deadlocks caused worker threads to block on pending locks, backing up incoming client requests."
        else:
            s2 = "Thread pool saturation and blocking I/O operations created heavy queuing delays, preventing worker threads from acknowledging incoming requests."

    elif fault_type == "error_burst":
        if h == 0:
            s1 = f"Incident detection models isolated an aggressive error cascade originating at '{root}', where failure rates spiked abruptly ({delta_str})."
        elif h == 1:
            s1 = f"High-frequency telemetry flagged '{root}' under acute failure conditions, characterized by an unprecedented error burst ({delta_str})."
        else:
            s1 = f"Cluster health monitors registered severe reliability degradation in '{root}', caused by widespread operational failures ({delta_str})."

        if "auth" in root:
            s2 = "JWT validation failures and keystore synchronization errors caused authentication handlers to reject client tokens, triggering rapid circuit trips."
        elif "payment" in root:
            s2 = "Third-party payment processor network timeouts and settlement handshake drops forced the service to return immediate HTTP 500 error envelopes."
        elif "order" in root or "cart" in root:
            s2 = "State serialization errors and concurrent distributed transaction rollbacks caused active operations to abort, generating cascading RPC exceptions."
        else:
            s2 = "Uncaught runtime exceptions and breached retry budgets rapidly tripped circuit breakers, causing the service to shed load and reject incoming traffic."

    elif fault_type == "resource_exhaustion":
        if h == 0:
            s1 = f"Node telemetry detected critical hardware boundary saturation on '{root}', with resource consumption breaching safe thresholds ({delta_str})."
        elif h == 1:
            s1 = f"Workload profiling revealed severe computational exhaustion within '{root}', showing intensive resource starvation ({delta_str})."
        else:
            s1 = f"Capacity alerts triggered on '{root}' due to severe resource contention and limit clamping ({delta_str})."

        if "memory" in delta_str or "mem" in delta_str:
            s2 = "Heap fragmentation and unchecked object retention triggered aggressive JVM/GC stop-the-world pauses, pushing the container dangerously close to OOM-killer termination."
        else:
            s2 = "Runaway execution loops and cgroups CPU quota throttling severely constrained available processing cycles, resulting in stalled request execution cycles."

    else:
        s1 = f"Causal graph topology algorithms isolated anomalous state drift centered at '{root}' ({delta_str})."
        s2 = "Inter-service RPC queue buildup and dependency backpressure caused the service to operate outside its baseline performance envelope."

    if affected:
        aff_count = len(affected)
        aff_preview = ", ".join(affected[:3])
        if aff_count == 1:
            s3 = f"This failure propagated downstream along causal dependency edges, directly destabilizing '{aff_preview}'."
        else:
            s3 = f"The failure propagated downstream across {aff_count} dependent microservices ({aff_preview}), exhausting client-side retry budgets and tripping upstream circuit breakers."
    else:
        s3 = f"While currently isolated to '{root}', backpressure threatens edge ingress routing and upstream gateway stability."

    if fault_type in ("latency_spike", "resource_exhaustion"):
        s4 = "The incident breached p99 latency SLO agreements, resulting in an estimated 15-25% drop in end-to-end request throughput during the incident window."
    elif fault_type == "error_burst":
        s4 = "Elevated 5xx response rates depleted the error budget for the current rolling window, with direct revenue impact observed across active user checkout journeys."
    else:
        s4 = "Overall system availability fell below target reliability objectives during the anomalous interval, requiring prioritized remediation."

    return f"{s1} {s2} {s3} {s4}"


def _generate_recommendations(root: str, fault_type: str) -> List[str]:
    """Generate 5+ specific, actionable SRE recommendations with kubectl commands and monitoring improvements."""
    if fault_type == "latency_spike":
        return [
            f"Restart deployment to flush saturated thread pools and clear thread contention: `kubectl rollout restart deployment/{root} -n default`",
            f"Scale deployment horizontally to distribute synchronous request concurrency: `kubectl scale deployment/{root} --replicas=5 -n default`",
            f"Extract real-time slow query and connection timeout traces: `kubectl logs -l app={root} --tail=500 -n default | grep -iE 'slow query|lock wait|pool exhausted|timeout'`",
            f"Audit and increase client-side RPC deadlines and thread pool connection limits for callers of {root}",
            f"Implement Istio VirtualService timeout policy: enforce 2.5s maximum request timeout with 2 retries on {root}",
            f"Configure Prometheus alert for p99 latency degradation: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service=\"{root}\"}}[2m])) > 0.8`",
        ]
    elif fault_type == "error_burst":
        return [
            f"Restart crashing or anomalous pod instances to reset execution state: `kubectl rollout restart deployment/{root} -n default`",
            f"Inspect stack traces and HTTP 5xx error distribution: `kubectl logs -l app={root} --tail=400 -n default --timestamps | grep -iE 'exception|panic|fatal|50[0-4]'`",
            f"Verify network connectivity and Kubernetes service endpoints: `kubectl get endpoints {root} -n default && kubectl get networkpolicy -n default`",
            f"Apply Istio circuit breaker DestinationRule with consecutive5xxErrors: 3 and baseEjectionTime: 30s for {root}",
            f"Verify environment secret configuration and credentials: `kubectl describe deployment/{root} -n default`",
            f"Create Prometheus alert for 5xx breach: `rate(http_requests_total{{service=\"{root}\",status=~\"5..\"}}[2m]) / rate(http_requests_total[2m]) > 0.02`",
        ]
    elif fault_type == "resource_exhaustion":
        return [
            f"Profile real-time container CPU and memory consumption: `kubectl top pods -l app={root} -n default --containers`",
            f"Scale pod replicas to distribute compute pressure across cluster nodes: `kubectl scale deployment/{root} --replicas=4 -n default`",
            f"Inspect OOM-kill terminations and kernel eviction logs: `kubectl describe pods -l app={root} -n default | grep -iE 'oomkilled|terminated|evicted'`",
            f"Raise container cgroup CPU limits and JVM/heap limits in `kubectl edit deployment/{root} -n default`",
            f"Capture memory heap dump or thread trace from running pod: `kubectl exec -it deploy/{root} -n default -- jcmd 1 GC.heap_dump /tmp/heap.hprof`",
            f"Configure Prometheus alert for near-OOM saturation: `container_memory_working_set_bytes{{container=\"{root}\"}} / container_spec_memory_limit_bytes > 0.85`",
        ]
    else:
        return [
            f"Trigger rolling deployment restart to restore nominal state: `kubectl rollout restart deployment/{root} -n default`",
            f"Extract recent pod lifecycle events and terminations: `kubectl describe pods -l app={root} -n default`",
            f"Collect anomalous application error logs: `kubectl logs -l app={root} --tail=500 -n default --since=30m`",
            f"Verify host node health and capacity: `kubectl top nodes && kubectl describe nodes`",
            f"Enforce readiness and liveness probes in deployment manifest to enable automatic pod healing",
            f"Establish baseline Prometheus anomaly alert for {root} error and latency deviations exceeding 3 standard deviations",
        ]
