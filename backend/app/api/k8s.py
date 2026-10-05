from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.services.k8s_discovery import k8s_discovery
from app.services.recovery_executor import recovery_executor
from app.ai_module.rl.recovery_engine import RecoveryAction, ActionType

router = APIRouter(prefix="/k8s", tags=["kubernetes"])

@router.get("/services")
def list_services():
    return k8s_discovery.discover_services()

@router.get("/topology")
def get_topology():
    return k8s_discovery.discover_topology()

@router.get("/pods")
def get_pods():
    services = k8s_discovery.discover_services()
    result = {}
    for svc in services:
        result[svc] = k8s_discovery.get_pod_status(svc)
    return result

@router.post("/recover/{service}")
def execute_recovery(service: str, dry_run: bool = True):
    action = RecoveryAction(
        action_type=ActionType.RESTART_POD,
        target_service=service,
        confidence=1.0,
        reason="Manual API trigger"
    )
    old_dry = recovery_executor.dry_run
    recovery_executor.dry_run = dry_run
    res = recovery_executor.execute_recovery(action)
    recovery_executor.dry_run = old_dry
    return {"success": res, "service": service, "action": "restart"}

@router.post("/recover/{service}/scale")
def scale_service(service: str, replicas: int, dry_run: bool = True):
    action = RecoveryAction(
        action_type=ActionType.SCALE_UP if replicas > 1 else ActionType.SCALE_DOWN,
        target_service=service,
        parameters={"replicas": replicas},
        confidence=1.0,
        reason="Manual API scale"
    )
    old_dry = recovery_executor.dry_run
    recovery_executor.dry_run = dry_run
    res = recovery_executor.execute_recovery(action)
    recovery_executor.dry_run = old_dry
    return {"success": res, "service": service, "action": "scale", "replicas": replicas}
