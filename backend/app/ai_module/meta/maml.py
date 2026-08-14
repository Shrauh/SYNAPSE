"""
SYNAPSE Meta-Learning — Model-Agnostic Meta-Learning (MAML).

Enables few-shot adaptation of the GNN anomaly detector to new
fault patterns with minimal data. MAML learns an initialization
that can be quickly fine-tuned to new tasks in 3-5 gradient steps.

Reference: Finn et al., "Model-Agnostic Meta-Learning for Fast
Adaptation of Deep Networks", ICML 2017.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.optim as optim

from app.config import settings


class MAMLAdapter:
    """MAML-based few-shot adaptation for the GNN model.

    Instead of training from scratch on new fault types, MAML
    learns a model initialization that requires only a few gradient
    steps to adapt to new patterns.
    """

    def __init__(
        self,
        model: Optional[nn.Module] = None,
        inner_lr: float = None,
        outer_lr: float = None,
        inner_steps: int = None,
    ):
        self._base_model = model
        self.inner_lr = inner_lr or settings.maml_inner_lr
        self.outer_lr = outer_lr or settings.maml_outer_lr
        self.inner_steps = inner_steps or settings.maml_inner_steps

        self._meta_optimizer: Optional[optim.Adam] = None
        self._adaptation_history: List[Dict[str, Any]] = []
        self._tasks_meta_trained: int = 0
        self._initialized = False

    def initialize(self, model: nn.Module) -> None:
        """Initialize MAML with a model."""
        self._base_model = model
        self._meta_optimizer = optim.Adam(
            self._base_model.parameters(),
            lr=self.outer_lr,
        )
        self._initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._base_model is not None

    def adapt(
        self,
        support_data: list,
        criterion: nn.Module = None,
    ) -> nn.Module:
        """Few-shot adapt the model to a new task.

        Takes support data (few examples of the new pattern) and
        performs inner-loop gradient steps to create an adapted model.

        Args:
            support_data: List of PyG Data objects (support set).
            criterion: Loss function (default: MSELoss).

        Returns:
            Adapted model (copy — does not modify base model).
        """
        if not self.is_initialized:
            raise RuntimeError("MAML not initialized. Call initialize() first.")

        if criterion is None:
            criterion = nn.MSELoss()

        # Clone the base model for adaptation
        adapted_model = copy.deepcopy(self._base_model)
        adapted_model.train()

        # Inner loop: few gradient steps on support data
        for step in range(self.inner_steps):
            total_loss = torch.tensor(0.0)
            device = next(adapted_model.parameters()).device

            for data in support_data:
                try:
                    data_x = data.x.to(device) if hasattr(data, 'x') else data.features.to(device)
                    data_ei = data.edge_index.to(device) if hasattr(data, 'edge_index') else None

                    if data_ei is not None:
                        x_hat, _, _ = adapted_model(data_x, data_ei)
                    else:
                        # Fallback for non-graph data
                        continue

                    loss = criterion(x_hat, data_x)
                    total_loss = total_loss.to(device) + loss
                except Exception:
                    continue

            if total_loss.requires_grad:
                # Manual SGD step (inner loop)
                grads = torch.autograd.grad(
                    total_loss,
                    adapted_model.parameters(),
                    create_graph=False,
                    allow_unused=True,
                )
                for param, grad in zip(adapted_model.parameters(), grads):
                    if grad is not None:
                        param.data -= self.inner_lr * grad.data

        return adapted_model

    def meta_train_step(
        self,
        task_batch: List[Tuple[list, list]],
        criterion: nn.Module = None,
    ) -> float:
        """One step of meta-training (outer loop).

        Each task is a (support_set, query_set) pair.

        Args:
            task_batch: List of (support_data, query_data) tuples.
            criterion: Loss function.

        Returns:
            Average meta-loss across tasks.
        """
        if not self.is_initialized:
            return 0.0

        if criterion is None:
            criterion = nn.MSELoss()

        self._meta_optimizer.zero_grad()
        meta_loss = torch.tensor(0.0)
        device = next(self._base_model.parameters()).device
        meta_loss = meta_loss.to(device)
        valid_tasks = 0

        for support_data, query_data in task_batch:
            # Inner loop: adapt on support set
            adapted = self.adapt(support_data, criterion)

            # Evaluate adapted model on query set
            task_loss = torch.tensor(0.0).to(device)
            for data in query_data:
                try:
                    data_x = data.x.to(device)
                    data_ei = data.edge_index.to(device)
                    x_hat, _, _ = adapted(data_x, data_ei)
                    task_loss += criterion(x_hat, data_x)
                except Exception:
                    continue

            meta_loss += task_loss
            valid_tasks += 1

        if valid_tasks > 0:
            meta_loss /= valid_tasks
            if meta_loss.requires_grad:
                meta_loss.backward()
                self._meta_optimizer.step()

        self._tasks_meta_trained += 1
        return meta_loss.item()

    def record_adaptation(
        self,
        task_name: str,
        accuracy: float,
    ) -> None:
        """Record an adaptation result for tracking."""
        self._adaptation_history.append({
            "task": task_name,
            "accuracy": accuracy,
        })

    def get_status(self) -> Dict[str, Any]:
        """Get MAML status for API reporting."""
        return {
            "meta_lr": self.outer_lr,
            "inner_lr": self.inner_lr,
            "inner_steps": self.inner_steps,
            "tasks_meta_trained": self._tasks_meta_trained,
            "adaptation_history": self._adaptation_history[-10:],  # Last 10
            "initialized": self._initialized,
        }


# Module-level singleton
maml_adapter = MAMLAdapter()
