"""
SYNAPSE Log Analyzer — fetches and analyzes service logs for RCA.

Connects to:
  - Loki (http://localhost:3100) — if available
  - kubectl logs — fallback for K8s
  - Push endpoint — services can push their own logs

Extracts:
  - Error patterns (exceptions, stack traces)
  - Warning frequency
  - Last N error messages per service
  - Error correlation across services
"""
from __future__ import annotations
import logging
import subprocess
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger("synapse.logs")

LOKI_URL = "http://localhost:3100"

# Common error patterns to look for in logs
ERROR_PATTERNS = [
    (re.compile(r'(?i)(exception|error|fatal|critical|panic)', re.IGNORECASE), "error"),
    (re.compile(r'(?i)connection (refused|reset|timeout)', re.IGNORECASE), "connection_error"),
    (re.compile(r'(?i)(out of memory|oom|heap)', re.IGNORECASE), "memory_error"),
    (re.compile(r'(?i)timeout', re.IGNORECASE), "timeout"),
    (re.compile(r'(?i)(5[0-9]{2}|internal server error)', re.IGNORECASE), "http_error"),
    (re.compile(r'(?i)(null|undefined|nilpointer|nil pointer)', re.IGNORECASE), "null_error"),
    (re.compile(r'(?i)(deadlock|lock wait timeout)', re.IGNORECASE), "deadlock"),
]


def _classify_error(line: str) -> Optional[str]:
    """Classify a log line into an error type."""
    for pattern, error_type in ERROR_PATTERNS:
        if pattern.search(line):
            return error_type
    return None


def _extract_error_lines(log_text: str, max_lines: int = 20) -> List[Dict[str, str]]:
    """Extract error lines from raw log text."""
    errors = []
    for line in log_text.splitlines():
        error_type = _classify_error(line)
        if error_type:
            errors.append({
                "line": line.strip()[:200],  # cap length
                "type": error_type,
            })
    return errors[-max_lines:]  # most recent errors


