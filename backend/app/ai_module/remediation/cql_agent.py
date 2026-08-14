"""
SYNAPSE CQL Agent — Conservative Q-Learning for Auto-Remediation.

Implements Conservative Q-Learning (CQL) as an offline RL agent that
selects remediation actions based on observed system state.

CQL adds a conservative penalty to standard Q-learning to prevent
over-optimistic Q-values on out-of-distribution actions — critical
for safety in production auto-remediation.

State space:  (fault_type, top_anomalous_services, metric_summary)
Action space: 6 remediation actions (see action_space.py)
Reward:       +1 if incident resolved, -0.5 if situation worsened

When CQL confidence > threshold → AUTO EXECUTE
When CQL confidence <= threshold → RECOMMEND ONLY (human approval needed)

Reference:
    Kumar et al. (2020). Conservative Q-Learning for Offline RL.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.ai_module.remediation.action_space import (
    ALL_ACTIONS,
    ACTION_REGISTRY,
    FAULT_TO_ACTION,
    RemediationAction,
)
from app.config import settings

logger = logging.getLogger(__name__)


class CQLAgent:
    """Conservative Q-Learning agent for remediation action selection.

    Uses a Q-table (hashed state → Q-values per action) in offline RL
    mode. The Q-table is updated by engineer feedback after each incident.

    The conservative penalty α penalizes actions that haven't been
    observed in the offline data to prevent unsafe exploitation.
    """

    ACTION_IDS = [a.action_id for a in ALL_ACTIONS]
    N_ACTIONS = len(ALL_ACTIONS)

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount: float = 0.95,
        cql_alpha: float = 1.0,      # Conservative penalty weight
        exploration_eps: float = 0.05,  # Epsilon for rare exploration
    ) -> None:
        self.lr = learning_rate
        self.gamma = discount
        self.cql_alpha = cql_alpha
        self.eps = exploration_eps

        # Q-table: state_hash → [Q(s,a) for each action]
        self._q_table: Dict[str, np.ndarray] = {}
        # Visit counts: state_hash → action_idx → count
        self._visit_counts: Dict[str, np.ndarray] = {}
        # Replay buffer for offline updates
        self._replay: List[Dict[str, Any]] = []

    def _encode_state(
        self,
        fault_type: str,
        root_cause_service: str,
        anomaly_scores: Dict[str, float],
        metric_deltas: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> str:
        """Encode system state into a hashable string.

        State features:
          - fault_type (discretized)
          - root_cause_service
          - top-3 anomalous services (sorted)
          - whether CPU/memory/error/latency are elevated
        """
        # Top-3 anomalous services
        top_svcs = sorted(anomaly_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        top_names = tuple(s for s, _ in top_svcs)

        # Binary feature flags from deltas
        flags = {"high_cpu": 0, "high_mem": 0, "high_err": 0, "high_lat": 0}
        if metric_deltas:
            for svc_deltas in metric_deltas.values():
                for metric, delta_str in svc_deltas.items():
                    try:
                        val = abs(float(delta_str.replace("%", "").replace("+", "")))
                        if metric == "cpu" and val > 50:
                            flags["high_cpu"] = 1
                        elif metric == "memory" and val > 50:
                            flags["high_mem"] = 1
                        elif metric == "error_rate" and val > 30:
                            flags["high_err"] = 1
                        elif metric == "latency" and val > 100:
                            flags["high_lat"] = 1
                    except (ValueError, AttributeError):
                        pass

        state_obj = {
            "fault": fault_type or "unknown",
            "root": root_cause_service,
            "top": top_names,
            "flags": tuple(sorted(flags.items())),
        }
        state_str = json.dumps(state_obj, sort_keys=True)
        return hashlib.md5(state_str.encode()).hexdigest()[:12]

    def _get_q_values(self, state_hash: str) -> np.ndarray:
        """Get Q-values for a state, initializing from priors if unseen."""
        if state_hash not in self._q_table:
            # Initialize with small random values (optimistic initialization)
            self._q_table[state_hash] = np.random.uniform(0.4, 0.6, self.N_ACTIONS)
            self._visit_counts[state_hash] = np.zeros(self.N_ACTIONS)
        return self._q_table[state_hash]

    def _apply_cql_penalty(
        self,
        q_values: np.ndarray,
        state_hash: str,
    ) -> np.ndarray:
        """Apply conservative penalty to reduce confidence on rare state-actions.

        CQL penalty: Q_cql(s,a) = Q(s,a) - α * (1 / (n(s,a) + 1))
        Where n(s,a) is the number of times we've seen this (state, action) pair.
        """
        counts = self._visit_counts.get(state_hash, np.zeros(self.N_ACTIONS))
        # Conservative penalty: less data → lower effective Q
        penalty = self.cql_alpha / (counts + 1)
        return q_values - penalty

    def select_action(
        self,
        fault_type: str,
        root_cause_service: str,
        anomaly_scores: Dict[str, float],
        metric_deltas: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Tuple[RemediationAction, float, bool]:
        """Select the best remediation action using CQL Q-values.

        Args:
            fault_type: Detected fault type (e.g., 'cpu_stress').
            root_cause_service: Service identified as root cause.
            anomaly_scores: Current anomaly scores dict.
            metric_deltas: Metric changes from baseline.

        Returns:
            Tuple of:
              - action: The selected RemediationAction
              - confidence: Float 0-1 (softmax probability of top action)
              - should_auto_execute: True if confidence > action's threshold
        """
        state_hash = self._encode_state(
            fault_type, root_cause_service, anomaly_scores, metric_deltas
        )
        q_values = self._get_q_values(state_hash)
        q_conservative = self._apply_cql_penalty(q_values, state_hash)

        # Softmax confidence
        exp_q = np.exp(q_conservative - np.max(q_conservative))
        probs = exp_q / exp_q.sum()

        best_action_idx = int(np.argmax(probs))
        confidence = float(probs[best_action_idx])

        # Get the action
        best_action_id = self.ACTION_IDS[best_action_idx]
        action = ACTION_REGISTRY.get(best_action_id)

        # Fallback to rule-based if action not found or Q table not trained
        if action is None or confidence < 0.15:
            action = FAULT_TO_ACTION.get(fault_type, FAULT_TO_ACTION.get("latency_spike"))
            if action is None:
                action = ALL_ACTIONS[0]  # Scale up as safe default
            confidence = 0.70  # Rule-based confidence

        # Decide auto-execute
        if action.always_require_approval:
            should_auto_execute = False
        else:
            threshold = action.auto_execute_threshold
            should_auto_execute = (
                settings.remediation_auto_execute
                and confidence >= threshold
            )

        logger.info(
            f"[CQL] Action={action.action_id}, confidence={confidence:.3f}, "
            f"auto={should_auto_execute}, state={state_hash}"
        )
        return action, confidence, should_auto_execute

    def update_from_feedback(
        self,
        fault_type: str,
        root_cause_service: str,
        anomaly_scores: Dict[str, float],
        action_id: str,
        reward: float,
        metric_deltas: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> None:
        """Update Q-table from engineer feedback (offline RL update).

        Args:
            fault_type: Fault type at time of action.
            root_cause_service: Root cause service.
            anomaly_scores: Anomaly scores at time of action.
            action_id: Action that was taken.
            reward: Feedback reward (+1 = resolved, -0.5 = worsened, 0 = neutral).
            metric_deltas: Metric deltas at time of action.
        """
        state_hash = self._encode_state(
            fault_type, root_cause_service, anomaly_scores, metric_deltas
        )
        q_values = self._get_q_values(state_hash)

        if action_id not in self.ACTION_IDS:
            logger.warning(f"[CQL] Unknown action ID: {action_id}")
            return

        action_idx = self.ACTION_IDS.index(action_id)

        # Standard Q-learning update (offline: no next state bootstrap)
        target = reward  # Terminal update (no next state for offline RL)
        q_values[action_idx] += self.lr * (target - q_values[action_idx])
        self._q_table[state_hash] = q_values

        # Increment visit count
        if state_hash not in self._visit_counts:
            self._visit_counts[state_hash] = np.zeros(self.N_ACTIONS)
        self._visit_counts[state_hash][action_idx] += 1

        # Add to replay buffer
        self._replay.append({
            "state": state_hash,
            "action": action_id,
            "reward": reward,
            "fault_type": fault_type,
        })

        # Keep replay buffer bounded
        if len(self._replay) > 500:
            self._replay = self._replay[-500:]

        logger.info(f"[CQL] Updated Q[{state_hash}][{action_id}] = {q_values[action_idx]:.4f}")

    def get_all_action_scores(
        self,
        fault_type: str,
        root_cause_service: str,
        anomaly_scores: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Get confidence scores for all actions (for UI display)."""
        state_hash = self._encode_state(fault_type, root_cause_service, anomaly_scores)
        q_values = self._get_q_values(state_hash)
        q_conservative = self._apply_cql_penalty(q_values, state_hash)
        exp_q = np.exp(q_conservative - np.max(q_conservative))
        probs = exp_q / exp_q.sum()

        results = []
        for i, action in enumerate(ALL_ACTIONS):
            results.append({
                "action_id": action.action_id,
                "name": action.name,
                "confidence": float(probs[i]),
                "requires_approval": action.always_require_approval,
                "threshold": action.auto_execute_threshold,
                "risk_level": action.risk_level,
            })

        return sorted(results, key=lambda x: x["confidence"], reverse=True)

    def get_status(self) -> Dict[str, Any]:
        """Return agent status for monitoring."""
        return {
            "q_table_states": len(self._q_table),
            "replay_buffer_size": len(self._replay),
            "action_ids": self.ACTION_IDS,
            "cql_alpha": self.cql_alpha,
        }


# Module-level singleton
cql_agent = CQLAgent()
