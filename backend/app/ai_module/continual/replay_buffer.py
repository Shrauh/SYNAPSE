"""
SYNAPSE Continual Learning — Experience Replay Buffer.

Maintains a buffer of representative past training samples to interleave
with new data during training, preventing catastrophic forgetting.
Complements EWC with a data-level retention strategy.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any, Dict, List, Optional

import torch


class ReplayBuffer:
    """Fixed-size buffer storing representative past training examples.

    Uses reservoir sampling to maintain a representative subset of
    all training data seen so far, even as the buffer fills up.
    """

    def __init__(self, max_size: int = 500):
        """
        Args:
            max_size: Maximum number of samples to retain.
        """
        self.max_size = max_size
        self._buffer: List[Dict[str, Any]] = []
        self._total_seen: int = 0

    def add(
        self,
        features: torch.Tensor,
        edge_index: torch.Tensor,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Add a training sample to the buffer.

        Uses reservoir sampling: each new sample has a (max_size / total_seen)
        probability of being included, ensuring uniform representation.

        Args:
            features: Node feature tensor [num_nodes, num_features]
            edge_index: Edge index tensor [2, num_edges]
            metadata: Optional metadata (task_id, timestamp, etc.)
        """
        sample = {
            "features": features.cpu().clone(),
            "edge_index": edge_index.cpu().clone(),
            "metadata": metadata or {},
        }

        self._total_seen += 1

        if len(self._buffer) < self.max_size:
            self._buffer.append(sample)
        else:
            # Reservoir sampling
            idx = random.randint(0, self._total_seen - 1)
            if idx < self.max_size:
                self._buffer[idx] = sample

    def add_batch(
        self,
        data_list: list,
        task_id: str = "unknown",
    ) -> int:
        """Add multiple samples from a list of PyG-style data objects.

        Args:
            data_list: List of objects with .x and .edge_index attributes.
            task_id: Identifier for the task these samples belong to.

        Returns:
            Number of samples added.
        """
        count = 0
        for data in data_list:
            if hasattr(data, 'x') and hasattr(data, 'edge_index'):
                self.add(
                    features=data.x,
                    edge_index=data.edge_index,
                    metadata={"task_id": task_id},
                )
                count += 1
        return count

    def sample(self, batch_size: int) -> List[Dict[str, Any]]:
        """Sample a random batch from the buffer.

        Args:
            batch_size: Number of samples to return.

        Returns:
            List of sample dicts (may be smaller than batch_size if buffer is small).
        """
        actual_size = min(batch_size, len(self._buffer))
        if actual_size == 0:
            return []
        return random.sample(self._buffer, actual_size)

    def get_replay_data(self, batch_size: int = 10) -> list:
        """Get replay samples as PyG-compatible data objects.

        Returns:
            List of SimpleNamespace objects with .x and .edge_index.
        """
        from types import SimpleNamespace

        samples = self.sample(batch_size)
        data_list = []
        for s in samples:
            data = SimpleNamespace(
                x=s["features"],
                edge_index=s["edge_index"],
            )
            data_list.append(data)
        return data_list

    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer.clear()
        self._total_seen = 0

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def total_seen(self) -> int:
        return self._total_seen

    def get_stats(self) -> Dict[str, int]:
        """Return buffer statistics."""
        task_counts: Dict[str, int] = {}
        for sample in self._buffer:
            tid = sample.get("metadata", {}).get("task_id", "unknown")
            task_counts[tid] = task_counts.get(tid, 0) + 1

        return {
            "buffer_size": len(self._buffer),
            "max_size": self.max_size,
            "total_seen": self._total_seen,
            "task_distribution": task_counts,
        }