async def fetch_loki_logs(
    service: str,
    minutes_back: int = 10,
    limit: int = 100,
) -> Optional[str]:
    """
    Fetch logs from Loki for a specific service.
    Tries multiple label selectors.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes_back)
    start_ns = int(start.timestamp() * 1e9)
    end_ns = int(end.timestamp() * 1e9)

    # Try different label selectors
    queries = [
        f'{{service="{service}"}}',
        f'{{app="{service}"}}',
        f'{{job="{service}"}}',
        f'{{container="{service}"}}',
    ]

    async with httpx.AsyncClient(timeout=5.0) as client:
        for query in queries:
            try:
                resp = await client.get(
                    f"{LOKI_URL}/loki/api/v1/query_range",
                    params={
                        "query": query,
                        "start": start_ns,
                        "end": end_ns,
                        "limit": limit,
                        "direction": "backward",
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    streams = data.get("data", {}).get("result", [])
                    if streams:
                        all_lines = []
                        for stream in streams:
                            for ts, line in stream.get("values", []):
                                all_lines.append(line)
                        return "\n".join(all_lines)
            except Exception as e:
                logger.debug(f"Loki query failed for {query}: {e}")

    return None


def fetch_kubectl_logs(
    service: str,
    namespace: str = "default",
    lines: int = 100,
) -> Optional[str]:
    """Fetch logs from Kubernetes pod via kubectl."""
    try:
        # Get pod name for deployment
        pod_result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace,
             "-l", f"app={service}",
             "--field-selector=status.phase=Running",
             "-o", "jsonpath={.items[0].metadata.name}"],
            capture_output=True, text=True, timeout=8
        )
        pod_name = pod_result.stdout.strip()
        if not pod_name:
            # try with name= label
            pod_result = subprocess.run(
                ["kubectl", "get", "pods", "-n", namespace,
                 "-l", f"name={service}",
                 "-o", "jsonpath={.items[0].metadata.name}"],
                capture_output=True, text=True, timeout=8
            )
            pod_name = pod_result.stdout.strip()

        if not pod_name:
            return None

        log_result = subprocess.run(
            ["kubectl", "logs", pod_name, "-n", namespace,
             f"--tail={lines}", "--timestamps=true"],
            capture_output=True, text=True, timeout=15
        )
        return log_result.stdout if log_result.returncode == 0 else None
    except Exception as e:
        logger.debug(f"kubectl logs failed for {service}: {e}")
        return None


# In-memory push log store
_pushed_logs: Dict[str, List[str]] = {}  # service -> [log lines]


def receive_pushed_logs(service: str, lines: List[str]) -> None:
    """Receive logs pushed by a service via the push endpoint."""
    if service not in _pushed_logs:
        _pushed_logs[service] = []
    _pushed_logs[service].extend(lines)
    # Keep last 500 lines
    _pushed_logs[service] = _pushed_logs[service][-500:]


async def analyze_service_logs(
    service: str,
    namespace: str = "default",
    minutes_back: int = 10,
) -> Dict[str, Any]:
    """
    Fetch and analyze logs for a service. Tries Loki → kubectl → pushed logs.
    Returns structured error summary for the LLM.
    """
    log_text = None
    source = None

    # Try Loki first (richest data)
    loki_logs = await fetch_loki_logs(service, minutes_back)
    if loki_logs:
        log_text = loki_logs
        source = "loki"
    else:
        # Try kubectl
        kubectl_logs = fetch_kubectl_logs(service, namespace)
        if kubectl_logs:
            log_text = kubectl_logs
            source = "kubectl"
        # Try pushed logs
        elif service in _pushed_logs:
            log_text = "\n".join(_pushed_logs[service])
            source = "push"

    if not log_text:
        return {
            "service": service,
            "available": False,
            "source": None,
            "error_count": 0,
            "errors": [],
            "summary": "No logs available",
        }

    error_lines = _extract_error_lines(log_text)
    error_types = [e["type"] for e in error_lines]

    # Count by type
    type_counts: Dict[str, int] = {}
    for t in error_types:
        type_counts[t] = type_counts.get(t, 0) + 1

    dominant_error = max(type_counts, key=type_counts.get) if type_counts else None

    summary = f"{len(error_lines)} errors found. "
    if dominant_error:
        summary += f"Most common: {dominant_error} ({type_counts[dominant_error]}x). "
    if error_lines:
        summary += f"Last error: {error_lines[-1]['line'][:150]}"

    return {
        "service": service,
        "available": True,
        "source": source,
        "error_count": len(error_lines),
        "error_types": type_counts,
        "dominant_error": dominant_error,
        "errors": error_lines[-5:],  # last 5 errors
        "summary": summary,
    }


async def analyze_multiple_services(
    services: List[str],
    namespace: str = "default",
) -> Dict[str, Dict[str, Any]]:
    """Analyze logs for multiple services in parallel."""
    import asyncio
    tasks = [analyze_service_logs(s, namespace) for s in services]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = {}
    for svc, result in zip(services, results):
        if isinstance(result, Exception):
            out[svc] = {"service": svc, "available": False, "error_count": 0, "summary": str(result)}
        else:
            out[svc] = result
    return out


def build_log_context_for_llm(log_analyses: Dict[str, Dict]) -> str:
    """
    Format log analysis results as a prompt context string for the LLM.
    This enriches the LLM prompt with real log evidence.
    """
    lines = ["=== Log Analysis ==="]
    for service, analysis in log_analyses.items():
        if not analysis.get("available"):
            lines.append(f"{service}: no logs available")
            continue
        lines.append(f"\n{service} [{analysis.get('source', '?')}]:")
        lines.append(f"  Errors: {analysis['error_count']}")
        if analysis.get("dominant_error"):
            lines.append(f"  Dominant: {analysis['dominant_error']}")
        for err in analysis.get("errors", [])[-3:]:
            lines.append(f"  > {err['line'][:150]}")
    return "\n".join(lines)
