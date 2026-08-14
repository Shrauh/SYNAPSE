"""
SYNAPSE Continual Learning — Elastic Weight Consolidation (EWC).

Prevents catastrophic forgetting when the GNN model is updated on new
fault patterns. EWC adds a regularization term that penalizes changes
to weights that were important for previously learned tasks.

Reference: Kirkpatrick et al., "Overcoming catastrophic forgetting in
neural networks", PNAS 2017.
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional

import torch
import torch.nn as nn


class EWC:
    """Elastic Weight Consolidation for continual learning.

    After training on a task, computes the Fisher Information Matrix
    (diagonal approximation) to identify important weights. During
    subsequent training, adds a penalty for deviating from those weights.
    """

    def __init__(
        self,
        model: nn.Module,
        ewc_lambda: float = 5000.0,
    ):
        """
        Args:
            model: The neural network model (GATAnomalyDetector).
            ewc_lambda: Regularization strength. Higher = more resistance
                to forgetting (but slower adaptation).
        """
        self.model = model
        self.ewc_lambda = ewc_lambda

        # Stored per-task: {task_id: (fisher_diag, optimal_params)}
        self._task_memories: Dict[str, dict] = {}
        self._tasks_seen: int = 0

    def register_task(
        self,
        task_id: str,
        data_list: list,
        criterion: nn.Module = None,
    ) -> None:
        """Record the Fisher information for a completed task.

        Call this AFTER training on a task, BEFORE moving to the next.

        Args:
            task_id: Unique identifier for this task/scenario.
            data_list: List of PyG Data objects used for this task.
            criterion: Loss function (default: MSELoss).
        """
        if criterion is None:
            criterion = nn.MSELoss()

        # Save current optimal parameters
        optimal_params = {
            name: param.data.clone()
            for name, param in self.model.named_parameters()
            if param.requires_grad
        }

        # Compute Fisher Information (diagonal approximation)
        fisher_diag = self._compute_fisher(data_list, criterion)

        self._task_memories[task_id] = {
            "fisher": fisher_diag,
            "params": optimal_params,
        }
        self._tasks_seen += 1

    def _compute_fisher(
        self,
        data_list: list,
        criterion: nn.Module,
    ) -> Dict[str, torch.Tensor]:
        """Compute diagonal Fisher Information Matrix.

        Uses empirical Fisher: average of squared gradients over data.
        """
        fisher = {
            name: torch.zeros_like(param)
            for name, param in self.model.named_parameters()
            if param.requires_grad
        }

        self.model.eval()
        n_samples = 0

        for data in data_list:
            self.model.zero_grad()

            try:
                x_hat, _, _ = self.model(data.x, data.edge_index)
                loss = criterion(x_hat, data.x)
                loss.backward()
            except Exception:
                continue

            for name, param in self.model.named_parameters():
                if param.requires_grad and param.grad is not None:
                    fisher[name] += param.grad.data ** 2

            n_samples += 1

        # Average
        for name in fisher:
            if n_samples > 0:
                fisher[name] /= n_samples

        return fisher

    def penalty(self) -> torch.Tensor:
        """Compute the EWC penalty term to add to the training loss.

        penalty = (lambda/2) * sum_i F_i * (theta_i - theta_i*)^2

        where F_i is Fisher information, theta_i is current param,
        and theta_i* is the optimal param from previous tasks.
        """
        total_penalty = torch.tensor(0.0)
        if not self._task_memories:
            return total_penalty

        device = next(self.model.parameters()).device
        total_penalty = total_penalty.to(device)

        for task_id, memory in self._task_memories.items():
            fisher = memory["fisher"]
            optimal = memory["params"]

            for name, param in self.model.named_parameters():
                if name in fisher and param.requires_grad:
                    f = fisher[name].to(device)
                    p_star = optimal[name].to(device)
                    total_penalty += (f * (param - p_star) ** 2).sum()

        return (self.ewc_lambda / 2) * total_penalty

    @property
    def tasks_seen(self) -> int:
        return self._tasks_seen

    @property
    def task_ids(self) -> List[str]:
        return list(self._task_memories.keys())

    def get_stats(self) -> Dict:
        """Return EWC statistics."""
        return {
            "ewc_lambda": self.ewc_lambda,
            "tasks_seen": self._tasks_seen,
            "task_ids": self.task_ids,
        }
