import subprocess
import logging
import time
from datetime import datetime, timezone
from app.ai_module.rl.recovery_engine import RecoveryAction, ActionType

logger = logging.getLogger(__name__)

class RecoveryExecutor:
    def __init__(self, dry_run: bool = True, confirm_before_execute: bool = True):
        self.dry_run = dry_run
        self.confirm_before_execute = confirm_before_execute

    def restart_deployment(self, service_name: str, namespace: str = 'default'):
        cmd = f"kubectl rollout restart deployment/{service_name} -n {namespace}"
        return self._run_command(cmd)

    def scale_deployment(self, service_name: str, replicas: int, namespace: str = 'default'):
        cmd = f"kubectl scale deployment/{service_name} --replicas={replicas} -n {namespace}"
        return self._run_command(cmd)

    def verify_recovery(self, service_name: str, timeout: int = 60) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            cmd = f"kubectl get pods -l app={service_name} -n default -o json"
            try:
                result = subprocess.run(cmd.split(), capture_output=True, text=True)
                if result.returncode == 0:
                    import json
                    data = json.loads(result.stdout)
                    all_running = True
                    items = data.get('items', [])
                    if not items:
                        all_running = False
                    for item in items:
                        if item.get('status', {}).get('phase') != 'Running':
                            all_running = False
                    if all_running:
                        return True
            except Exception as e:
                logger.error(f"Error verifying recovery: {e}")
            time.sleep(5)
        return False

    def execute_recovery(self, action: RecoveryAction):
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info(f"[{timestamp}] Executing recovery action: {action.action_type} for {action.target_service}")
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would execute {action.action_type} for {action.target_service}")
            return True

        if action.action_type == ActionType.RESTART_POD:
            return self.restart_deployment(action.target_service)
        elif action.action_type == ActionType.SCALE_UP:
            replicas = action.parameters.get('replicas', 4)
            return self.scale_deployment(action.target_service, replicas)
        elif action.action_type == ActionType.SCALE_DOWN:
            replicas = action.parameters.get('replicas', 1)
            return self.scale_deployment(action.target_service, replicas)
        else:
            logger.warning(f"Unsupported action type for direct execution: {action.action_type}")
            return False

    def _run_command(self, cmd: str) -> bool:
        logger.info(f"Running command: {cmd}")
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Command successful: {result.stdout}")
                return True
            else:
                logger.error(f"Command failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Exception running command: {e}")
            return False

recovery_executor = RecoveryExecutor()
