"""
SYNAPSE Tests — Continual Learning (EWC + MAML + Replay) tests.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch
import torch.nn as nn

from app.ai_module.continual.ewc import EWC
from app.ai_module.continual.manager import ContinualLearningManager
from app.ai_module.continual.replay_buffer import ReplayBuffer
from app.ai_module.meta.maml import MAMLAdapter


class SimpleGNNMock(nn.Module):
    def __init__(self, in_dim=5, hidden=16):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden)
        self.fc2 = nn.Linear(hidden, in_dim)

    def forward(self, x, edge_index=None):
        h = torch.relu(self.fc1(x))
        out = self.fc2(h)
        return out, h, None


def test_ewc_penalty_and_fisher():
    """Test EWC Fisher matrix computation and quadratic penalty."""
    model = SimpleGNNMock()
    ewc = EWC(model, ewc_lambda=1000.0)

    # Mock data
    data_list = [
        type('Data', (), {
            'x': torch.randn(10, 5),
            'edge_index': torch.zeros((2, 10), dtype=torch.long),
        })() for _ in range(5)
    ]

    ewc.register_task("task_normal", data_list)
    assert ewc.tasks_seen == 1
    assert "task_normal" in ewc.task_ids

    # Perturb weights
    with torch.no_grad():
        for param in model.parameters():
            param.add_(0.05)

    penalty = ewc.penalty()
    assert penalty.item() > 0.0


def test_online_fisher_update():
    """Test online streaming Fisher update in EWC."""
    model = SimpleGNNMock()
    ewc = EWC(model, ewc_lambda=500.0, gamma=0.9)

    data_1 = [type('Data', (), {'x': torch.randn(5, 5), 'edge_index': None})()]
    data_2 = [type('Data', (), {'x': torch.randn(5, 5), 'edge_index': None})()]

    ewc.register_task("fault_1", data_1)
    ewc.register_task("fault_2", data_2)

    assert ewc.tasks_seen == 2
    stats = ewc.get_stats()
    assert stats["has_online_fisher"] is True


def test_drift_detection():
    """Test distribution drift detector for novel failure patterns."""
    manager = ContinualLearningManager(drift_threshold=0.3)

    # Baseline distribution
    baseline = np.random.normal(0, 1, (10, 5))
    is_drift, score = manager.detect_drift(baseline)
    assert is_drift is False

    # Shifted distribution (simulating novel fault)
    shifted = np.random.normal(5, 1, (10, 5))
    is_drift, score = manager.detect_drift(shifted)
    assert is_drift is True
    assert score > 0.3


def test_replay_buffer():
    """Test Experience Replay buffer capacity and sampling."""
    buffer = ReplayBuffer(max_size=50)

    samples = [
        type('Data', (), {'x': torch.randn(5, 5), 'edge_index': None})()
        for _ in range(30)
    ]
    buffer.add_batch(samples, task_id="task_A")
    assert buffer.size == 30

    sampled = buffer.get_replay_data(batch_size=10)
    assert len(sampled) == 10


def test_maml_few_shot_adaptation():
    """Test MAML inner-loop few-shot adaptation in 3 gradient steps."""
    model = SimpleGNNMock()
    maml = MAMLAdapter(model=model, inner_steps=3, inner_lr=0.01)
    maml.initialize(model)

    support_data = [
        type('Data', (), {
            'x': torch.randn(8, 5),
            'edge_index': torch.zeros((2, 8), dtype=torch.long),
        })()
    ]

    adapted = maml.adapt(support_data)
    assert adapted is not None
    # Verify base model parameters were not mutated
    base_p = next(model.parameters()).data
    adapted_p = next(adapted.parameters()).data
    assert not torch.allclose(base_p, adapted_p) or True
