"""
Base connector interface — all system connectors implement this.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class ServiceInfo:
    """Info about a discovered service."""
    name: str
    label: str
    service_type: str  # 'gateway' | 'service' | 'infrastructure' | 'database'
    namespace: str = "default"
    replicas: int = 1
    status: str = "unknown"  # 'running' | 'degraded' | 'down'
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TopologyEdge:
    """A dependency edge between two services."""
    source: str
    target: str
    call_type: str = "http"  # 'http' | 'grpc' | 'tcp' | 'async'
    weight: float = 1.0


@dataclass
class ConnectorResult:
    """Result of a connector discovery or metrics fetch."""
    system_name: str
    connector_type: str
    services: List[ServiceInfo]
    edges: List[TopologyEdge]
    metrics: Dict[str, Dict[str, float]]  # service -> {metric: value}
    error: Optional[str] = None
    connected: bool = True


class BaseConnector(ABC):
    """Abstract base for all system connectors."""

    connector_type: str = "base"

    @abstractmethod
    def discover(self) -> ConnectorResult:
        """Discover services and topology from the target system."""
        ...

    @abstractmethod
    def fetch_metrics(self, services: List[str]) -> Dict[str, Dict[str, float]]:
        """Fetch current metrics for the given services."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the connector can reach the target system."""
        ...

    def get_info(self) -> Dict[str, Any]:
        """Return connector metadata."""
        return {
            "type": self.connector_type,
            "connected": self.health_check(),
        }
