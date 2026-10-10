"""
Connector Registry — manages active connectors and routes data to SYNAPSE.
"""
from __future__ import annotations
import logging
from typing import Dict, Optional, Any
from app.services.connectors.base import BaseConnector, ConnectorResult
from app.services.connectors.k8s_connector import K8sConnector
from app.services.connectors.prometheus_connector import PrometheusConnector
from app.services.connectors.push_connector import PushConnector

logger = logging.getLogger("synapse.connector.registry")


class ConnectorRegistry:
    """Central registry for all active connectors."""

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._active_connector: Optional[str] = None
        # Register defaults
        self.register("k8s", K8sConnector(namespace="default"))
        self.register("prometheus", PrometheusConnector())
        self.register("push", PushConnector())

    def register(self, name: str, connector: BaseConnector) -> None:
        self._connectors[name] = connector
        logger.info(f"Registered connector: {name} ({connector.connector_type})")

    def activate(self, name: str) -> bool:
        if name not in self._connectors:
            return False
        self._active_connector = name
        logger.info(f"Activated connector: {name}")
        return True

    def get_active(self) -> Optional[BaseConnector]:
        if self._active_connector:
            return self._connectors.get(self._active_connector)
        return None

    def discover(self, connector_name: Optional[str] = None) -> Optional[ConnectorResult]:
        name = connector_name or self._active_connector
        if not name or name not in self._connectors:
            return None
        return self._connectors[name].discover()

    def list_connectors(self) -> Dict[str, Any]:
        return {
            name: {
                "type": c.connector_type,
                "active": name == self._active_connector,
                "connected": c.health_check(),
            }
            for name, c in self._connectors.items()
        }

    def add_k8s_connector(self, name: str, namespace: str, kubeconfig: Optional[str] = None) -> None:
        self.register(name, K8sConnector(namespace=namespace, kubeconfig=kubeconfig))

    def add_prometheus_connector(self, name: str, url: str, label_key: str = "service") -> None:
        self.register(name, PrometheusConnector(url=url, label_key=label_key))


# Singleton
connector_registry = ConnectorRegistry()
