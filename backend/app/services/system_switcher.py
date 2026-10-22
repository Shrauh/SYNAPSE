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
from typing import Dict, List, Optional, Tuple, Any

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


# ─────────────────────────────────────────────────
# Bidirectional Mappings: Active System <-> Simulator
# ─────────────────────────────────────────────────

SYSTEM_TO_SIMULATOR_MAPS: Dict[str, Dict[str, str]] = {
    "default": {
        "api-gateway": "api-gateway",
        "auth-service": "auth-service",
        "user-service": "user-service",
        "payment-service": "payment-service",
        "order-service": "order-service",
        "inventory-service": "inventory-service",
        "notification-service": "notification-service",
        "search-service": "search-service",
        "cache-service": "cache-service",
        "database": "database",
    },
    "online-boutique": {
        "frontend": "api-gateway",
        "paymentservice": "payment-service",
        "checkoutservice": "order-service",
        "productcatalogservice": "inventory-service",
        "recommendationservice": "search-service",
        "cartservice": "cache-service",
        "currencyservice": "auth-service",
        "emailservice": "notification-service",
        "redis-cart": "database",
        "shippingservice": "user-service",
        # Built-in fallbacks/aliases
        "payment-service": "payment-service",
        "order-service": "order-service",
        "inventory-service": "inventory-service",
        "search-service": "search-service",
        "auth-service": "auth-service",
        "cache-service": "cache-service",
        "notification-service": "notification-service",
        "database": "database",
        "user-service": "user-service",
        "api-gateway": "api-gateway",
    },
    "fintech": {
        "api-gateway": "api-gateway",
        "transaction-service": "payment-service",
        "fraud-detection": "auth-service",
        "account-service": "user-service",
    },
    "healthcare": {
        "patient-gateway": "api-gateway",
        "appointment-service": "order-service",
        "records-service": "database",
        "notification-service": "notification-service",
    },
}

SIMULATOR_TO_SYSTEM_MAPS: Dict[str, Dict[str, str]] = {
    "default": {
        "api-gateway": "api-gateway",
        "auth-service": "auth-service",
        "user-service": "user-service",
        "payment-service": "payment-service",
        "order-service": "order-service",
        "inventory-service": "inventory-service",
        "notification-service": "notification-service",
        "search-service": "search-service",
        "cache-service": "cache-service",
        "database": "database",
    },
    "online-boutique": {
        "api-gateway": "frontend",
        "payment-service": "paymentservice",
        "order-service": "checkoutservice",
        "inventory-service": "productcatalogservice",
        "search-service": "recommendationservice",
        "cache-service": "cartservice",
        "auth-service": "currencyservice",
        "notification-service": "emailservice",
        "database": "redis-cart",
        "user-service": "shippingservice",
    },
    "fintech": {
        "api-gateway": "api-gateway",
        "payment-service": "transaction-service",
        "order-service": "transaction-service",
        "auth-service": "fraud-detection",
        "user-service": "account-service",
        "database": "account-service",
        "inventory-service": "transaction-service",
        "search-service": "fraud-detection",
        "notification-service": "transaction-service",
        "cache-service": "account-service",
    },
    "healthcare": {
        "api-gateway": "patient-gateway",
        "order-service": "appointment-service",
        "payment-service": "appointment-service",
        "database": "records-service",
        "user-service": "records-service",
        "cache-service": "records-service",
        "auth-service": "patient-gateway",
        "notification-service": "notification-service",
        "search-service": "appointment-service",
        "inventory-service": "records-service",
    },
}


def get_system_mappings(system_name: Optional[str] = None) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Returns (forward_map, reverse_map) between the active system and simulator.
    forward_map: active_system_service -> simulator_service
    reverse_map: simulator_service -> active_system_service
    """
    sys_name = system_name or get_active_system()

    if sys_name in SYSTEM_TO_SIMULATOR_MAPS and sys_name in SIMULATOR_TO_SYSTEM_MAPS:
        return (
            dict(SYSTEM_TO_SIMULATOR_MAPS[sys_name]),
            dict(SIMULATOR_TO_SYSTEM_MAPS[sys_name]),
        )

    # Custom or dynamic topology
    active_services = get_service_names()
    from data.simulator import SERVICE_NAMES

    forward: Dict[str, str] = {}
    reverse: Dict[str, str] = {}

    if not active_services:
        for s in SERVICE_NAMES:
            forward[s] = s
            reverse[s] = s
        return forward, reverse

    for i, s in enumerate(active_services):
        sim_name = SERVICE_NAMES[i % len(SERVICE_NAMES)]
        forward[s] = sim_name
        if sim_name not in reverse:
            reverse[sim_name] = s

    for sim_name in SERVICE_NAMES:
        if sim_name not in reverse:
            reverse[sim_name] = active_services[0]

    return forward, reverse


def map_to_simulator(service_name: str, system_name: Optional[str] = None) -> str:
    """Map a service name from the active system to the simulator service name."""
    fwd, _ = get_system_mappings(system_name)
    if service_name in fwd:
        return fwd[service_name]
    from data.simulator import SERVICE_NAMES
    if service_name in SERVICE_NAMES:
        return service_name
    import difflib
    matches = difflib.get_close_matches(service_name, list(fwd.keys()), n=1)
    if matches:
        return fwd[matches[0]]
    matches_sim = difflib.get_close_matches(service_name, SERVICE_NAMES, n=1)
    if matches_sim:
        return matches_sim[0]
    return SERVICE_NAMES[3] if len(SERVICE_NAMES) > 3 else SERVICE_NAMES[0]


def map_from_simulator(simulator_service: str, system_name: Optional[str] = None) -> str:
    """Map a simulator service name back to the active system's service name."""
    _, rev = get_system_mappings(system_name)
    if simulator_service in rev:
        return rev[simulator_service]
    active_services = get_service_names()
    if simulator_service in active_services:
        return simulator_service
    import difflib
    matches = difflib.get_close_matches(simulator_service, active_services, n=1)
    if matches:
        return matches[0]
    return simulator_service


def remap_rca_result(
    result_data: Dict[str, Any],
    system_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Remap all service names in an RCA result payload back to the active system."""
    _, rev = get_system_mappings(system_name)

    def _remap(svc: str) -> str:
        return rev.get(svc, svc)

    remapped = dict(result_data)

    if "root_cause" in remapped and isinstance(remapped["root_cause"], str):
        remapped["root_cause"] = _remap(remapped["root_cause"])
    elif "root_cause_service" in remapped and isinstance(remapped["root_cause_service"], str):
        remapped["root_cause_service"] = _remap(remapped["root_cause_service"])

    if "anomaly_scores" in remapped and isinstance(remapped["anomaly_scores"], dict):
        remapped["anomaly_scores"] = {
            _remap(k): float(v) for k, v in remapped["anomaly_scores"].items()
        }

    if "affected_services" in remapped and isinstance(remapped["affected_services"], list):
        remapped["affected_services"] = [
            _remap(s) for s in remapped["affected_services"]
        ]

    if "propagation_chain" in remapped and isinstance(remapped["propagation_chain"], str):
        parts = remapped["propagation_chain"].split(" → ")
        remapped["propagation_chain"] = " → ".join(_remap(p.strip()) for p in parts)

    return remapped


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
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(broadcast_json({
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
