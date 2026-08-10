"""
Prometheus Real-Time Metrics Ingestion for SYNAPSE.

Replaces the data simulator with real metrics scraped from
Prometheus, enabling true real-time anomaly detection.
"""
import httpx
import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PROMETHEUS_URL = "http://localhost:9090"
SERVICES = [
    "api-gateway", "auth-service", "user-service",
    "order-service", "payment-service",
]
METRICS = ["latency", "error_rate", "cpu", "memory", "request_rate"]


class PrometheusIngestion:
    """Ingest real-time metrics from Prometheus API."""

    def __init__(self, prometheus_url: str = PROMETHEUS_URL):
        self.base_url = prometheus_url
        self._baseline: Dict[str, Dict[str, float]] = {}

    async def fetch_current_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Fetch current metrics for all services from Prometheus.

        Returns:
            Dict mapping service_name -> {metric_name: value}
        """
        metrics = {}
        for service in SERVICES:
            metrics[service] = {
                "latency": await self._query_metric(
                    f'rate(http_request_duration_seconds_sum{{service="{service}"}}[1m]) / '
                    f'rate(http_request_duration_seconds_count{{service="{service}"}}[1m])'
                ),
                "error_rate": await self._query_metric(
                    f'rate(http_errors_total{{service="{service}"}}[1m])'
                ),
                "cpu": await self._query_metric(
                    f'process_cpu_percent{{service="{service}"}}'
                ),
                "memory": await self._query_metric(
                    f'process_memory_mb{{service="{service}"}}'
                ),
                "request_rate": await self._query_metric(
                    f'rate(http_requests_total{{service="{service}"}}[1m])'
                ),
            }
        return metrics

    async def fetch_feature_matrix(self) -> np.ndarray:
        """
        Fetch metrics and return as feature matrix for GNN.

        Returns:
            numpy array of shape [num_services, num_features]
        """
        metrics = await self.fetch_current_metrics()
        matrix = np.zeros((len(SERVICES), len(METRICS)))
        for i, svc in enumerate(SERVICES):
            for j, metric in enumerate(METRICS):
                matrix[i, j] = metrics.get(svc, {}).get(metric, 0.0)
        return matrix

    async def compute_deltas(self) -> Dict[str, Dict[str, str]]:
        """
        Compute metric deltas from baseline for LLM context.

        Returns:
            Dict mapping service -> {metric: "+XX%" or "-XX%"}
        """
        current = await self.fetch_current_metrics()
        deltas = {}

        for svc, values in current.items():
            svc_deltas = {}
            baseline = self._baseline.get(svc, {})
            for metric, val in values.items():
                base = baseline.get(metric, val)
                if base > 0:
                    pct = ((val - base) / base) * 100
                    svc_deltas[metric] = f"{pct:+.0f}%"
                else:
                    svc_deltas[metric] = "+0%"
            deltas[svc] = svc_deltas

        return deltas

    def update_baseline(self, metrics: Dict[str, Dict[str, float]]):
        """Update baseline metrics for delta computation."""
        self._baseline = {
            svc: dict(vals) for svc, vals in metrics.items()
        }

    async def _query_metric(self, query: str) -> float:
        """Query a single metric from Prometheus."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/query",
                    params={"query": query},
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("data", {}).get("result", [])
                if results:
                    return float(results[0]["value"][1])
                return 0.0
        except Exception as e:
            logger.debug(f"Prometheus query failed: {e}")
            return 0.0

    async def check_connection(self) -> bool:
        """Check if Prometheus is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/v1/status/config")
                return resp.status_code == 200
        except Exception:
            return False


# Module-level singleton
prometheus_ingestion = PrometheusIngestion()
