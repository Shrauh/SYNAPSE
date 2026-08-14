"""
Tests for the Recovery Engine module.
"""
import pytest
from app.ai_module.rl.recovery_engine import (
    RecoveryEngine, ActionType, RecoveryAction, ActionResult,
)


class TestRecoveryEngine:
    """Tests for simulated recovery actions."""

    def setup_method(self):
        self.engine = RecoveryEngine()

    def test_l1_selects_action(self):
        """L1 fault should select appropriate action."""
        action = self.engine.select_action(
            severity_level=1, root_cause_service="api-gateway",
            fault_type="latency_spike", causal_confidence=0.85,
        )
        assert action.action_type == ActionType.SCALE_UP
        assert action.target_service == "api-gateway"

    def test_l3_does_nothing(self):
        """L3+ should not auto-fix."""
        action = self.engine.select_action(
            severity_level=3, root_cause_service="db-service",
            fault_type="cpu_overload", causal_confidence=0.9,
        )
        assert action.action_type == ActionType.DO_NOTHING

    def test_low_confidence_does_nothing(self):
        """Low confidence should skip auto-fix."""
        action = self.engine.select_action(
            severity_level=1, root_cause_service="svc-a",
            fault_type="error_spike", causal_confidence=0.3,
        )
        assert action.action_type == ActionType.DO_NOTHING

    def test_execute_simulated(self):
        """Executed actions should be simulated."""
        action = RecoveryAction(
            action_type=ActionType.RESTART_POD,
            target_service="auth-service",
            confidence=0.9,
        )
        result = self.engine.execute_action(action)
        assert result.simulated is True
        assert result.success is True
        assert "auth-service" in result.kubectl_command

    def test_kubectl_command_format(self):
        """Verify kubectl commands are properly formatted."""
        action = RecoveryAction(
            action_type=ActionType.SCALE_UP,
            target_service="order-service",
            parameters={"replicas": 4},
            confidence=0.9,
        )
        result = self.engine.execute_action(action)
        assert "order-service" in result.kubectl_command
        assert "4" in result.kubectl_command

    def test_action_history(self):
        """Verify actions are logged in history."""
        action = RecoveryAction(
            action_type=ActionType.RESTART_POD,
            target_service="test-svc",
            confidence=0.8,
        )
        self.engine.execute_action(action)
        history = self.engine.get_action_history()
        assert len(history) == 1
        assert history[0]["service"] == "test-svc"

    def test_engine_status(self):
        """Verify status reporting."""
        status = self.engine.get_status()
        assert "total_actions" in status
        assert "supported_actions" in status
        assert len(status["supported_actions"]) == 6
