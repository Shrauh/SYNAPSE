"""
SYNAPSE Causal Discovery — DECI (Deep End-to-end Causal Inference) Engine.

Replaces the baseline PC Algorithm with differentiable causal discovery.
Leverages continuous optimization with NOTEARS acyclicity constraints and
integrates LLM-RAG prior knowledge (W0) to restrict search space and find
the true non-linear root cause in under 60 seconds.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from app.ai_module.causal.deci import DECIEngine


class CausalDiscoveryEngine:
    """Discovers causal structure among anomalous services using DECI."""

    def __init__(
        self,
        alpha: float = 0.05,
        indep_test: str = "deci",
        lambda_prior: float = 2.0,
        max_iter: int = 120,
    ):
        """
        Args:
            alpha: Significance threshold for discovery.
            indep_test: Causal method identifier ('deci').
            lambda_prior: Regularization factor for LLM-RAG prior injection W0.
            max_iter: Optimization iterations for DECI.
        """
        self.alpha = alpha
        self.indep_test = indep_test
        self._deci = DECIEngine(
            max_iter=max_iter,
            lambda_prior=lambda_prior,
            edge_threshold=0.20,
        )

    def discover(
        self,
        time_series_matrix: np.ndarray,
        service_names: List[str],
        w0_prior: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Run DECI causal discovery on anomalous service time series.

        Args:
            time_series_matrix: Shape [num_timesteps, num_anomalous_services].
            service_names: Names of anomalous services (columns).
            w0_prior: Optional LLM-RAG prior adjacency matrix.

        Returns:
            Dict containing:
                - "adjacency": Weighted adjacency matrix
                - "edges": List of (source, target, strength) tuples
                - "nodes": service_names
                - "dag": Adjacency dict {source: [targets]}
                - "h_score": NOTEARS score
                - "method": Method name string
        """
        return self._deci.discover(
            time_series_matrix=time_series_matrix,
            service_names=service_names,
            w0_prior=w0_prior,
        )
