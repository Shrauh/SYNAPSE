"""
SYNAPSE Verification Service — Post-action outcome evaluation.

Collects available telemetry, compares pre/post metrics, evaluates
against defined success criteria, and determines verification outcome.

CRITICAL: Never reports VERIFIED_SUCCESS when required metrics are
missing, stale (>5 min old), or unavailable. Uses INCONCLUSIVE in
all uncertain cases.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.models import ServiceMetric, SuggestedAction, Incident, VerificationRun

logger = logging.getLogger("synapse.verification")

# Metric staleness threshold — older than this → data not fresh
STALE_THRESHOLD_SECONDS = 300  # 5 minutes

# Minimum metric count for a conclusive verification
MIN_METRICS_FOR_CONCLUSIVE = 1


async def collect_verification_evidence(
    db: AsyncSession,
    action: SuggestedAction,
    incident: Incident,
) -> Dict[str, Any]:
    """
    Collect pre/post metrics and evaluate verification criteria.
    Returns a dict with outcome, metric_comparison, and evidence quality fields.
    """
    target_service = action.target_service or incident.root_cause_service or ""
    criteria = action.verification_metrics or []
    missing_metrics: List[str] = []
    metric_comparison: List[Dict] = []

    # Get baseline (pre-action) — use incident anomaly_scores as proxy
    baseline_anomaly = (incident.anomaly_scores or {}).get(target_service)

    # Get post-action metrics from ServiceMetric table
    post_metrics = await _get_recent_metrics(db, target_service, window_seconds=120)
    baseline_metrics = await _get_recent_metrics(
        db, target_service, window_seconds=600, offset_seconds=120
    )

    data_freshness_seconds = None
    if post_metrics:
        newest = max(post_metrics, key=lambda m: m.timestamp)
        data_freshness_seconds = (
            datetime.now(timezone.utc) - newest.timestamp.replace(tzinfo=timezone.utc)
            if newest.timestamp.tzinfo is None
            else (datetime.now(timezone.utc) - newest.timestamp)
        ).total_seconds()

    # Build baseline/post snapshots
    baseline_snapshot = _aggregate_metrics(baseline_metrics) if baseline_metrics else None
    post_snapshot = _aggregate_metrics(post_metrics) if post_metrics else None

    # If no post-action data at all → INCONCLUSIVE
    if not post_metrics:
        return {
            "outcome": "VERIFICATION_INCONCLUSIVE",
            "metric_comparison": [],
            "baseline_snapshot": baseline_snapshot,
            "post_action_snapshot": None,
            "data_freshness_seconds": None,
            "missing_metrics": ["all — no telemetry available for service"],
            "symptoms_resolved": None,
            "original_anomalies_cleared": None,
            "summary": (
                f"Verification inconclusive: no telemetry data available for {target_service!r} "
                f"after action execution. Cannot confirm recovery."
            ),
            "next_step_recommendation": (
                "Ensure Prometheus is scraping this service and retry verification in 2-3 minutes."
            ),
        }

    # Data staleness check
    if data_freshness_seconds and data_freshness_seconds > STALE_THRESHOLD_SECONDS:
        return {
            "outcome": "VERIFICATION_INCONCLUSIVE",
            "metric_comparison": [],
            "baseline_snapshot": baseline_snapshot,
            "post_action_snapshot": post_snapshot,
            "data_freshness_seconds": data_freshness_seconds,
            "missing_metrics": [f"stale data ({data_freshness_seconds:.0f}s old)"],
            "symptoms_resolved": None,
            "original_anomalies_cleared": None,
            "summary": (
                f"Verification inconclusive: telemetry for {target_service!r} is "
                f"{data_freshness_seconds:.0f}s stale (threshold: {STALE_THRESHOLD_SECONDS}s)."
            ),
            "next_step_recommendation": "Wait for fresh telemetry and retry verification.",
        }

    # Compare metrics
    criteria_results = []
    all_criteria_met = True
    any_criterion_available = False

    metric_fields = {
        "latency": ("latency", "ms", "decrease"),
        "error_rate": ("error_rate", "ratio", "decrease"),
        "cpu": ("cpu", "%", "decrease"),
        "memory": ("memory", "%", "decrease"),
        "request_rate": ("request_rate", "rps", "increase"),
    }

    for metric_name, (field, unit, default_direction) in metric_fields.items():
        base_val = getattr(baseline_snapshot, field, None) if baseline_snapshot else None
        post_val = getattr(post_snapshot, field, None) if post_snapshot else None

        if base_val is None or post_val is None:
            missing_metrics.append(metric_name)
            metric_comparison.append({
                "metric": metric_name,
                "source": "service_metrics",
                "unit": unit,
                "baseline": None,
                "post": None,
                "diff": None,
                "pct_change": None,
                "interpretation": "unavailable",
                "missing_data_reason": "No baseline or post-action data",
                "data_fresh": False,
            })
            continue

        any_criterion_available = True
        diff = post_val - base_val
        pct_change = (diff / base_val * 100) if abs(base_val) > 1e-9 else None

        # Find matching criterion from action's verification_metrics
        criterion = next(
            (c for c in criteria if c.get("metric") == metric_name), None
        )
        direction = (criterion or {}).get("direction", default_direction)
        threshold = (criterion or {}).get("threshold")

        # Determine interpretation
        if direction == "decrease":
            improved = diff < 0
            interpretation = "improved" if improved else ("unchanged" if abs(diff) < 0.01 else "regressed")
        elif direction == "increase":
            improved = diff > 0
            interpretation = "improved" if improved else ("unchanged" if abs(diff) < 0.01 else "regressed")
        else:
            improved = abs(diff) < 0.05
            interpretation = "stable" if improved else "changed"

        # Check threshold
        criterion_met = True
        if threshold is not None:
            if direction == "decrease":
                criterion_met = post_val <= threshold
            elif direction == "increase":
                criterion_met = post_val >= threshold

        if criterion and not criterion_met:
            all_criteria_met = False

        criteria_results.append({
            "metric": metric_name,
            "threshold": threshold,
            "direction": direction,
            "met": criterion_met,
        })

        metric_comparison.append({
            "metric": metric_name,
            "source": "service_metrics",
            "unit": unit,
            "baseline": round(base_val, 4),
            "post": round(post_val, 4),
            "diff": round(diff, 4),
            "pct_change": round(pct_change, 2) if pct_change is not None else None,
            "interpretation": interpretation,
            "data_fresh": (data_freshness_seconds or 0) < STALE_THRESHOLD_SECONDS,
        })

    # Determine final outcome
    if not any_criterion_available:
        outcome = "VERIFICATION_INCONCLUSIVE"
        summary = f"Verification inconclusive: no metric data available for comparison."
        next_step = "Check Prometheus connectivity and retry."
    elif all_criteria_met and criteria_results:
        outcome = "VERIFIED_SUCCESS"
        summary = f"Verification succeeded: all measurable criteria met for {target_service!r}."
        next_step = "Monitor for 15 minutes to confirm stability."
    else:
        # Check if things are generally improving even without explicit criteria
        improvements = sum(1 for m in metric_comparison if m.get("interpretation") == "improved")
        regressions = sum(1 for m in metric_comparison if m.get("interpretation") == "regressed")
        if improvements > regressions and improvements >= 2:
            outcome = "VERIFIED_SUCCESS"
            summary = f"Verification succeeded: {improvements} of {len(metric_comparison)} metrics improved."
            next_step = "Monitor for 15 minutes to confirm stability."
        elif regressions > improvements:
            outcome = "VERIFICATION_FAILED"
            summary = f"Verification failed: {regressions} metrics regressed after action."
            next_step = "Consider rollback if regression is significant."
        else:
            outcome = "VERIFICATION_INCONCLUSIVE"
            summary = f"Verification inconclusive: mixed or minimal metric changes observed."
            next_step = "Collect more telemetry and consider manual inspection."

    return {
        "outcome": outcome,
        "criteria": criteria_results,
        "metric_comparison": metric_comparison,
        "baseline_snapshot": _snapshot_dict(baseline_snapshot),
        "post_action_snapshot": _snapshot_dict(post_snapshot),
        "data_freshness_seconds": data_freshness_seconds,
        "missing_metrics": missing_metrics,
        "symptoms_resolved": 1 if outcome == "VERIFIED_SUCCESS" else (0 if outcome == "VERIFICATION_FAILED" else None),
        "original_anomalies_cleared": 1 if outcome == "VERIFIED_SUCCESS" else None,
        "summary": summary,
        "next_step_recommendation": next_step,
    }


async def _get_recent_metrics(
    db: AsyncSession,
    service_name: str,
    window_seconds: int = 120,
    offset_seconds: int = 0,
) -> List[ServiceMetric]:
    """Get recent metrics for a service within a time window."""
    if not service_name:
        return []
    now = datetime.now(timezone.utc)
    end = now - timedelta(seconds=offset_seconds)
    start = end - timedelta(seconds=window_seconds)

    result = await db.execute(
        select(ServiceMetric)
        .where(ServiceMetric.service_name == service_name)
        .where(ServiceMetric.timestamp >= start)
        .where(ServiceMetric.timestamp <= end)
        .order_by(desc(ServiceMetric.timestamp))
        .limit(50)
    )
    return list(result.scalars().all())


class _MetricAggregate:
    __slots__ = ("latency", "error_rate", "cpu", "memory", "request_rate")
    def __init__(self, latency, error_rate, cpu, memory, request_rate):
        self.latency = latency
        self.error_rate = error_rate
        self.cpu = cpu
        self.memory = memory
        self.request_rate = request_rate


def _aggregate_metrics(metrics: List[ServiceMetric]) -> Optional[_MetricAggregate]:
    if not metrics:
        return None
    n = len(metrics)
    return _MetricAggregate(
        latency=sum(m.latency for m in metrics) / n,
        error_rate=sum(m.error_rate for m in metrics) / n,
        cpu=sum(m.cpu for m in metrics) / n,
        memory=sum(m.memory for m in metrics) / n,
        request_rate=sum(m.request_rate for m in metrics) / n,
    )


def _snapshot_dict(agg: Optional[_MetricAggregate]) -> Optional[Dict]:
    if agg is None:
        return None
    return {
        "latency": round(agg.latency, 4),
        "error_rate": round(agg.error_rate, 6),
        "cpu": round(agg.cpu, 4),
        "memory": round(agg.memory, 4),
        "request_rate": round(agg.request_rate, 4),
    }
