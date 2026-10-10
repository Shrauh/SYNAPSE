"""
Push Connector — any external system can PUSH metrics to SYNAPSE via HTTP.
Useful for: Docker Compose systems, bare-metal, non-K8s deployments.
"""
from __future__ import annotations
import logging
from typing import Dict, List, Any
from datetime import datetime, timezone
from app.services.connectors.base import BaseConnector, ConnectorResult, ServiceInfo, TopologyEdge

logger = logging.getLogger("synapse.connector.push")

# In-memory store for pushed metrics
_pushed_metrics: Dict[str, Dict[str, float]] = {}
_pushed_topology: Dict[str, Any] = {"services": [], "edges": []}
_last_push: Dict[str, str] = {}


class PushConnector(BaseConnector):
    """
    External systems push metrics to SYNAPSE via POST /system/push/metrics.
    No Prometheus or K8s required — works with anything.
    """
    connector_type = "push"

    def health_check(self) -> bool:
        return len(_pushed_metrics) > 0

    def discover(self) -> ConnectorResult:
        services = [
            ServiceInfo(
                name=name,
                label=name.replace("-", " ").title(),
                service_type="service",
                status="running",
            )
            for name in _pushed_metrics
        ]
        # Use pushed topology if available
        edges = [
            TopologyEdge(source=e["source"], target=e["target"])
            for e in _pushed_topology.get("edges", [])
        ]
        return ConnectorResult(
            system_name="push",
            connector_type=self.connector_type,
            services=services,
            edges=edges,
            metrics=dict(_pushed_metrics),
        )

    def fetch_metrics(self, services: List[str]) -> Dict[str, Dict[str, float]]:
        return {svc: _pushed_metrics.get(svc, {"latency": 0.0, "error_rate": 0.0, "cpu": 0.0, "memory": 0.0, "request_rate": 0.0}) for svc in services}

    @staticmethod
    def receive_push(service: str, metrics: Dict[str, float]) -> None:
        """Called by the API when a service pushes metrics."""
        _pushed_metrics[service] = metrics
        _last_push[service] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Received push from '{service}': {list(metrics.keys())}")

    @staticmethod
    def set_topology(services: List[str], edges: List[Dict]) -> None:
        """Set the topology for pushed services."""
        _pushed_topology["services"] = services
        _pushed_topology["edges"] = edges

    @staticmethod
    def get_push_status() -> Dict:
        return {
            "services_pushing": list(_pushed_metrics.keys()),
            "last_push_times": dict(_last_push),
            "total_services": len(_pushed_metrics),
        }
