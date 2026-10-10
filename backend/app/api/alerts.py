"""
SYNAPSE Alert Webhook — Alertmanager integration for automatic RCA triggering.

When Prometheus detects an anomaly and Alertmanager fires, this endpoint
automatically triggers SYNAPSE's full RCA pipeline without manual intervention.

Alertmanager webhook config:
  receivers:
  - name: synapse
    webhook_configs:
    - url: http://synapse-backend:8000/api/v1/alerts/webhook
      send_resolved: true
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import Incident
from app.api.rca import _run_pipeline_background

router = APIRouter(prefix="/alerts", tags=["Alert Webhook"])
logger = logging.getLogger("synapse.alerts")

# Track processed alert fingerprints to avoid duplicate RCA runs
_processed_alerts: Dict[str, str] = {}  # fingerprint -> incident_id


class AlertLabel(BaseModel):
    """Prometheus alert labels."""
    alertname: Optional[str] = None
    service: Optional[str] = None        # the affected service
    namespace: Optional[str] = "default"
    severity: Optional[str] = "warning"
    job: Optional[str] = None
    instance: Optional[str] = None
    # allow extra fields
    model_config = {"extra": "allow"}


class AlertAnnotation(BaseModel):
    """Prometheus alert annotations."""
    summary: Optional[str] = None
    description: Optional[str] = None
    model_config = {"extra": "allow"}


class PrometheusAlert(BaseModel):
    """Single alert from Alertmanager."""
    status: str  # 'firing' | 'resolved'
    labels: AlertLabel
    annotations: AlertAnnotation = AlertAnnotation()
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    fingerprint: Optional[str] = None
    generatorURL: Optional[str] = None


class AlertmanagerPayload(BaseModel):
    """Full Alertmanager webhook payload."""
    version: Optional[str] = "4"
    groupKey: Optional[str] = None
    status: str  # 'firing' | 'resolved'
    receiver: Optional[str] = None
    alerts: List[PrometheusAlert] = []
    commonLabels: Dict[str, str] = {}
    groupLabels: Dict[str, str] = {}
    externalURL: Optional[str] = None


def _extract_service(alert: PrometheusAlert) -> Optional[str]:
    """Extract service name from alert labels (tries multiple label keys)."""
    labels = alert.labels
    # Try in order of specificity
    for attr in ["service", "job", "instance"]:
        val = getattr(labels, attr, None)
        if val and val not in ("prometheus", "node-exporter", "unknown"):
            # Strip port from instance (e.g. 'my-service:8080' -> 'my-service')
            return val.split(":")[0]
    # Try extra fields
    extra = labels.model_extra or {}
    for key in ["deployment", "pod", "container", "app"]:
        if key in extra:
            val = str(extra[key])
            # Strip random pod suffix (my-svc-abc123-xyz -> my-svc)
            parts = val.rsplit("-", 2)
            return parts[0] if len(parts) >= 2 else val
    return None


def _extract_fault_type(alert: PrometheusAlert) -> str:
    """Infer fault type from alert name and annotations."""
    name = (alert.labels.alertname or "").lower()
    desc = (alert.annotations.description or "").lower()
    combined = name + " " + desc

    if any(x in combined for x in ["latency", "slow", "response_time", "duration"]):
        return "latency_spike"
    elif any(x in combined for x in ["error", "5xx", "fail", "exception"]):
        return "error_spike"
    elif any(x in combined for x in ["cpu", "throttl"]):
        return "cpu_overload"
    elif any(x in combined for x in ["memory", "oom", "heap"]):
        return "memory_leak"
    elif any(x in combined for x in ["timeout", "connect", "refused"]):
        return "connection_timeout"
    elif any(x in combined for x in ["restart", "crash", "crashloop"]):
        return "error_spike"
    return "anomaly"


@router.post("/webhook")
async def alertmanager_webhook(
    payload: AlertmanagerPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Alertmanager webhook endpoint — auto-triggers SYNAPSE RCA for firing alerts.

    Configure in Alertmanager:
      webhook_configs:
      - url: http://synapse-backend:8000/api/v1/alerts/webhook
    """
    firing_alerts = [a for a in payload.alerts if a.status == "firing"]
    resolved_alerts = [a for a in payload.alerts if a.status == "resolved"]

    logger.info(
        f"Webhook received: {len(firing_alerts)} firing, "
        f"{len(resolved_alerts)} resolved alerts"
    )

    triggered_incidents = []
    skipped = []

    for alert in firing_alerts:
        fingerprint = alert.fingerprint or alert.labels.alertname or "unknown"

        # Skip if already processing this alert
        if fingerprint in _processed_alerts:
            skipped.append(fingerprint)
            continue

        service = _extract_service(alert)
        fault_type = _extract_fault_type(alert)
        severity = alert.labels.severity or "warning"
        alert_name = alert.labels.alertname or "UnknownAlert"

        # Create incident record
        now = datetime.now(timezone.utc)
        incident = Incident(
            title=f"[AUTO] {alert_name} — {service or 'unknown service'}",
            description=(
                f"Auto-triggered by Alertmanager.\n"
                f"Alert: {alert_name}\n"
                f"Service: {service}\n"
                f"Fault type: {fault_type}\n"
                f"Summary: {alert.annotations.summary or 'N/A'}\n"
                f"Description: {alert.annotations.description or 'N/A'}"
            ),
            status="analyzing",
            severity=severity,
            detected_at=now,
        )
        db.add(incident)
        await db.commit()
        await db.refresh(incident)

        _processed_alerts[fingerprint] = incident.id

        # Build simulation result for pipeline (use detected service)
        sim_hint = None
        if service:
            sim_hint = {
                "source": "alertmanager",
                "root_cause_service": service,
                "fault_type": fault_type,
                "alert_name": alert_name,
            }

        # Trigger RCA pipeline in background
        background_tasks.add_task(
            _run_pipeline_background,
            incident.id,
            sim_hint,
        )

        triggered_incidents.append({
            "incident_id": incident.id,
            "alert": alert_name,
            "service": service,
            "fault_type": fault_type,
            "status": "rca_triggered",
        })
        logger.info(
            f"RCA triggered for alert '{alert_name}' "
            f"service='{service}' incident={incident.id}"
        )

    # Clean up resolved alert fingerprints
    for alert in resolved_alerts:
        fp = alert.fingerprint or alert.labels.alertname
        if fp in _processed_alerts:
            del _processed_alerts[fp]
            logger.info(f"Alert resolved, cleared fingerprint: {fp}")

    return {
        "status": "ok",
        "firing": len(firing_alerts),
        "resolved": len(resolved_alerts),
        "triggered": triggered_incidents,
        "skipped_duplicates": skipped,
    }


