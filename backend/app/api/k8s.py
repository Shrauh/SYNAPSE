"""
Kubernetes Integration API module for SYNAPSE.

Provides endpoints to monitor pod status, inject faults (kill pods),
execute recovery commands, and run anomaly detection against real K8s clusters.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_module.rl.recovery_engine import ActionType, RecoveryAction
from app.db.database import async_session, get_db
from app.db.models import Incident
from app.services.k8s_discovery import k8s_discovery
from app.services.recovery_executor import recovery_executor

logger = logging.getLogger("synapse.k8s")

router = APIRouter(prefix="/k8s", tags=["Kubernetes"])

# Known Online Boutique microservices
ONLINE_BOUTIQUE_SERVICES = {
    "frontend",
    "cartservice",
    "productcatalogservice",
    "currencyservice",
    "paymentservice",
    "shippingservice",
    "emailservice",
    "checkoutservice",
    "recommendationservice",
    "redis-cart",
    "adservice",
    "loadgenerator",
}


# ─────────────────────────────────────────────────────────────
# Request / Response Schemas
# ─────────────────────────────────────────────────────────────

class InjectFaultRequest(BaseModel):
    service: str = Field(..., description="Target service to inject fault into (e.g. 'cartservice')")
    fault_type: str = Field(default="pod_kill", description="Fault injection type (default: 'pod_kill')")


class RecoverRequest(BaseModel):
    service: str = Field(..., description="Target service to recover (e.g. 'cartservice')")
    action: str = Field(..., description="Recovery action: 'restart_pod' or 'scale_up'")


class PodInfo(BaseModel):
    name: str
    status: str
    ready: bool
    restarts: int
    age: str
    service: str


class ClusterStatusResponse(BaseModel):
    status: str
    total_pods: int
    total: int
    running: int
    failed: int
    services: List[str]
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Async Helper Functions
# ─────────────────────────────────────────────────────────────

async def _run_kubectl_async(cmd: List[str], timeout: int = 30) -> tuple[int, str, str]:
    """Execute a kubectl command asynchronously using run_in_executor with timeout."""
    loop = asyncio.get_running_loop()

    def _exec() -> tuple[int, str, str]:
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"kubectl command timed out after {timeout}s: {' '.join(cmd)}")
            return -1, "", f"kubectl command timed out after {timeout} seconds"
        except FileNotFoundError:
            logger.error("kubectl executable not found in system PATH")
            return -1, "", "kubectl executable not found in PATH"
        except Exception as e:
            logger.error(f"kubectl execution error: {e}")
            return -1, "", str(e)

    return await loop.run_in_executor(None, _exec)


def _extract_pod_status(item: dict) -> str:
    """Extract human-readable pod status matching standard kubectl output."""
    if item.get("metadata", {}).get("deletionTimestamp"):
        return "Terminating"

    status_obj = item.get("status", {}) or {}

    # Inspect containerStatuses for specific states
    container_statuses = status_obj.get("containerStatuses", []) or []
    for cs in container_statuses:
        state = cs.get("state", {}) or {}
        waiting = state.get("waiting")
        if waiting:
            return waiting.get("reason", "Waiting")
        terminated = state.get("terminated")
        if terminated:
            reason = terminated.get("reason")
            if reason:
                return reason
            exit_code = terminated.get("exitCode", 0)
            if exit_code != 0:
                return f"Error ({exit_code})"

    # Inspect initContainerStatuses
    init_statuses = status_obj.get("initContainerStatuses", []) or []
    for cs in init_statuses:
        state = cs.get("state", {}) or {}
        waiting = state.get("waiting")
        if waiting:
            return f"Init:{waiting.get('reason', 'Waiting')}"
        terminated = state.get("terminated")
        if terminated and terminated.get("exitCode", 0) != 0:
            return "Init:Error"

    return status_obj.get("phase", "Unknown")


def _extract_pod_ready(item: dict) -> bool:
    """Determine whether the pod is ready to serve traffic."""
    conditions = item.get("status", {}).get("conditions", []) or []
    for cond in conditions:
        if cond.get("type") == "Ready":
            return cond.get("status") == "True"

    container_statuses = item.get("status", {}).get("containerStatuses", []) or []
    if container_statuses:
        return all(cs.get("ready", False) for cs in container_statuses)
    return False


def _extract_pod_restarts(item: dict) -> int:
    """Sum total restart count across all containers in the pod."""
    container_statuses = item.get("status", {}).get("containerStatuses", []) or []
    return sum(cs.get("restartCount", 0) for cs in container_statuses)


def _extract_pod_age(item: dict) -> str:
    """Format pod age into a readable duration string (e.g. '12m', '3h', '2d')."""
    ts_str = item.get("metadata", {}).get("creationTimestamp")
    if not ts_str:
        return "unknown"
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        created = datetime.fromisoformat(ts_str)
        delta = datetime.now(timezone.utc) - created
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        rem_min = minutes % 60
        if hours < 24:
            return f"{hours}h{rem_min}m" if rem_min else f"{hours}h"
        days = hours // 24
        rem_hours = hours % 24
        return f"{days}d{rem_hours}h" if rem_hours else f"{days}d"
    except Exception:
        return "unknown"


def _extract_pod_service(item: dict) -> str:
    """Extract Online Boutique service name from metadata labels or name."""
    metadata = item.get("metadata", {}) or {}
    labels = metadata.get("labels", {}) or {}
    name = metadata.get("name", "")

    # Look for app label
    service = (
        labels.get("app")
        or labels.get("app.kubernetes.io/name")
        or labels.get("app.kubernetes.io/instance")
        or ""
    )

    # Fallback: check if pod name starts with any known boutique service
    if not service:
        for s in ONLINE_BOUTIQUE_SERVICES:
            if name == s or name.startswith(f"{s}-"):
                service = s
                break

    return service


async def _fetch_boutique_pods_async() -> List[Dict[str, Any]]:
    """Query kubectl for pods in default namespace and filter to Online Boutique services."""
    retcode, stdout, stderr = await _run_kubectl_async(
        ["kubectl", "get", "pods", "-n", "default", "-o", "json"],
        timeout=30,
    )

    if retcode != 0:
        logger.error(f"kubectl get pods failed (code {retcode}): {stderr}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to query Kubernetes pods: {stderr.strip() or 'kubectl execution error'}",
        )

    try:
        data = json.loads(stdout)
    except Exception as e:
        logger.error(f"Failed to parse kubectl json output: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse kubectl pod output: {e}",
        )

    pods: List[Dict[str, Any]] = []
    for item in data.get("items", []):
        metadata = item.get("metadata", {}) or {}
        namespace = metadata.get("namespace", "default")
        if namespace == "kube-system":
            continue

        service = _extract_pod_service(item)
        if service not in ONLINE_BOUTIQUE_SERVICES:
            continue

        pods.append({
            "name": metadata.get("name", "unknown"),
            "status": _extract_pod_status(item),
            "ready": _extract_pod_ready(item),
            "restarts": _extract_pod_restarts(item),
            "age": _extract_pod_age(item),
            "service": service,
        })

    return pods


# ─────────────────────────────────────────────────────────────
# Required Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/pods", response_model=List[PodInfo])
async def get_pods():
    """
    Returns real pod status from Kubernetes cluster.

    - Queries `kubectl get pods -n default -o json`
    - Returns clean list of pods with: name, status, ready, restarts, age, service label
    - Filters to only Online Boutique services (excluding kube-system)
    """
    pods = await _fetch_boutique_pods_async()
    return pods


@router.post("/inject-fault")
async def inject_fault(
    req: InjectFaultRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Kill a pod to inject a real fault into the Kubernetes cluster.

    - Executes: `kubectl delete pod -l app={service} -n default --grace-period=0 --force`
    - Creates an Incident record in the database
    - Triggers the RCA pipeline in the background
    - Broadcasts the fault injection event via WebSocket
    - Returns killed pod names, incident ID, and status message
    """
    service = req.service.strip()
    fault_type = req.fault_type.strip()

    # Step 1: Query existing pods for this service before deletion
    rc, stdout, _ = await _run_kubectl_async(
        ["kubectl", "get", "pods", "-l", f"app={service}", "-n", "default", "-o", "jsonpath={.items[*].metadata.name}"]
    )
    killed_pods = stdout.strip().split() if stdout.strip() else []

    # Step 2: Delete pods forcibly
    del_rc, del_stdout, del_stderr = await _run_kubectl_async(
        ["kubectl", "delete", "pod", "-l", f"app={service}", "-n", "default", "--grace-period=0", "--force"]
    )

    # If killed_pods wasn't found before deletion, parse from deletion output
    if not killed_pods and del_stdout:
        for line in del_stdout.splitlines():
            if "deleted" in line.lower():
                for token in line.split():
                    cleaned = token.strip('"').strip("'").strip("`")
                    if cleaned.startswith("pod/"):
                        killed_pods.append(cleaned.split("/", 1)[1])
                    elif "-" in cleaned and not cleaned.startswith("warning"):
                        killed_pods.append(cleaned)

    # Check for hard deletion error if no pods were found/deleted
    if del_rc != 0 and not killed_pods:
        err_msg = del_stderr.strip() or del_stdout.strip()
        logger.error(f"kubectl delete failed: {err_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to kill pods for service '{service}': {err_msg}",
        )

    # Fallback display if pod name wasn't explicitly captured
    if not killed_pods:
        killed_pods = [f"{service}-pod"]

    now = datetime.now(timezone.utc)

    # Step 3: Create Incident record
    incident = Incident(
        title=f"K8s Fault Injection: {service} ({fault_type})",
        description=f"Fault '{fault_type}' injected on Kubernetes service '{service}'. Pods killed: {', '.join(killed_pods)}.",
        status="analyzing",
        severity="high",
        root_cause_service=service,
        fault_type=fault_type,
        affected_services=[service],
        timeline=[
            {
                "timestamp": now.isoformat(),
                "event": f"Fault '{fault_type}' injected on '{service}'. Pods terminated forcibly.",
                "service": service,
                "type": "fault_injection",
            }
        ],
        window_start=now - timedelta(minutes=5),
        window_end=now,
        detected_at=now,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    incident_id = incident.id

    # Step 4: Trigger RCA pipeline in the background
    from app.api.rca import _run_pipeline_background
    background_tasks.add_task(
        _run_pipeline_background,
        incident_id,
        {"service": service, "fault_type": fault_type},
    )

    # Step 5: Broadcast via WebSocket
    try:
        from app.api.ws import manager
        await manager.broadcast({
            "type": "k8s_fault_injected",
            "service": service,
            "fault_type": fault_type,
            "killed_pods": killed_pods,
            "incident_id": incident_id,
            "timestamp": now.isoformat(),
        })
    except Exception as ws_err:
        logger.warning(f"WebSocket broadcast error: {ws_err}")

    return {
        "killed_pods": killed_pods,
        "incident_id": incident_id,
        "message": "Pod killed, RCA pipeline started",
    }


@router.get("/status", response_model=ClusterStatusResponse)
async def get_cluster_status():
    """
    Quick cluster health check.

    Returns:
    - total_pods: Total Online Boutique pods discovered
    - running: Number of ready pods running normally
    - failed: Number of failed/crashed/not-ready pods
    - services: List of distinct service names
    - status: 'healthy', 'degraded', or 'unavailable'
    """
    try:
        pods = await _fetch_boutique_pods_async()
    except HTTPException as e:
        return ClusterStatusResponse(
            status="unavailable",
            total_pods=0,
            total=0,
            running=0,
            failed=0,
            services=[],
            error=e.detail,
        )
    except Exception as e:
        return ClusterStatusResponse(
            status="error",
            total_pods=0,
            total=0,
            running=0,
            failed=0,
            services=[],
            error=str(e),
        )

    total_pods = len(pods)
    running = sum(1 for p in pods if p["status"] == "Running" and p["ready"])
    failed = sum(
        1 for p in pods
        if p["status"] in ("Error", "CrashLoopBackOff", "Failed", "OOMKilled", "ErrImagePull", "ImagePullBackOff")
        or not p["ready"]
    )
    services = sorted(list({p["service"] for p in pods if p.get("service")}))
    status_str = "healthy" if failed == 0 and total_pods > 0 else ("degraded" if failed > 0 else "unknown")

    return ClusterStatusResponse(
        status=status_str,
        total_pods=total_pods,
        total=total_pods,
        running=running,
        failed=failed,
        services=services,
    )


@router.post("/recover")
async def recover_service(req: RecoverRequest):
    """
    Execute real kubectl recovery commands.

    - For `restart_pod`: `kubectl rollout restart deployment/{service} -n default`
    - For `scale_up`: `kubectl scale deployment/{service} --replicas=3 -n default`
    - Returns the kubectl output
    """
    service = req.service.strip()
    action = req.action.strip()
    action_key = action.lower()

    if action_key in ("restart_pod", "restart"):
        cmd = ["kubectl", "rollout", "restart", f"deployment/{service}", "-n", "default"]
    elif action_key in ("scale_up", "scale"):
        cmd = ["kubectl", "scale", f"deployment/{service}", "--replicas=3", "-n", "default"]
    elif action_key == "scale_down":
        cmd = ["kubectl", "scale", f"deployment/{service}", "--replicas=1", "-n", "default"]
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported recovery action: '{action}'. Expected 'restart_pod' or 'scale_up'."
        )

    retcode, stdout, stderr = await _run_kubectl_async(cmd, timeout=30)
    output = stdout.strip() if stdout.strip() else stderr.strip()

    if retcode != 0:
        logger.error(f"Recovery failed for {service} ({action}): {output}")
        raise HTTPException(
            status_code=500,
            detail=f"Recovery command failed (exit code {retcode}): {output}",
        )

    # Broadcast recovery event via WebSocket
    try:
        from app.api.ws import manager
        await manager.broadcast({
            "type": "k8s_recovery_executed",
            "service": service,
            "action": action,
            "output": output,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as ws_err:
        logger.warning(f"WebSocket broadcast error: {ws_err}")

    return {
        "success": True,
        "service": service,
        "action": action,
        "output": output,
        "message": f"Successfully executed '{action}' on {service}",
    }


# ─────────────────────────────────────────────────────────────
# Additional Discovery & Detection Endpoints (Compatibility)
# ─────────────────────────────────────────────────────────────

@router.get("/services")
def list_services():
    """Discover all Kubernetes deployments in default namespace."""
    return k8s_discovery.discover_services()


@router.get("/topology")
def get_topology():
    """Discover service call topology from Kubernetes environment variables."""
    return k8s_discovery.discover_topology()


@router.post("/detect")
async def live_detect():
    """Run live anomaly detection using real Prometheus metrics + K8s discovery."""
    from app.services.prometheus_ingestion import prometheus_ingestion
    import numpy as np

    services = k8s_discovery.discover_services()
    if not services:
        raise HTTPException(status_code=503, detail="No K8s services found. Is kubectl working?")

    prom_ok = await prometheus_ingestion.check_connection()
    prometheus_ingestion.set_services(services)
    metrics = await prometheus_ingestion.fetch_current_metrics(services)

    feature_names = ["latency", "error_rate", "cpu", "memory", "request_rate"]
    matrix = np.zeros((len(services), len(feature_names)))
    for i, svc in enumerate(services):
        for j, feat in enumerate(feature_names):
            matrix[i, j] = metrics.get(svc, {}).get(feat, 0.0)

    mean = matrix.mean(axis=0, keepdims=True)
    std = matrix.std(axis=0, keepdims=True) + 1e-8
    z_scores = np.abs((matrix - mean) / std)
    anomaly_scores = z_scores.mean(axis=1)

    max_score = anomaly_scores.max() if anomaly_scores.max() > 0 else 1.0
    anomaly_scores = anomaly_scores / max_score

    scored_services = {svc: round(float(anomaly_scores[i]), 4) for i, svc in enumerate(services)}
    anomalous = {svc: score for svc, score in scored_services.items() if score > 0.5}
    healthy = {svc: score for svc, score in scored_services.items() if score <= 0.5}

    pod_statuses = {}
    for svc in services:
        pod_statuses[svc] = k8s_discovery.get_pod_status(svc)

    unhealthy_pods = {
        svc: status for svc, status in pod_statuses.items()
        if status not in ("Running", "running", None)
    }

    return {
        "prometheus_connected": prom_ok,
        "total_services": len(services),
        "services": services,
        "anomaly_scores": scored_services,
        "anomalous_services": anomalous,
        "healthy_services": healthy,
        "pod_statuses": pod_statuses,
        "unhealthy_pods": unhealthy_pods,
        "metrics_snapshot": {svc: {k: round(v, 4) for k, v in m.items()} for svc, m in metrics.items()},
        "detection_method": "z-score + prometheus live metrics",
    }


@router.post("/detect-and-recover")
async def detect_and_recover(dry_run: bool = True):
    """Full pipeline: detect anomalies -> identify root cause -> execute recovery."""
    detection = await live_detect()

    anomalous = detection.get("anomalous_services", {})
    unhealthy = detection.get("unhealthy_pods", {})

    if not anomalous and not unhealthy:
        return {
            "status": "healthy",
            "message": "All services are healthy. No recovery needed.",
            **detection,
        }

    if anomalous:
        root_cause = max(anomalous, key=anomalous.get)
        confidence = anomalous[root_cause]
    elif unhealthy:
        root_cause = list(unhealthy.keys())[0]
        confidence = 1.0
    else:
        return {"status": "healthy", "message": "No issues found.", **detection}

    from app.ai_module.severity.classifier import severity_classifier
    severity_result = severity_classifier.classify(
        anomaly_scores=detection["anomaly_scores"],
        causal_confidence=confidence,
        root_cause_service=root_cause,
    )

    from app.ai_module.rl.recovery_engine import recovery_engine
    recovery_action = recovery_engine.select_action(
        severity_level=severity_result.level.value,
        root_cause_service=root_cause,
        fault_type="detected_anomaly",
        causal_confidence=confidence,
    )

    kubectl_result = None
    if recovery_action.action_type != ActionType.DO_NOTHING:
        old_dry = recovery_executor.dry_run
        recovery_executor.dry_run = dry_run
        kubectl_result = recovery_executor.execute_recovery(recovery_action)
        recovery_executor.dry_run = old_dry

    return {
        "status": "incident_detected",
        "root_cause": root_cause,
        "confidence": round(confidence, 2),
        "severity": severity_result.level.name,
        "response_strategy": severity_result.response_strategy,
        "recovery_action": recovery_action.action_type.value,
        "recovery_reason": recovery_action.reason,
        "kubectl_executed": kubectl_result,
        "dry_run": dry_run,
        **detection,
    }
