"""
SYNAPSE W0 Prior Matrix Generator — LLM-Informed Causal Priors.

Generates a W0 prior matrix that encodes the known service dependency
topology into the DECI causal discovery loss function. This "injects"
human + LLM knowledge as a Bayesian prior, biasing the learned causal
DAG toward architecturally plausible edges.

W0[i][j] = 1.0  → strong prior that service[i] causes service[j]
W0[i][j] = 0.0  → no prior (data-driven only)
W0[i][j] = -1.0 → strong prior AGAINST edge (impossible dependency)

Usage:
    from app.ai_module.llm.w0_generator import w0_generator
    matrix, names = await w0_generator.generate(service_names)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# ── Hard-coded topology from Google Online Boutique ──────────────────────
# This is the ground truth dependency graph. W0 is built from this.
KNOWN_TOPOLOGY: Dict[str, List[str]] = {
    "frontend":  ["checkout", "cart", "catalog", "ad"],
    "checkout":  ["payment", "order", "cart"],
    "cart":      ["redis"],
    "payment":   ["orderdb"],
    "order":     ["orderdb", "email"],
    "catalog":   [],
    "ad":        [],
    "redis":     [],
    "email":     [],
    "orderdb":   [],
}

# Topology-based W0 weights
TOPOLOGY_WEIGHT = 0.8   # Strong prior for known edges
IMPOSSIBLE_WEIGHT = -0.5  # Negative prior for reverse of known edges


class W0Generator:
    """Generates W0 causal prior matrices from topology + LLM knowledge.

    The W0 matrix is used to constrain the DECI / NOTEARS optimization
    by penalizing edges that contradict known service dependencies.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, np.ndarray] = {}

    def generate_from_topology(
        self,
        service_names: List[str],
    ) -> np.ndarray:
        """Build W0 from hard-coded Google Online Boutique topology.

        Args:
            service_names: Ordered list of service names (matrix row/col order).

        Returns:
            numpy array of shape (N, N) where N = len(service_names).
        """
        n = len(service_names)
        idx = {svc: i for i, svc in enumerate(service_names)}
        W0 = np.zeros((n, n), dtype=float)

        for src, targets in KNOWN_TOPOLOGY.items():
            if src not in idx:
                continue
            for tgt in targets:
                if tgt not in idx:
                    continue
                i, j = idx[src], idx[tgt]
                W0[i][j] = TOPOLOGY_WEIGHT    # src → tgt is likely
                W0[j][i] = IMPOSSIBLE_WEIGHT  # tgt → src is unlikely

        return W0

    async def generate_llm_enhanced(
        self,
        service_names: List[str],
        anomaly_context: Optional[Dict[str, float]] = None,
    ) -> np.ndarray:
        """Generate W0 enhanced by LLM knowledge of the incident.

        First builds topology-based W0, then queries the LLM to adjust
        weights based on the current anomaly pattern. For example, if
        `payment` has a very high anomaly score, the LLM might suggest
        strengthening edges from `payment` → downstream services.

        Args:
            service_names: Ordered list of service names.
            anomaly_context: Current anomaly scores for context.

        Returns:
            numpy array of shape (N, N).
        """
        # Start with topology prior
        W0 = self.generate_from_topology(service_names)

        if not anomaly_context:
            return W0

        # Try LLM enhancement
        try:
            W0 = await self._query_llm_adjustments(
                service_names, W0, anomaly_context
            )
        except Exception as e:
            logger.warning(f"[W0] LLM enhancement failed, using topology only: {e}")

        return W0

    async def _query_llm_adjustments(
        self,
        service_names: List[str],
        base_W0: np.ndarray,
        anomaly_scores: Dict[str, float],
    ) -> np.ndarray:
        """Ask LLM to suggest causal prior adjustments given anomaly context."""
        try:
            from app.ai_module.llm.groq_client import groq_client
            if not groq_client.is_available:
                return base_W0

            # Sort by anomaly score for context
            sorted_svcs = sorted(
                anomaly_scores.items(), key=lambda x: x[1], reverse=True
            )[:5]

            system = (
                "You are an expert in distributed systems and microservice dependencies. "
                "Given anomaly scores and known service topology, identify which services "
                "are most likely CAUSAL ROOTS (causing other services to fail)."
            )
            user = (
                f"Services and anomaly scores (higher = more anomalous):\n"
                + "\n".join(f"  - {svc}: {score:.3f}" for svc, score in sorted_svcs)
                + f"\n\nKnown topology:\n"
                + "\n".join(
                    f"  - {s} → {', '.join(ts) or 'none'}"
                    for s, ts in KNOWN_TOPOLOGY.items()
                    if s in service_names
                )
                + "\n\nReturn JSON with causal edge weights to emphasize."
                + "\nFormat: {\"edges\": [{\"from\": \"svc\", \"to\": \"svc\", \"weight\": 0.0-1.0}]}"
                + "\nOnly include edges that should be STRENGTHENED beyond topology baseline."
                + "\nMaximum 5 edges."
            )

            result = await groq_client.complete_json(system=system, user=user)
            W0 = base_W0.copy()
            idx = {svc: i for i, svc in enumerate(service_names)}

            for edge in result.get("edges", []):
                src = edge.get("from", "")
                tgt = edge.get("to", "")
                weight = float(edge.get("weight", 0.5))
                if src in idx and tgt in idx:
                    i, j = idx[src], idx[tgt]
                    # LLM adjustment: average with existing weight, capped at 1.0
                    W0[i][j] = min(1.0, (W0[i][j] + weight) / 2 + 0.2)

            logger.info(f"[W0] LLM enhanced {len(result.get('edges', []))} causal edges")
            return W0

        except Exception as e:
            logger.warning(f"[W0] LLM adjustment failed: {e}")
            return base_W0

    def get_edge_strengths(
        self,
        W0: np.ndarray,
        service_names: List[str],
        threshold: float = 0.3,
    ) -> List[Tuple[str, str, float]]:
        """Extract significant edges from W0 matrix.

        Args:
            W0: Prior matrix.
            service_names: Service name ordering.
            threshold: Minimum weight to include as an edge.

        Returns:
            List of (source, target, weight) tuples.
        """
        edges = []
        for i, src in enumerate(service_names):
            for j, tgt in enumerate(service_names):
                if i != j and W0[i][j] > threshold:
                    edges.append((src, tgt, float(W0[i][j])))
        return sorted(edges, key=lambda x: x[2], reverse=True)


# Module-level singleton
w0_generator = W0Generator()
