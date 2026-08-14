"""
SYNAPSE Kubernetes Executor — Auto-Remediation Action Executor.

Executes remediation actions against a Kubernetes cluster using the
official Python kubernetes client. In local development mode (K8s
not available), all actions are simulated and logged.

Safety rules:
  - All executions are logged with full audit trail
  - CIRCUIT_BREAK and DRAIN_TRAFFIC always require human approval
  - CQL confidence must exceed action threshold before auto-execution
  - Dry-run mode available for testing without cluster changes

Usage:
    from app.ai_module.remediation.k8s_executor import k8s_executor
    result = await k8s_executor.execute(action, service, confidence)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.ai_module.remediation.action_space import RemediationAction
from app.config import settings

logger = logging.getLogger(__name__)


class KubernetesExecutor:
    """Executes Kubernetes remediation actions.

    Supports two modes:
      - LIVE mode: executes actual kubectl commands via kubernetes client
      - SIMULATION mode: logs actions without modifying cluster state
    """

    def __init__(self) -> None:
        self._k8s_available = False
        self._k8s_client = None
        self._apps_v1 = None
        self._core_v1 = None
        self._namespace = settings.k8s_namespace
        self._execution_log: list = []

    def _try_init_k8s(self) -> bool:
        """Attempt to initialize Kubernetes client."""
        if self._k8s_available:
            return True
        try:
            from kubernetes import client, config as k8s_config
            try:
                k8s_config.load_incluster_config()  # Running inside cluster
            except Exception:
                k8s_config.load_kube_config()       # Local kubeconfig
            self._k8s_client = client.ApiClient()
            self._apps_v1 = client.AppsV1Api()
            self._core_v1 = client.CoreV1Api()
            self._k8s_available = True
            logger.info("[K8s] Kubernetes client initialized successfully")
            return True
        except Exception as e:
            logger.info(f"[K8s] Kubernetes not available ({e}). Running in simulation mode.")
            return False

    async def execute(
        self,
        action: RemediationAction,
        service: str,
        confidence: float,
        dry_run: bool = False,
        node: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a remediation action.

        Args:
            action: The RemediationAction to execute.
            service: Target service name.
            confidence: CQL confidence score.
            dry_run: If True, log only — don't change cluster state.
            node: Target node name (for DRAIN_TRAFFIC).

        Returns:
            Execution result dict with status, command, timestamp, etc.
        """
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        result: Dict[str, Any] = {
            "execution_id": execution_id,
            "action_id": action.action_id,
            "service": service,
            "confidence": confidence,
            "timestamp": timestamp,
            "status": "pending",
            "mode": "dry_run" if dry_run else ("live" if settings.k8s_enabled else "simulation"),
            "command": action.command_template.format(
                service=service,
                namespace=self._namespace,
                node=node or service,
            ),
            "message": "",
        }

        if dry_run:
            result["status"] = "dry_run"
            result["message"] = f"[DRY RUN] Would execute: {result['command']}"
            logger.info(f"[K8s] DRY RUN: {result['command']}")
            self._execution_log.append(result)
            return result

        # Check confidence threshold
        if confidence < action.auto_execute_threshold and not action.always_require_approval:
            result["status"] = "below_threshold"
            result["message"] = (
                f"Confidence {confidence:.2f} < threshold {action.auto_execute_threshold}. "
                f"Human approval required."
            )
            self._execution_log.append(result)
            return result

        if action.always_require_approval:
            result["status"] = "requires_approval"
            result["message"] = f"Action {action.action_id} requires human approval."
            self._execution_log.append(result)
            return result

        # Execute
        if settings.k8s_enabled and self._try_init_k8s():
            result = await self._execute_live(action, service, node, result)
        else:
            result = await self._execute_simulation(action, service, node, result)

        self._execution_log.append(result)
        return result

    async def _execute_live(
        self,
        action: RemediationAction,
        service: str,
        node: Optional[str],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action against real Kubernetes cluster."""
        loop = asyncio.get_event_loop()

        try:
            if action.action_id == "SCALE_UP":
                await loop.run_in_executor(None, self._scale_up, service)
            elif action.action_id == "RESTART_POD":
                await loop.run_in_executor(None, self._restart_pod, service)
            elif action.action_id == "ROLLBACK":
                await loop.run_in_executor(None, self._rollback, service)
            elif action.action_id == "INCREASE_POOL":
                await loop.run_in_executor(None, self._increase_pool, service)
            else:
                result["status"] = "skipped"
                result["message"] = f"{action.action_id} requires manual execution"
                return result

            result["status"] = "success"
            result["message"] = f"Successfully executed {action.action_id} on {service}"
            logger.info(f"[K8s] LIVE: {action.action_id} on {service} — SUCCESS")

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Execution failed: {str(e)}"
            logger.error(f"[K8s] LIVE: {action.action_id} on {service} — FAILED: {e}")

        return result

    def _scale_up(self, service: str) -> None:
        """Scale deployment to 3 replicas."""
        body = {"spec": {"replicas": 3}}
        self._apps_v1.patch_namespaced_deployment_scale(
            name=service, namespace=self._namespace, body=body
        )

    def _restart_pod(self, service: str) -> None:
        """Rolling restart via annotation."""
        import time
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": str(time.time())
                        }
                    }
                }
            }
        }
        self._apps_v1.patch_namespaced_deployment(
            name=service, namespace=self._namespace, body=body
        )

    def _rollback(self, service: str) -> None:
        """Rollback to previous revision."""
        # kubectl rollout undo equivalent
        deployment = self._apps_v1.read_namespaced_deployment(
            name=service, namespace=self._namespace
        )
        revision = deployment.metadata.annotations.get(
            "deployment.kubernetes.io/revision", "1"
        )
        logger.info(f"[K8s] Rolling back {service} from revision {revision}")
        # Actual rollback via rollout history API
        self._apps_v1.patch_namespaced_deployment(
            name=service,
            namespace=self._namespace,
            body={"spec": {"rollbackTo": {"revision": 0}}},
        )

    def _increase_pool(self, service: str) -> None:
        """Patch ConfigMap to increase DB connection pool."""
        from kubernetes import client
        body = client.V1ConfigMap(
            data={"db_pool_size": "50", "db_max_overflow": "20"}
        )
        try:
            self._core_v1.patch_namespaced_config_map(
                name=f"{service}-config",
                namespace=self._namespace,
                body=body,
            )
        except Exception:
            # ConfigMap may not exist — create it
            body.metadata = client.V1ObjectMeta(name=f"{service}-config")
            self._core_v1.create_namespaced_config_map(
                namespace=self._namespace, body=body
            )

    async def _execute_simulation(
        self,
        action: RemediationAction,
        service: str,
        node: Optional[str],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate action execution (no real K8s)."""
        # Simulate execution delay
        await asyncio.sleep(0.5)

        logger.info(
            f"[K8s] SIMULATION: {action.action_id} on {service} "
            f"(~{action.estimated_time_sec}s in production)"
        )

        result["status"] = "simulated"
        result["message"] = (
            f"[SIMULATION] {action.name} on '{service}' — "
            f"would run: {result['command']}"
        )
        return result

    async def approve_and_execute(
        self,
        execution_id: str,
        action: RemediationAction,
        service: str,
        confidence: float,
    ) -> Dict[str, Any]:
        """Execute a previously held action after human approval."""
        logger.info(f"[K8s] Human approved: {execution_id}")
        # Remove approval gate — force execute
        original_threshold = action.auto_execute_threshold
        action.auto_execute_threshold = 0.0  # Bypass threshold
        result = await self.execute(action, service, confidence)
        action.auto_execute_threshold = original_threshold
        result["approved_by_human"] = True
        return result

    def get_execution_log(self, limit: int = 50) -> list:
        """Return recent execution records."""
        return self._execution_log[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Return executor status."""
        return {
            "k8s_enabled": settings.k8s_enabled,
            "k8s_available": self._k8s_available,
            "namespace": self._namespace,
            "total_executions": len(self._execution_log),
            "mode": "live" if (settings.k8s_enabled and self._k8s_available) else "simulation",
        }


# Module-level singleton
k8s_executor = KubernetesExecutor()
