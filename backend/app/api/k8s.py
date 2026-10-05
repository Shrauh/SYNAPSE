from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.services.k8s_discovery import k8s_discovery
from app.services.recovery_executor import recovery_executor
from app.ai_module.rl.recovery_engine import RecoveryAction, ActionType

router = APIRouter(prefix="/k8s", tags=["kubernetes"])

@router.get("/services")
def list_services():
    return k8s_discovery.discover_services()

@router.get("/topology")
def get_topology():
    return k8s_discovery.discover_topology()

@router.get("/pods")
def get_pods():
    services = k8s_discovery.discover_services()
    result = {}
    for svc in services:
        result[svc] = k8s_discovery.get_pod_status(svc)
    return result

@router.post("/recover/{service}")
def execute_recovery(service: str, dry_run: bool = True):
    action = RecoveryAction(
        action_type=ActionType.RESTART_POD,
        target_service=service,
        confidence=1.0,
        reason="Manual API trigger"
    )
    old_dry = recovery_executor.dry_run
    recovery_executor.dry_run = dry_run
    res = recovery_executor.execute_recovery(action)
    recovery_executor.dry_run = old_dry
    return {"success": res, "service": service, "action": "restart", "dry_run": dry_run}

@router.post("/recover/{service}/scale")
def scale_service(service: str, replicas: int, dry_run: bool = True):
    action = RecoveryAction(
        action_type=ActionType.SCALE_UP if replicas > 1 else ActionType.SCALE_DOWN,
        target_service=service,
        parameters={"replicas": replicas},
        confidence=1.0,
        reason="Manual API scale"
    )
    old_dry = recovery_executor.dry_run
    recovery_executor.dry_run = dry_run
    res = recovery_executor.execute_recovery(action)
    recovery_executor.dry_run = old_dry
    return {"success": res, "service": service, "action": "scale", "replicas": replicas, "dry_run": dry_run}


@router.post("/detect")
async def live_detect():
    """Run live anomaly detection using real Prometheus metrics + K8s discovery.

    This is the REAL detection pipeline — no simulator, no synthetic data.
    Reads actual metrics from Prometheus and runs the full AI pipeline.
    """
    from app.services.prometheus_ingestion import prometheus_ingestion

    # Step 1: Discover live services from K8s
    services = k8s_discovery.discover_services()
    if not services:
        raise HTTPException(status_code=503, detail="No K8s services found. Is kubectl working?")

    # Step 2: Check Prometheus
    prom_ok = await prometheus_ingestion.check_connection()

    # Step 3: Fetch real metrics
    prometheus_ingestion.set_services(services)
    metrics = await prometheus_ingestion.fetch_current_metrics(services)

    # Step 4: Compute feature matrix
    import numpy as np
    feature_names = ["latency", "error_rate", "cpu", "memory", "request_rate"]
    matrix = np.zeros((len(services), len(feature_names)))
    for i, svc in enumerate(services):
        for j, feat in enumerate(feature_names):
            matrix[i, j] = metrics.get(svc, {}).get(feat, 0.0)

    # Step 5: Anomaly detection (z-score based on real metrics)
    mean = matrix.mean(axis=0, keepdims=True)
    std = matrix.std(axis=0, keepdims=True) + 1e-8
    z_scores = np.abs((matrix - mean) / std)
    anomaly_scores = z_scores.mean(axis=1)

    # Normalize to 0-1
    max_score = anomaly_scores.max() if anomaly_scores.max() > 0 else 1.0
    anomaly_scores = anomaly_scores / max_score

    # Build results
    scored_services = {svc: round(float(anomaly_scores[i]), 4) for i, svc in enumerate(services)}
    anomalous = {svc: score for svc, score in scored_services.items() if score > 0.5}
    healthy = {svc: score for svc, score in scored_services.items() if score <= 0.5}

    # Step 6: Get pod statuses
    pod_statuses = {}
    for svc in services:
        pod_statuses[svc] = k8s_discovery.get_pod_status(svc)

    # Find crashed/unhealthy pods
    unhealthy_pods = {svc: status for svc, status in pod_statuses.items()
                      if status not in ("Running", "running", None)}

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
    """Full pipeline: detect anomalies → identify root cause → execute recovery.

    Set dry_run=false to actually execute kubectl commands.
    """
    detection = await live_detect()

    anomalous = detection.get("anomalous_services", {})
    unhealthy = detection.get("unhealthy_pods", {})

    if not anomalous and not unhealthy:
        return {
            "status": "healthy",
            "message": "All services are healthy. No recovery needed.",
            **detection,
        }

    # Find root cause (most anomalous or first unhealthy)
    if anomalous:
        root_cause = max(anomalous, key=anomalous.get)
        confidence = anomalous[root_cause]
    elif unhealthy:
        root_cause = list(unhealthy.keys())[0]
        confidence = 1.0
    else:
        return {"status": "healthy", "message": "No issues found.", **detection}

    # Classify severity
    from app.ai_module.severity.classifier import severity_classifier
    severity_result = severity_classifier.classify(
        anomaly_scores=detection["anomaly_scores"],
        causal_confidence=confidence,
        root_cause_service=root_cause,
    )

    # Select recovery action
    from app.ai_module.rl.recovery_engine import recovery_engine
    recovery_action = recovery_engine.select_action(
        severity_level=severity_result.level.value,
        root_cause_service=root_cause,
        fault_type="detected_anomaly",
        causal_confidence=confidence,
    )

    # Execute recovery
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
