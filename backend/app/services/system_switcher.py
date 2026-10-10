"""
SYNAPSE System Switcher — Dynamic Multi-System Support.

Allows SYNAPSE to monitor ANY Kubernetes deployment, not just
the default 10-service topology. Switch between systems live
without restarting the backend.

Supported systems:
  - default     : SYNAPSE simulator services (10 services)
  - online-boutique : Google Online Boutique (auto-discovered)
  - fintech     : FinTech demo stack (4 services)
  - healthcare  : HealthCare demo stack (4 services)
  - custom      : Any K8s namespace (auto-discovered via kubectl)
"""

from __future__ import annotations

import logging
import subprocess
import json
from typing import Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger("synapse.switcher")

# ─────────────────────────────────────────────────
# Known topology profiles (edges = dependencies)
# ─────────────────────────────────────────────────

KNOWN_TOPOLOGIES: Dict[str, Dict] = {
    "default": {
        "label": "SYNAPSE Default (Simulator)",
        "services": [
            ("api-gateway", "API Gateway", "gateway"),
            ("auth-service", "Auth Service", "service"),
            ("user-service", "User Service", "service"),
            ("payment-service", "Payment Service", "service"),
            ("order-service", "Order Service", "service"),
            ("inventory-service", "Inventory Service", "service"),
            ("notification-service", "Notification Service", "service"),
            ("search-service", "Search Service", "service"),
            ("cache-service", "Cache Service", "infrastructure"),
            ("database", "Database", "infrastructure"),
        ],
        "edges": [
            ("api-gateway", "auth-service"),
            ("api-gateway", "user-service"),
            ("api-gateway", "order-service"),
            ("api-gateway", "search-service"),
            ("auth-service", "database"),
            ("auth-service", "cache-service"),
            ("user-service", "database"),
            ("order-service", "payment-service"),
            ("order-service", "inventory-service"),
            ("order-service", "database"),
            ("payment-service", "database"),
            ("payment-service", "notification-service"),
            ("inventory-service", "database"),
            ("inventory-service", "cache-service"),
            ("notification-service", "cache-service"),
        ],
    },
    "online-boutique": {
        "label": "Google Online Boutique (E-Commerce)",
        "services": [
            ("frontend", "Frontend", "gateway"),
            ("checkoutservice", "Checkout Service", "service"),
            ("productcatalogservice", "Product Catalog", "service"),
            ("cartservice", "Cart Service", "service"),
            ("currencyservice", "Currency Service", "service"),
            ("paymentservice", "Payment Service", "service"),
            ("shippingservice", "Shipping Service", "service"),
            ("emailservice", "Email Service", "service"),
            ("recommendationservice", "Recommendation Service", "service"),
            ("redis-cart", "Redis Cache", "infrastructure"),
        ],
        "edges": [
            ("frontend", "checkoutservice"),
            ("frontend", "productcatalogservice"),
            ("frontend", "cartservice"),
            ("frontend", "currencyservice"),
            ("frontend", "shippingservice"),
            ("frontend", "recommendationservice"),
            ("checkoutservice", "productcatalogservice"),
            ("checkoutservice", "cartservice"),
            ("checkoutservice", "currencyservice"),
            ("checkoutservice", "paymentservice"),
            ("checkoutservice", "shippingservice"),
            ("checkoutservice", "emailservice"),
            ("cartservice", "redis-cart"),
            ("recommendationservice", "productcatalogservice"),
        ],
    },
    "fintech": {
        "label": "FinTech Stack (Banking)",
        "services": [
            ("api-gateway", "API Gateway", "gateway"),
            ("transaction-service", "Transaction Service", "service"),
            ("fraud-detection", "Fraud Detection", "service"),
            ("account-service", "Account Service", "service"),
        ],
        "edges": [
            ("api-gateway", "transaction-service"),
            ("api-gateway", "account-service"),
            ("transaction-service", "fraud-detection"),
        ],
    },
    "healthcare": {
        "label": "HealthCare Stack (Medical)",
        "services": [
            ("patient-gateway", "Patient Gateway", "gateway"),
            ("appointment-service", "Appointment Service", "service"),
            ("records-service", "Records Service", "service"),
            ("notification-service", "Notification Service", "service"),
        ],
        "edges": [
            ("patient-gateway", "appointment-service"),
            ("appointment-service", "records-service"),
            ("appointment-service", "notification-service"),
        ],
    },
}