@router.get("/status")
def alert_status() -> Dict[str, Any]:
    """Show currently tracked active alerts."""
    return {
        "active_alerts": len(_processed_alerts),
        "tracked": [
            {"fingerprint": fp, "incident_id": inc_id}
            for fp, inc_id in _processed_alerts.items()
        ],
        "webhook_url": "POST /api/v1/alerts/webhook",
        "alertmanager_config": (
            "receivers:\n"
            "- name: synapse\n"
            "  webhook_configs:\n"
            "  - url: http://<synapse-host>:8000/api/v1/alerts/webhook\n"
            "    send_resolved: true"
        ),
    }


@router.post("/test")
async def test_alert(
    service: str = "payment-service",
    fault_type: str = "latency_spike",
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Send a test alert to verify the webhook pipeline works.
    Use this to demo the auto-trigger flow without real Alertmanager.
    """
    fake_payload = AlertmanagerPayload(
        status="firing",
        alerts=[
            PrometheusAlert(
                status="firing",
                labels=AlertLabel(
                    alertname="TestAlert",
                    service=service,
                    severity="critical",
                ),
                annotations=AlertAnnotation(
                    summary=f"Test alert for {service}",
                    description=f"Simulated {fault_type} on {service}",
                ),
                fingerprint=f"test-{service}-{fault_type}",
            )
        ],
    )
    return await alertmanager_webhook(fake_payload, background_tasks, db)
