"""
System Switch API — Switch SYNAPSE to monitor any microservice system live.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.connectors.registry import connector_registry
from app.services.connectors.push_connector import PushConnector

from app.services.system_switcher import (
    switch_system,
    get_active_system,
    get_active_topology,
    get_service_names,
    KNOWN_TOPOLOGIES,
    discover_from_k8s,
)

router = APIRouter(prefix="/system", tags=["System Switch"])


class SwitchRequest(BaseModel):
    system: str  # 'default' | 'online-boutique' | 'fintech' | 'healthcare' | 'custom'
    namespace: str = "default"  # used only for 'custom'


@router.get("/active")
def get_active() -> Dict[str, Any]:
    """Get currently active monitoring system."""
    topo = get_active_topology()
    return {
        "system": get_active_system(),
        "label": topo["label"] if topo else "Unknown",
        "services": get_service_names(),
        "service_count": len(get_service_names()),
    }


@router.get("/available")
def list_available() -> Dict[str, Any]:
    """List all available systems to switch to."""
    return {
        "available": [
            {
                "id": key,
                "label": val["label"],
                "service_count": len(val["services"]),
                "services": [s[0] for s in val["services"]],
            }
            for key, val in KNOWN_TOPOLOGIES.items()
        ],
        "custom": {
            "id": "custom",
            "label": "Auto-discover from any K8s namespace",
            "usage": "POST /system/switch with {\"system\": \"custom\", \"namespace\": \"your-namespace\"}",
        },
    }


@router.post("/switch")
def switch(req: SwitchRequest) -> Dict[str, Any]:
    """
    Switch SYNAPSE to monitor a different microservice system.

    - system='online-boutique' → Google Online Boutique (10 services)
    - system='fintech'         → FinTech Stack (4 services)
    - system='healthcare'      → HealthCare Stack (4 services)
    - system='custom'          → Auto-discover from K8s namespace
    - system='default'         → SYNAPSE simulator services

    Takes effect immediately — no restart needed.
    """
    result = switch_system(req.system, req.namespace)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/discover")
def discover(namespace: str = "default") -> Dict[str, Any]:
    """Auto-discover services from any K8s namespace."""
    topo = discover_from_k8s(namespace)
    if not topo.get("services"):
        raise HTTPException(
            status_code=404,
            detail=f"No deployments found in namespace '{namespace}'. Is kubectl configured?"
        )
    return {
        "namespace": namespace,
        "discovered_services": [s[0] for s in topo["services"]],
        "service_count": len(topo["services"]),
        "inferred_edges": topo["edges"],
        "tip": "Use POST /system/switch with system='custom' to activate this topology",
    }

class PushMetricsRequest(BaseModel):
    service: str
    metrics: Dict[str, float]  # {latency, error_rate, cpu, memory, request_rate}

class RegisterTopologyRequest(BaseModel):
    services: List[str]
    edges: List[Dict[str, str]]  # [{"source": "a", "target": "b"}]

class AddConnectorRequest(BaseModel):
    name: str
    type: str  # 'k8s' | 'prometheus'
    # K8s options
    namespace: Optional[str] = "default"
    kubeconfig: Optional[str] = None
    # Prometheus options
    url: Optional[str] = None
    label_key: Optional[str] = "service"

@router.get("/connectors")
def list_connectors():
    """List all registered connectors and their status."""
    return connector_registry.list_connectors()

@router.post("/connectors/add")
def add_connector(req: AddConnectorRequest):
    """Register a new connector (K8s namespace or Prometheus endpoint)."""
    if req.type == "k8s":
        connector_registry.add_k8s_connector(req.name, req.namespace, req.kubeconfig)
    elif req.type == "prometheus":
        connector_registry.add_prometheus_connector(req.name, req.url, req.label_key)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown connector type: {req.type}")
    return {"registered": req.name, "type": req.type, "message": f"Connector '{req.name}' added. Use POST /system/connectors/{req.name}/activate to use it."}

@router.post("/connectors/{name}/activate")
def activate_connector(name: str):
    """Set a connector as active — SYNAPSE will use it for monitoring."""
    result = connector_registry.activate(name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Connector '{name}' not found.")
    discovered = connector_registry.discover(name)
    if discovered and not discovered.error:
        # Push topology into system switcher
        services = [(s.name, s.label, s.service_type) for s in discovered.services]
        edges = [(e.source, e.target) for e in discovered.edges]
        from app.services.system_switcher import _apply_topology_to_graph_builder
        _apply_topology_to_graph_builder({"label": discovered.system_name, "services": services, "edges": edges})
    return {
        "activated": name,
        "discovered_services": [s.name for s in (discovered.services if discovered else [])],
        "message": f"Connector '{name}' is now active."
    }

@router.post("/connectors/{name}/discover")
def connector_discover(name: str):
    """Run discovery on a specific connector."""
    result = connector_registry.discover(name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Connector '{name}' not found.")
    return {
        "connector": name,
        "system": result.system_name,
        "connected": result.connected,
        "services": [{"name": s.name, "type": s.service_type, "status": s.status} for s in result.services],
        "edges": [{"source": e.source, "target": e.target} for e in result.edges],
        "error": result.error,
    }

@router.post("/push/metrics")
def push_metrics(req: PushMetricsRequest):
    """
    Push metrics from any external service to SYNAPSE.
    No K8s or Prometheus needed — works with anything.
    
    Example body:
    {"service": "my-api", "metrics": {"latency": 0.5, "error_rate": 0.02, "cpu": 45.0, "memory": 512.0, "request_rate": 100.0}}
    """
    PushConnector.receive_push(req.service, req.metrics)
    return {"received": True, "service": req.service}

@router.post("/push/topology")
def push_topology(req: RegisterTopologyRequest):
    """Register the topology for pushed services."""
    PushConnector.set_topology(req.services, req.edges)
    return {"registered": True, "services": req.services, "edges": req.edges}

@router.get("/push/status")
def push_status():
    """Show which services are actively pushing metrics."""
    return PushConnector.get_push_status()
