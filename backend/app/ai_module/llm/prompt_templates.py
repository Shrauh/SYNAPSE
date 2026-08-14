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
    """Generate a human-readable explanation."""
    fault_desc = {
        "latency_spike": "a significant latency spike",
        "error_burst": "a burst of errors",
        "resource_exhaustion": "resource exhaustion (high CPU/memory)",
        "unknown": "anomalous behavior",
    }

    delta_summary = ", ".join(f"{k}: {v}" for k, v in deltas.items()) if deltas else "elevated metrics"
    affected_str = ", ".join(affected[:3]) if affected else "no other services"

    return (
        f"The {root} service experienced {fault_desc.get(fault_type, 'an anomaly')} "
        f"({delta_summary}). This caused cascading failures affecting {affected_str}. "
        f"The causal analysis indicates {root} as the originating point of the incident."
    )


def _generate_recommendations(root: str, fault_type: str) -> List[str]:
    """Generate actionable recommendations based on fault type."""
    base = [f"Investigate {root} service logs for the incident timeframe"]

    if fault_type == "latency_spike":
        base.extend([
            f"Check {root} for slow queries, lock contention, or connection pool exhaustion",
            f"Review recent deployments to {root} for performance regressions",
            f"Consider scaling {root} horizontally if under heavy load",
        ])
    elif fault_type == "error_burst":
        base.extend([
            f"Check {root} error logs for exception patterns and stack traces",
            f"Verify upstream dependencies of {root} are healthy",
            f"Check for configuration changes or expired credentials in {root}",
        ])
    elif fault_type == "resource_exhaustion":
        base.extend([
            f"Check {root} CPU and memory usage trends over the past hour",
            f"Look for memory leaks or runaway processes in {root}",
            f"Scale {root} resources or restart pods if resource limits are hit",
        ])
    else:
        base.extend([
            f"Run diagnostics on {root} and its dependencies",
            "Review recent changes across the affected service chain",
        ])

    return base
