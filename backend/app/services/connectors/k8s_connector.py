"""
Kubernetes Connector — discovers services from any K8s cluster via kubectl.
Works with: Online Boutique, FinTech, HealthCare, any K8s deployment.
"""
from __future__ import annotations
import subprocess
import json
import logging
from typing import Dict, List, Optional
from app.services.connectors.base import BaseConnector, ConnectorResult, ServiceInfo, TopologyEdge

logger = logging.getLogger("synapse.connector.k8s")


class K8sConnector(BaseConnector):
    """Connects to any Kubernetes cluster and discovers deployments."""

    connector_type = "kubernetes"

    def __init__(self, namespace: str = "default", kubeconfig: Optional[str] = None):
        self.namespace = namespace
        self.kubeconfig = kubeconfig

    def _kubectl(self, cmd: str) -> Optional[dict]:
        full_cmd = ["kubectl"]
        if self.kubeconfig:
            full_cmd += ["--kubeconfig", self.kubeconfig]
        full_cmd += cmd.split()
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return json.loads(result.stdout)
            logger.warning(f"kubectl error: {result.stderr[:200]}")
        except Exception as e:
            logger.error(f"kubectl failed: {e}")
        return None

    def health_check(self) -> bool:
        data = self._kubectl(f"get namespace {self.namespace} -o json")
        return data is not None

    def discover(self) -> ConnectorResult:
        data = self._kubectl(f"get deployments -n {self.namespace} -o json")
        if not data:
            return ConnectorResult(
                system_name=f"k8s:{self.namespace}",
                connector_type=self.connector_type,
                services=[], edges=[],
                metrics={},
                error=f"Cannot reach K8s namespace '{self.namespace}'",
                connected=False,
            )

        services = []
        for item in data.get("items", []):
            name = item["metadata"]["name"]
            labels = item["metadata"].get("labels", {})
            replicas = item.get("status", {}).get("readyReplicas", 0) or 0
            desired = item.get("spec", {}).get("replicas", 1)
            status = "running" if replicas >= desired else ("degraded" if replicas > 0 else "down")

            # Infer type from name
            if any(x in name for x in ["gateway", "frontend", "ingress"]):
                stype = "gateway"
            elif any(x in name for x in ["db", "database", "postgres", "mysql", "mongo", "redis"]):
                stype = "infrastructure"
            elif any(x in name for x in ["cache", "redis", "memcached"]):
                stype = "infrastructure"
            else:
                stype = "service"

            services.append(ServiceInfo(
                name=name,
                label=name.replace("-", " ").replace("_", " ").title(),
                service_type=stype,
                namespace=self.namespace,
                replicas=replicas,
                status=status,
                metadata={"desired_replicas": desired, "labels": labels},
            ))

        # Build topology: gateway -> all services
        edges = []
        gateways = [s for s in services if s.service_type == "gateway"]
        non_gateways = [s for s in services if s.service_type != "gateway"]
        for gw in gateways:
            for svc in non_gateways:
                edges.append(TopologyEdge(source=gw.name, target=svc.name))
        # If no gateway, make first service connect to others
        if not gateways and len(services) > 1:
            root = services[0]
            for svc in services[1:]:
                edges.append(TopologyEdge(source=root.name, target=svc.name))

        return ConnectorResult(
            system_name=f"k8s:{self.namespace}",
            connector_type=self.connector_type,
            services=services,
            edges=edges,
            metrics={s.name: {"latency": 0.0, "error_rate": 0.0, "cpu": 0.0, "memory": 0.0, "request_rate": 0.0} for s in services},
        )

    def fetch_metrics(self, services: List[str]) -> Dict[str, Dict[str, float]]:
        # Get pod resource usage via kubectl top
        metrics = {s: {"latency": 0.0, "error_rate": 0.0, "cpu": 0.0, "memory": 0.0, "request_rate": 0.0} for s in services}
        data = self._kubectl(f"top pods -n {self.namespace} --no-headers")
        # kubectl top returns plain text not JSON, parse separately
        try:
            result = subprocess.run(
                ["kubectl", "top", "pods", "-n", self.namespace, "--no-headers"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    parts = line.split()
                    if len(parts) >= 3:
                        pod_name = parts[0]
                        cpu_str = parts[1].replace("m", "")
                        mem_str = parts[2].replace("Mi", "").replace("Ki", "")
                        for svc in services:
                            if pod_name.startswith(svc):
                                try:
                                    metrics[svc]["cpu"] = float(cpu_str) / 10.0  # millicores -> %
                                    metrics[svc]["memory"] = float(mem_str)
                                except ValueError:
                                    pass
        except Exception as e:
            logger.debug(f"kubectl top failed: {e}")
        return metrics

    def get_pod_statuses(self) -> Dict[str, str]:
        """Get real pod statuses for all services."""
        statuses = {}
        data = self._kubectl(f"get pods -n {self.namespace} -o json")
        if not data:
            return statuses
        for item in data.get("items", []):
            pod_name = item["metadata"]["name"]
            phase = item.get("status", {}).get("phase", "Unknown")
            # Match pod to deployment name (strip random suffix)
            parts = pod_name.rsplit("-", 2)
            if len(parts) >= 2:
                dep_name = "-".join(parts[:-2])
                statuses[dep_name] = phase
        return statuses