# ─────────────────────────────────────────────────
# Active system state (in-memory)
# ─────────────────────────────────────────────────

_active_system: str = "default"
_active_topology: Optional[Dict] = None


def get_active_system() -> str:
    return _active_system


def get_active_topology() -> Optional[Dict]:
    return _active_topology or KNOWN_TOPOLOGIES.get(_active_system)


def get_service_names() -> List[str]:
    topo = get_active_topology()
    if not topo:
        return []
    return [s[0] for s in topo["services"]]


def _kubectl(cmd: str):
    """Run kubectl and return parsed JSON output."""
    try:
        result = subprocess.run(
            ["kubectl"] + cmd.split(),
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"kubectl failed: {e}")
    return None


def discover_from_k8s(namespace: str = "default") -> Dict:
    """Auto-discover services from any K8s namespace."""
    data = _kubectl(f"get deployments -n {namespace} -o json")
    if not data:
        return {}

    services = []
    for item in data.get("items", []):
        name = item["metadata"]["name"]
        labels = item["metadata"].get("labels", {})
        stype = "gateway" if "gateway" in name or "frontend" in name else "service"
        label = name.replace("-", " ").title()
        services.append((name, label, stype))

    # Build flat topology (no edges — fully connected discovery)
    edges = []
    if len(services) >= 2:
        # Gateway/frontend connects to all others
        gateway = next((s[0] for s in services if s[2] == "gateway"), services[0][0])
        for svc in services:
            if svc[0] != gateway:
                edges.append((gateway, svc[0]))

    return {
        "label": f"Auto-discovered: {namespace}",
        "services": services,
        "edges": edges,
    }


def switch_system(system_name: str, namespace: str = "default") -> Dict:
    """
    Switch SYNAPSE to monitor a different system.

    Args:
        system_name: One of 'default', 'online-boutique', 'fintech',
                     'healthcare', or 'custom' (auto-discover from K8s).
        namespace: K8s namespace for custom discovery.

    Returns:
        Dict with new system info and service list.
    """
    global _active_system, _active_topology

    if system_name == "custom":
        topo = discover_from_k8s(namespace)
        if not topo.get("services"):
            return {"error": f"No deployments found in namespace '{namespace}'"}
        _active_topology = topo
        _active_system = "custom"
    elif system_name in KNOWN_TOPOLOGIES:
        _active_topology = KNOWN_TOPOLOGIES[system_name]
        _active_system = system_name
    else:
        return {"error": f"Unknown system '{system_name}'. Available: {list(KNOWN_TOPOLOGIES.keys())} + 'custom'"}

    # Rebuild graph_builder with new topology
    _apply_topology_to_graph_builder(_active_topology)

    logger.info(f"Switched to system: {_active_system} — {len(_active_topology['services'])} services")

    try:
        from app.api.ws import broadcast_json
        import asyncio
        from app.services.graph_builder import graph_builder
        asyncio.create_task(broadcast_json({
            "type": "system_switched",
            "system": system_name,
            "services": list(graph_builder.service_names)
        }))
    except Exception:
        pass

    return {
        "system": _active_system,
        "label": _active_topology["label"],
        "services": [s[0] for s in _active_topology["services"]],
        "service_count": len(_active_topology["services"]),
        "edges": _active_topology["edges"],
        "message": f"SYNAPSE is now monitoring '{_active_topology['label']}'",
    }


def _apply_topology_to_graph_builder(topology: Dict) -> None:
    """Push the new topology into the live graph_builder singleton."""
    try:
        from app.services.graph_builder import graph_builder
        graph_builder._graph.clear()
        graph_builder._service_info.clear()
        graph_builder._node_metrics.clear()
        graph_builder._anomaly_scores.clear()

        for sid, label, stype in topology["services"]:
            graph_builder._graph.add_node(sid)
            graph_builder._service_info[sid] = {"label": label, "type": stype}
            graph_builder._node_metrics[sid] = {
                "latency": 0.0, "error_rate": 0.0,
                "cpu": 0.0, "memory": 0.0, "request_rate": 0.0,
            }
            graph_builder._anomaly_scores[sid] = 0.0

        for src, tgt in topology["edges"]:
            graph_builder._graph.add_edge(src, tgt, weight=1.0)

        graph_builder._initialized = True
        logger.info(f"Graph builder updated: {len(topology['services'])} nodes, {len(topology['edges'])} edges")
    except Exception as e:
        logger.error(f"Failed to update graph builder: {e}")
