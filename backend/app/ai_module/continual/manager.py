"""
SYNAPSE Continual Learning Manager — Coordinates EWC + Replay.

Provides a unified interface for continual learning that combines
Elastic Weight Consolidation (knowledge preservation in weights) with
Experience Replay (knowledge preservation in data).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

from app.ai_module.continual.ewc import EWC
from app.ai_module.continual.replay_buffer import ReplayBuffer
from app.config import settings


class ContinualLearningManager:
    """Manages continual learning for the GNN anomaly detector.

    Combines:
    1. EWC — regularizes weight updates to preserve important knowledge
    2. Replay Buffer — interleaves past data during training

    Usage:
        manager = ContinualLearningManager(model)
        # After training on task 1:
        manager.register_completed_task("task_1", task_1_data)
        # When training on task 2:
        loss = base_loss + manager.get_ewc_penalty()
        replay_data = manager.get_replay_samples()
    """

    def __init__(
        self,
        model: Optional[nn.Module] = None,
        ewc_lambda: float = None,
        replay_buffer_size: int = 500,
    ):
        self._model = model
        self._ewc: Optional[EWC] = None
        self._replay = ReplayBuffer(max_size=replay_buffer_size)
        self._ewc_lambda = ewc_lambda or settings.ewc_lambda
        self._initialized = False
        self._forgetting_rate = 0.0
        self._prev_performance: Dict[str, float] = {}

    def initialize(self, model: nn.Module) -> None:
        """Initialize with a model (can be called after construction)."""
        self._model = model
        self._ewc = EWC(model, ewc_lambda=self._ewc_lambda)
        self._initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._model is not None

    def register_completed_task(
        self,
        task_id: str,
        training_data: list,
        task_performance: float = 0.0,
    ) -> None:
        """Register a completed training task for continual learning.

        Call this AFTER successfully training on a task.

        Args:
            task_id: Unique identifier (e.g., "normal_baseline", "fault_db_latency")
            training_data: List of PyG Data objects used for training.
            task_performance: Performance metric (e.g., loss) for forgetting tracking.
        """
        if not self.is_initialized:
            return

        # Register with EWC
        self._ewc.register_task(task_id, training_data)

        # Add samples to replay buffer
        self._replay.add_batch(training_data, task_id=task_id)

        # Track performance for forgetting rate computation
        self._prev_performance[task_id] = task_performance

    def get_ewc_penalty(self) -> torch.Tensor:
        """Get the EWC regularization penalty to add to training loss.

        Returns:
            Scalar tensor. Add to base loss during training.
        """
        if not self.is_initialized or self._ewc is None:
            return torch.tensor(0.0)
        return self._ewc.penalty()

    def get_replay_samples(self, batch_size: int = 10) -> list:
        """Get replay samples to interleave during training.

        Returns:
            List of data objects with .x and .edge_index.
        """
        return self._replay.get_replay_data(batch_size)

    def update_forgetting_rate(
        self,
        current_performance: Dict[str, float],
    ) -> float:
        """Compute the forgetting rate across previous tasks.

        Forgetting rate = average performance drop on previous tasks
        after training on a new task.

        Args:
            current_performance: {task_id: current_metric} for old tasks.

        Returns:
            Forgetting rate (0 = no forgetting, 1 = complete forgetting).
        """
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
            "replay_stats": self._replay.get_stats(),
        }


# Module-level singleton
continual_manager = ContinualLearningManager()
