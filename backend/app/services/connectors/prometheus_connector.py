"""
Prometheus Connector — fetches real metrics from any Prometheus endpoint.
Works with any system that has Prometheus scraping configured.
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional
import httpx
from app.services.connectors.base import BaseConnector, ConnectorResult, ServiceInfo, TopologyEdge

logger = logging.getLogger("synapse.connector.prometheus")


class PrometheusConnector(BaseConnector):
    """Fetches real-time metrics from a Prometheus instance."""

    connector_type = "prometheus"

    def __init__(self, url: str = "http://localhost:9090", label_key: str = "service"):
        self.url = url.rstrip("/")
        self.label_key = label_key  # prometheus label used as service name

    def health_check(self) -> bool:
        try:
            r = httpx.get(f"{self.url}/api/v1/status/config", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def _query(self, promql: str) -> list:
        try:
            r = httpx.get(f"{self.url}/api/v1/query", params={"query": promql}, timeout=5.0)
            r.raise_for_status()
            return r.json().get("data", {}).get("result", [])
        except Exception as e:
            logger.debug(f"Prometheus query failed: {e}")
            return []

    def discover(self) -> ConnectorResult:
        """Discover services from active Prometheus targets."""
        try:
            r = httpx.get(f"{self.url}/api/v1/targets", timeout=5.0)
            r.raise_for_status()
            targets = r.json().get("data", {}).get("activeTargets", [])
        except Exception as e:
            return ConnectorResult(
                system_name="prometheus",
                connector_type=self.connector_type,
                services=[], edges=[],
                metrics={},
                error=str(e),
                connected=False,
            )

        seen = {}
        for t in targets:
            labels = t.get("labels", {})
            name = labels.get(self.label_key) or labels.get("app") or labels.get("job") or ""
            if not name or name in ("prometheus", "node-exporter", "kubelet"):
                continue
            health = t.get("health", "unknown")
            seen[name] = ServiceInfo(
                name=name,
                label=name.replace("-", " ").title(),
                service_type="gateway" if "gateway" in name or "frontend" in name else "service",
                status="running" if health == "up" else "degraded",
            )

        services = list(seen.values())
        # Simple star topology — refine with actual trace data if available
        gateways = [s for s in services if s.service_type == "gateway"]
        edges = []
        if gateways:
            for svc in services:
                if svc.name != gateways[0].name:
                    edges.append(TopologyEdge(source=gateways[0].name, target=svc.name))

        return ConnectorResult(
            system_name="prometheus",
            connector_type=self.connector_type,
            services=services,
            edges=edges,
            metrics={s.name: self._fetch_one(s.name) for s in services},
        )

    def fetch_metrics(self, services: List[str]) -> Dict[str, Dict[str, float]]:
        return {svc: self._fetch_one(svc) for svc in services}

    def _fetch_one(self, service: str) -> Dict[str, float]:
        def q(promql: str) -> float:
            results = self._query(promql)
            for r in results:
                try:
                    return float(r["value"][1])
                except Exception:
                    pass
            return 0.0

        return {
            "latency": q(f'rate(http_request_duration_seconds_sum{{{self.label_key}="{service}"}}[1m]) / rate(http_request_duration_seconds_count{{{self.label_key}="{service}"}}[1m])'),
            "error_rate": q(f'rate(http_errors_total{{{self.label_key}="{service}"}}[1m])'),
            "cpu": q(f'rate(container_cpu_usage_seconds_total{{pod=~"{service}.*"}}[1m]) * 100'),
            "memory": q(f'container_memory_usage_bytes{{pod=~"{service}.*"}} / 1024 / 1024'),
            "request_rate": q(f'rate(http_requests_total{{{self.label_key}="{service}"}}[1m])'),
        }
