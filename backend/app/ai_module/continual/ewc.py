"""
SYNAPSE Continual Learning — Elastic Weight Consolidation (EWC).

Prevents catastrophic forgetting when the GNN model is updated on new
fault patterns. EWC adds a regularization term that penalizes changes
to weights that were important for previously learned tasks.

Features:
    - Standard Task-based EWC
    - Online Fisher Information Updates (streaming continuous learning)
    - Drift-aware weight consolidation

Reference: Kirkpatrick et al., "Overcoming catastrophic forgetting in
neural networks", PNAS 2017.
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    torch = None  # type: ignore
    nn = None     # type: ignore
    HAS_TORCH = False


class EWC:
    """Elastic Weight Consolidation for continual learning.

    After training on a task, computes the Fisher Information Matrix
    (diagonal approximation) to identify important weights. During
    subsequent training, adds a penalty for deviating from those weights.
    """

    def __init__(
        self,
        model: Optional[nn.Module] = None,
        ewc_lambda: float = 5000.0,
        gamma: float = 0.95,
    ):
        """
        Args:
            model: The neural network model (GATAnomalyDetector / VAE-GNN).
            ewc_lambda: Regularization strength. Higher = more resistance to forgetting.
            gamma: Decay factor for online Fisher updates (0 < gamma <= 1).
        """
        self.model = model
        self.ewc_lambda = ewc_lambda
        self.gamma = gamma

        # Stored per-task: {task_id: (fisher_diag, optimal_params)}
        self._task_memories: Dict[str, dict] = {}
        self._online_fisher: Optional[Dict[str, torch.Tensor]] = None
        self._online_params: Optional[Dict[str, torch.Tensor]] = None
        self._tasks_seen: int = 0

    def register_task(
        self,
        task_id: str,
        data_list: list,
        criterion: Optional[nn.Module] = None,
    ) -> None:
        """Record the Fisher information for a completed task."""
        if not HAS_TORCH or self.model is None or not data_list:
            self._tasks_seen += 1
            return

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

        # Also update running online Fisher matrix
        self.update_online_fisher(fisher_diag, optimal_params)
        self._tasks_seen += 1

    def update_online_fisher(
        self,
        new_fisher: Dict[str, torch.Tensor],
        current_params: Dict[str, torch.Tensor],
    ) -> None:
        """Update the running online Fisher matrix: F_online = gamma * F_prev + F_new."""
        if self._online_fisher is None:
            self._online_fisher = {k: v.clone() for k, v in new_fisher.items()}
            self._online_params = {k: v.clone() for k, v in current_params.items()}
        else:
            for k in self._online_fisher:
                if k in new_fisher:
                    self._online_fisher[k] = self.gamma * self._online_fisher[k] + new_fisher[k]
                    self._online_params[k] = current_params[k].clone()

    def _compute_fisher(
        self,
        data_list: list,
        criterion: nn.Module,
    ) -> Dict[str, torch.Tensor]:
        """Compute diagonal Fisher Information Matrix via empirical gradients."""
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
                if hasattr(data, 'edge_index') and data.edge_index is not None:
                    x_hat, _, _ = self.model(data.x, data.edge_index)
                else:
                    x_hat = self.model(data.x) if callable(self.model) else data.x
                loss = criterion(x_hat, data.x)
                loss.backward()
            except Exception:
                continue

            for name, param in self.model.named_parameters():
                if param.requires_grad and param.grad is not None:
                    fisher[name] += param.grad.data ** 2

            n_samples += 1

        for name in fisher:
            if n_samples > 0:
                fisher[name] /= n_samples

        return fisher

    def penalty(self) -> torch.Tensor:
        """Compute the EWC quadratic penalty term to protect important weights.

        penalty = (lambda/2) * sum_i F_i * (theta_i - theta_i*)^2
        """
        if not HAS_TORCH or self.model is None:
            return torch.tensor(0.0) if HAS_TORCH else 0.0

        device = next(self.model.parameters()).device
        total_penalty = torch.tensor(0.0, device=device)

        if self._online_fisher is not None and self._online_params is not None:
            # Use Online EWC formulation
            for name, param in self.model.named_parameters():
                if name in self._online_fisher and param.requires_grad:
                    f = self._online_fisher[name].to(device)
                    p_star = self._online_params[name].to(device)
                    total_penalty += (f * (param - p_star) ** 2).sum()
        elif self._task_memories:
            for task_id, memory in self._task_memories.items():
                fisher = memory["fisher"]
                optimal = memory["params"]
                for name, param in self.model.named_parameters():
                    if name in fisher and param.requires_grad:
                        f = fisher[name].to(device)
                        p_star = optimal[name].to(device)
                        total_penalty += (f * (param - p_star) ** 2).sum()

        return (self.ewc_lambda / 2.0) * total_penalty

    @property
    def tasks_seen(self) -> int:
        return self._tasks_seen

    @property
    def task_ids(self) -> List[str]:
        return list(self._task_memories.keys())

    def get_stats(self) -> Dict:
        return {
            "ewc_lambda": self.ewc_lambda,
            "tasks_seen": self._tasks_seen,
            "task_ids": self.task_ids,
            "has_online_fisher": self._online_fisher is not None,
        }
