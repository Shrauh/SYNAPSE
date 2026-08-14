"""
SYNAPSE LLM Cache — Incident Signature Caching for LLM Responses.

Caches LLM responses keyed by incident signature (anomalous services +
causal structure) to avoid redundant API calls for duplicate patterns.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple


class RCACache:
    """LRU cache for LLM RCA responses, keyed by incident signature."""

    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _compute_signature(
        self,
        anomaly_scores: Dict[str, float],
        causal_edges: List[Tuple[str, str, float]],
    ) -> str:
        """Compute a hash signature for the incident pattern.

        Two incidents with the same set of anomalous services and
        causal structure (ignoring exact scores) get the same signature.
        """
        # Discretize anomaly scores to buckets (reduces cache sensitivity)
        discretized = {
            svc: round(score * 5) / 5  # Bucket to nearest 0.2
            for svc, score in sorted(anomaly_scores.items())
            if score > 0.3  # Only include meaningfully anomalous
        }

        # Normalize causal edges (sorted, discretized strength)
        normalized_edges = sorted([
            (src, tgt, round(strength * 4) / 4)
            for src, tgt, strength in causal_edges
        ])

        signature_data = {
            "scores": discretized,
            "edges": normalized_edges,
        }

        sig_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.sha256(sig_str.encode()).hexdigest()[:16]

    def get(
        self,
        anomaly_scores: Dict[str, float],
        causal_edges: List[Tuple[str, str, float]],
    ) -> Optional[Dict[str, Any]]:
        """Look up a cached response.

        Returns:
            Cached response dict, or None if not found.
        """
        sig = self._compute_signature(anomaly_scores, causal_edges)

        if sig in self._cache:
            self._hits += 1
            # Move to end (most recently used)
            self._cache.move_to_end(sig)
            return dict(self._cache[sig])  # Return copy

        self._misses += 1
        return None

    def put(
        self,
        anomaly_scores: Dict[str, float],
        causal_edges: List[Tuple[str, str, float]],
        response: Dict[str, Any],
    ) -> None:
        """Store a response in the cache."""
        sig = self._compute_signature(anomaly_scores, causal_edges)

        # Remove metadata keys from cached response
        clean = {k: v for k, v in response.items() if not k.startswith("_")}

        self._cache[sig] = clean
        self._cache.move_to_end(sig)

        # Evict oldest if over capacity
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> Dict[str, int]:
        """Cache hit/miss statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
        }
