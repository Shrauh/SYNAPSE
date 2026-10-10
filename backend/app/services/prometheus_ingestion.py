"""
Prometheus Real-Time Metrics Ingestion for SYNAPSE.

Dynamically discovers services from K8s and fetches real metrics
from Prometheus, enabling true real-time anomaly detection on
ANY microservice system.
"""
import httpx
import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PROMETHEUS_URL = "http://localhost:9090"
METRICS = ["latency", "error_rate", "cpu", "memory", "request_rate"]


class PrometheusIngestion:
    """Ingest real-time metrics from Prometheus API.

    Supports dynamic service discovery — works with any K8s deployment,
    not just a hardcoded list.
    """

    def __init__(self, prometheus_url: str = PROMETHEUS_URL):
        self.base_url = prometheus_url
        self._baseline: Dict[str, Dict[str, float]] = {}
        self._services: List[str] = []

    def set_services(self, services: List[str]):
        """Set the list of services to monitor (from K8s discovery)."""
        self._services = services
        logger.info(f"[Prometheus] Monitoring {len(services)} services: {services}")

    async def discover_services_from_prometheus(self) -> List[str]:
        """Auto-discover services from Prometheus targets."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/v1/targets")
                resp.raise_for_status()
                data = resp.json()
                targets = data.get("data", {}).get("activeTargets", [])
                services = set()
                for t in targets:
                    labels = t.get("labels", {})
                    # Try common label keys for service name
                    for key in ["service", "app", "job", "kubernetes_name"]:
                        if key in labels and labels[key] not in ("prometheus", "node-exporter"):
                            services.add(labels[key])
                            break
                return sorted(services)
        except Exception as e:
            logger.debug(f"Prometheus target discovery failed: {e}")
            return []

    async def fetch_current_metrics(self, services: List[str] = None) -> Dict[str, Dict[str, float]]:
        """
        Fetch current metrics for all services from Prometheus.

        Args:
            services: Optional list of service names. If None, uses self._services.

        Returns:
            Dict mapping service_name -> {metric_name: value}
        """
        svc_list = services or self._services
        if not svc_list:
            svc_list = await self.discover_services_from_prometheus()
            self._services = svc_list

        metrics = {}
        for service in svc_list:
            svc_metrics = {}

            # Try multiple label formats (different systems use different labels)
            for label_key in ["service", "app", "job"]:
                svc_metrics["latency"] = await self._query_metric(
                    f'rate(http_request_duration_seconds_sum{{{label_key}="{service}"}}[1m]) / '
                    f'rate(http_request_duration_seconds_count{{{label_key}="{service}"}}[1m])'
                )
                if svc_metrics["latency"] > 0:
                    break

            svc_metrics["error_rate"] = await self._query_metric_multi_label(
                service, 'rate(http_errors_total{{{key}="{svc}"}}[1m])'
            )
            svc_metrics["cpu"] = await self._query_metric_multi_label(
                service, 'process_cpu_percent{{{key}="{svc}"}}'
            )
            svc_metrics["memory"] = await self._query_metric_multi_label(
                service, 'process_memory_mb{{{key}="{svc}"}}'
            )
            svc_metrics["request_rate"] = await self._query_metric_multi_label(
                service, 'rate(http_requests_total{{{key}="{svc}"}}[1m])'
            )

            # Fallback: try container metrics from K8s
            if all(v == 0.0 for v in svc_metrics.values()):
                svc_metrics["cpu"] = await self._query_metric(
                    f'rate(container_cpu_usage_seconds_total{{pod=~"{service}.*"}}[1m]) * 100'
                )
                svc_metrics["memory"] = await self._query_metric(
                    f'container_memory_usage_bytes{{pod=~"{service}.*"}} / 1024 / 1024'
                )

            metrics[service] = svc_metrics
        return metrics

    async def fetch_feature_matrix(self, services: List[str] = None) -> np.ndarray:
        """
        Fetch metrics and return as feature matrix for GNN.

        Returns:
            numpy array of shape [num_services, num_features]
        """
        svc_list = services or self._services
        metrics = await self.fetch_current_metrics(svc_list)
        svc_list = list(metrics.keys())
        matrix = np.zeros((len(svc_list), len(METRICS)))
        for i, svc in enumerate(svc_list):
            for j, metric in enumerate(METRICS):
                matrix[i, j] = metrics.get(svc, {}).get(metric, 0.0)
        return matrix

    async def compute_deltas(self, services: List[str] = None) -> Dict[str, Dict[str, str]]:
        """
        Compute metric deltas from baseline for LLM context.

        Returns:
            Dict mapping service -> {metric: "+XX%" or "-XX%"}
        """
        current = await self.fetch_current_metrics(services)
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

    async def _query_metric_multi_label(self, service: str, query_template: str) -> float:
        """Try querying with multiple label keys (service, app, job)."""
        for key in ["service", "app", "job"]:
            query = query_template.format(key=key, svc=service)
            val = await self._query_metric(query)
            if val > 0:
                return val
        return 0.0

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
