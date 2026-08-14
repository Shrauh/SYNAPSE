"""
SYNAPSE Chaos Injector — Fault Injection Controller.

In local mode: calls the MicroserviceSimulator directly to create
fault scenarios without any real infrastructure.

In K8s mode (with Chaos Mesh): creates ChaosEngine CRDs via K8s API
to inject real faults into running microservices.

Usage:
    from data.chaos_injector import chaos_injector
    result = await chaos_injector.inject(fault_type="cpu_stress", service="payment")
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class ChaosInjector:
    """Fault injection controller supporting local simulation and Chaos Mesh.

    Supports all 10 fault types from the project spec:
      cpu_stress, db_exhaustion, dns_failure, oom_kill,
      network_latency, pod_crash, cascade_failure, retry_storm,
      memory_leak, config_error
    """

    FAULT_SEVERITY_MAP = {
        "low": 2.0,
        "medium": 5.0,
        "high": 7.0,
        "critical": 9.0,
    }

    def __init__(self) -> None:
        self._injection_log: List[Dict[str, Any]] = []

    async def inject(
        self,
        fault_type: str,
        service: str,
        severity: str = "medium",
        duration_minutes: int = 5,
        cascade: bool = False,
    ) -> Dict[str, Any]:
        """Inject a fault into the target service.

        Args:
            fault_type: Type of fault to inject.
            service: Target microservice name.
            severity: low | medium | high | critical
            duration_minutes: How long the fault lasts.
            cascade: If True, fault propagates to dependent services.

        Returns:
            Dict with injection result and simulation data.
        """
        injection_id = f"chaos_{uuid.uuid4().hex[:8]}"
        severity_num = self.FAULT_SEVERITY_MAP.get(severity, 5.0)

        logger.info(
            f"[Chaos] Injecting {fault_type} into {service} "
            f"(severity={severity}, duration={duration_minutes}min)"
        )

        # Run via simulator (local mode)
        result = await self._simulate_fault(
            injection_id=injection_id,
            fault_type=fault_type,
            service=service,
            severity_num=severity_num,
            duration_minutes=duration_minutes,
        )

        # Also try Chaos Mesh if K8s enabled
        if settings.k8s_enabled:
            try:
                k8s_result = await self._inject_chaos_mesh(
                    fault_type=fault_type,
                    service=service,
                    duration_minutes=duration_minutes,
                )
                result["chaos_mesh"] = k8s_result
            except Exception as e:
                logger.warning(f"[Chaos] Chaos Mesh injection failed: {e}")
                result["chaos_mesh"] = {"status": "unavailable", "error": str(e)}

        record = {
            "injection_id": injection_id,
            "fault_type": fault_type,
            "service": service,
            "severity": severity,
            "duration_minutes": duration_minutes,
            "injected_at": datetime.now(timezone.utc).isoformat(),
            "result": result,
        }
        self._injection_log.append(record)

        return record

    async def _simulate_fault(
        self,
        injection_id: str,
        fault_type: str,
        service: str,
        severity_num: float,
        duration_minutes: int,
    ) -> Dict[str, Any]:
        """Run fault via the MicroserviceSimulator."""
        try:
            from data.simulator import MicroserviceSimulator
            sim = MicroserviceSimulator(seed=None)  # Random seed for variety
            sim_result = sim.simulate_incident(
                root_cause=service,
                fault_type=fault_type,
                severity=severity_num,
                num_steps=max(30, duration_minutes * 2),
            )

            return {
                "mode": "simulation",
                "status": "injected",
                "metrics_rows": len(sim_result.metrics_df),
                "anomalous_services": list(
                    sim_result.metrics_df[
                        sim_result.metrics_df["error_rate"] > 0.2
                    ]["service"].unique()
                ),
                "sim_data": sim_result,  # Passed to RCA pipeline
            }
        except Exception as e:
            logger.error(f"[Chaos] Simulation failed: {e}")
            return {"mode": "simulation", "status": "error", "error": str(e)}

    async def _inject_chaos_mesh(
        self,
        fault_type: str,
        service: str,
        duration_minutes: int,
    ) -> Dict[str, Any]:
        """Create a Chaos Mesh ChaosEngine CRD."""
        duration_str = f"{duration_minutes}m"

        # Map fault types to Chaos Mesh experiment types
        chaos_map = {
            "cpu_stress":       ("StressChaos", {"stressors": {"cpu": {"workers": 4}}}),
            "memory_leak":      ("StressChaos", {"stressors": {"memory": {"size": "512MB"}}}),
            "oom_kill":         ("StressChaos", {"stressors": {"memory": {"size": "2GB", "oom_score_adj": 1000}}}),
            "network_latency":  ("NetworkChaos", {"action": "delay", "delay": {"latency": "2500ms"}}),
            "dns_failure":      ("DNSChaos", {"action": "error"}),
            "pod_crash":        ("PodChaos", {"action": "pod-kill"}),
        }

        chaos_type, chaos_spec = chaos_map.get(
            fault_type, ("PodChaos", {"action": "pod-failure"})
        )

        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": chaos_type,
            "metadata": {
                "name": f"synapse-chaos-{uuid.uuid4().hex[:6]}",
                "namespace": settings.k8s_namespace,
            },
            "spec": {
                "mode": "one",
                "selector": {
                    "namespaces": [settings.k8s_namespace],
                    "labelSelectors": {"app": service},
                },
                "duration": duration_str,
                **chaos_spec,
            }
        }

        try:
            from kubernetes import client, config as k8s_config
            try:
                k8s_config.load_incluster_config()
            except Exception:
                k8s_config.load_kube_config()

            custom_api = client.CustomObjectsApi()
            custom_api.create_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace=settings.k8s_namespace,
                plural=chaos_type.lower() + "s",
                body=manifest,
            )
            return {"status": "created", "kind": chaos_type, "manifest": manifest}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_injection_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent injection history."""
        return self._injection_log[-limit:]

    def get_available_faults(self) -> List[Dict[str, str]]:
        """Return all supported fault types with descriptions."""
        return [
            {"id": "cpu_stress",      "name": "CPU Stress",       "description": "CPU > 90%, latency 5-10x baseline"},
            {"id": "db_exhaustion",   "name": "DB Exhaustion",     "description": "error_rate 100%, latency > 4000ms"},
            {"id": "dns_failure",     "name": "DNS Failure",       "description": "error_rate 100%, latency near 0ms"},
            {"id": "oom_kill",        "name": "OOM Kill",          "description": "memory > 95%, service restarts"},
            {"id": "network_latency", "name": "Network Latency",   "description": "latency > 2500ms, error_rate 20-50%"},
            {"id": "pod_crash",       "name": "Pod Crash",         "description": "availability 0%, throughput 0"},
            {"id": "cascade_failure", "name": "Cascade Failure",   "description": "errors spread across graph"},
            {"id": "retry_storm",     "name": "Retry Storm",       "description": "throughput 10x, CPU 95%"},
            {"id": "memory_leak",     "name": "Memory Leak",       "description": "memory grows steadily over hours"},
            {"id": "config_error",    "name": "Config Error",      "description": "error_rate 100% after deploy"},
        ]


# Module-level singleton
chaos_injector = ChaosInjector()
