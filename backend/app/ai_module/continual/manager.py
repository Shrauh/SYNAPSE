"""
SYNAPSE Continual Learning Manager — Coordinates EWC + MAML + Replay.

Provides a unified interface for continual learning that combines:
1. Elastic Weight Consolidation (knowledge preservation in weights)
2. Experience Replay (knowledge preservation in data buffer)
3. Distribution Drift Detection (triggers adaptation when new failure patterns occur)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    torch = None  # type: ignore
    nn = None     # type: ignore
    HAS_TORCH = False

from app.ai_module.continual.ewc import EWC
from app.ai_module.continual.replay_buffer import ReplayBuffer
from app.config import settings


class ContinualLearningManager:
    """Manages continual learning and drift detection for SYNAPSE models."""

    def __init__(
        self,
        model: Optional[nn.Module] = None,
        ewc_lambda: Optional[float] = None,
        replay_buffer_size: int = 500,
        drift_threshold: float = 0.45,
    ):
        self._model = model
        self._ewc: Optional[EWC] = None
        self._replay = ReplayBuffer(max_size=replay_buffer_size)
        self._ewc_lambda = ewc_lambda or getattr(settings, "ewc_lambda", 5000.0)
        self._drift_threshold = drift_threshold
        self._baseline_mean: Optional[np.ndarray] = None
        self._baseline_std: Optional[np.ndarray] = None
        self._initialized = False
        self._forgetting_rate = 0.0
        self._prev_performance: Dict[str, float] = {}
        self._drift_events: List[Dict[str, Any]] = []

    def initialize(self, model: nn.Module) -> None:
        """Initialize with a model."""
        self._model = model
        self._ewc = EWC(model, ewc_lambda=self._ewc_lambda)
        self._initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._model is not None

    def fit_baseline_distribution(self, feature_matrix: np.ndarray) -> None:
        """Fit baseline feature distribution for drift detection."""
        self._baseline_mean = np.mean(feature_matrix, axis=0)
        self._baseline_std = np.std(feature_matrix, axis=0) + 1e-6

    def detect_drift(self, feature_matrix: np.ndarray) -> Tuple[bool, float]:
        """Detect whether incoming incident features represent a distribution drift / novel fault.

        Returns:
            (is_drift, drift_score)
        """
        if self._baseline_mean is None or self._baseline_std is None:
            self.fit_baseline_distribution(feature_matrix)
            return False, 0.0

        current_mean = np.mean(feature_matrix, axis=0)
        # Normalized Euclidean distance / Wasserstein proxy
        diff = np.abs(current_mean - self._baseline_mean) / self._baseline_std
        drift_score = float(np.mean(diff))

        is_drift = drift_score > self._drift_threshold
        if is_drift:
            self._drift_events.append({
                "drift_score": round(drift_score, 4),
                "threshold": self._drift_threshold,
            })
        return is_drift, round(drift_score, 4)

    def register_completed_task(
        self,
        task_id: str,
        training_data: list,
        task_performance: float = 0.0,
    ) -> None:
        """Register a completed training task for continual learning."""
        if not self.is_initialized or not self._ewc:
            return

        self._ewc.register_task(task_id, training_data)
        self._replay.add_batch(training_data, task_id=task_id)
        self._prev_performance[task_id] = task_performance

    def get_ewc_penalty(self) -> Any:
        """Get the EWC regularization penalty to add to training loss."""
        if not self.is_initialized or self._ewc is None or not HAS_TORCH:
            return torch.tensor(0.0) if HAS_TORCH else 0.0
        return self._ewc.penalty()

    def get_replay_samples(self, batch_size: int = 10) -> list:
        return self._replay.get_replay_data(batch_size)

    def update_forgetting_rate(
        self,
        current_performance: Dict[str, float],
    ) -> float:
        """Compute the forgetting rate across previous tasks."""
        if not self._prev_performance:
            return 0.0

        drops = []
        for task_id, prev_perf in self._prev_performance.items():
            if task_id in current_performance:
                curr_perf = current_performance[task_id]
                if prev_perf > 0:
                    drop = max(0, (prev_perf - curr_perf) / prev_perf)
                    drops.append(drop)

        self._forgetting_rate = sum(drops) / len(drops) if drops else 0.0
        return self._forgetting_rate

    def get_status(self) -> Dict[str, Any]:
        """Get continual learning status for API reporting."""
        return {
            "ewc_lambda": self._ewc_lambda,
            "tasks_learned": self._ewc.tasks_seen if self._ewc else 0,
            "replay_buffer_size": self._replay.size,
            "forgetting_rate": round(self._forgetting_rate, 4),
            "task_ids": self._ewc.task_ids if self._ewc else [],
            "drift_events_count": len(self._drift_events),
            "last_drift": self._drift_events[-1] if self._drift_events else None,
            "replay_stats": self._replay.get_stats(),
        }


# Module-level singleton
continual_manager = ContinualLearningManager()
