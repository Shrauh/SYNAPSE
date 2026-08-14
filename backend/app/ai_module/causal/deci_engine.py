"""
SYNAPSE DECI Engine — Differentiable Causal Inference.

Implements the DECI (Deep End-to-end Causal Inference) algorithm using
NOTEARS continuous DAG relaxation with W0 prior injection.

NOTEARS formulation:
    min_W  ℓ(W) + λ₁‖W‖₁ + λ₂ h(W)
    s.t.   h(W) = tr(e^(W∘W)) - d = 0   (acyclicity)

W0 prior injection:
    ℓ_total = ℓ_data(W) + α · ‖W - W0‖²_masked

This biases the discovered DAG toward known causal relationships
(from service topology + LLM priors) while still learning from data.

References:
    - Zheng et al. (2018). DAGs with NOTEARS.
    - Geffner et al. (2022). Deep End-to-end Causal Inference. (DECI)
    - CAUSICA library: https://github.com/microsoft/causica
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class DECIEngine:
    """NOTEARS-based causal discovery with W0 prior injection.

    This is a DECI surrogate using NOTEARS optimization. The full
    CAUSICA DECI implementation can be swapped in if available.
    """

    def __init__(
        self,
        lambda1: float = 0.1,       # L1 sparsity regularizer
        lambda2: float = 0.01,       # Acyclicity constraint weight
        w0_alpha: float = 0.5,       # W0 prior injection weight
        max_iter: int = 100,         # Optimization iterations
        h_tol: float = 1e-8,         # Acyclicity tolerance
        lr: float = 0.01,            # Adam learning rate
    ) -> None:
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        self.w0_alpha = w0_alpha
        self.max_iter = max_iter
        self.h_tol = h_tol
        self.lr = lr
        self._has_torch = False
        self._check_torch()

    def _check_torch(self) -> None:
        """Check if PyTorch is available for gradient-based optimization."""
        try:
            import torch
            self._has_torch = True
        except ImportError:
            logger.warning("[DECI] PyTorch not available. Using numpy-based fallback.")

    def discover(
        self,
        X: np.ndarray,
        service_names: List[str],
        W0: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Run DECI causal discovery on a time-series feature matrix.

        Args:
            X: Data matrix of shape (T, N) where T=timesteps, N=services.
            service_names: List of service names (length N).
            W0: Prior matrix of shape (N, N). W0[i][j] > 0 means i→j likely.

        Returns:
            Dict with:
                - 'adjacency': (N, N) float adjacency matrix
                - 'edges': list of (src, tgt, strength) tuples
                - 'dag': networkx DiGraph
                - 'method': 'notears' or 'correlation_fallback'
        """
        n = len(service_names)

        if X.shape[0] < 3 or X.shape[1] < 2:
            logger.warning("[DECI] Insufficient data — using correlation fallback")
            return self._correlation_fallback(X, service_names, W0)

        # Try NOTEARS with PyTorch
        if self._has_torch:
            try:
                adj = self._notears_linear(X, W0)
                return self._build_result(adj, service_names, method="notears_w0")
            except Exception as e:
                logger.warning(f"[DECI] NOTEARS failed: {e}. Using correlation fallback.")

        return self._correlation_fallback(X, service_names, W0)

    def _notears_linear(
        self,
        X: np.ndarray,
        W0: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """NOTEARS linear continuous optimization.

        Minimizes:
            ℓ(W) = (1/2n) ‖X - XW‖²_F + λ₁‖W‖₁ + λ₂ h(W)
            + α ‖(W - W0) ⊙ M‖² (when W0 provided)

        Returns:
            Adjacency matrix W of shape (N, N).
        """
        import torch
        import torch.optim as optim

        n = X.shape[1]
        X_t = torch.tensor(X, dtype=torch.float32)
        W = torch.zeros(n, n, requires_grad=True, dtype=torch.float32)

        if W0 is not None:
            W0_t = torch.tensor(W0, dtype=torch.float32)
            # Mask: only penalize edges where W0 has strong opinion
            M = (torch.abs(W0_t) > 0.2).float()
        else:
            W0_t = None
            M = None

        optimizer = optim.Adam([W], lr=self.lr)
        rho = 1.0    # Augmented Lagrangian rho
        alpha = 0.0  # Lagrangian multiplier

        for iteration in range(self.max_iter):
            optimizer.zero_grad()

            # Zero diagonal (no self-loops)
            W_masked = W * (1 - torch.eye(n))

            # Data fit loss: (1/2n) ‖X - X@W‖²
            X_hat = X_t @ W_masked
            data_loss = 0.5 / X.shape[0] * torch.sum((X_t - X_hat) ** 2)

            # L1 sparsity
            l1_loss = self.lambda1 * torch.sum(torch.abs(W_masked))

            # Acyclicity: h(W) = tr(e^(W∘W)) - n
            W_sq = W_masked * W_masked
            # Matrix exponential approximation via Taylor series (faster)
            h = torch.trace(torch.matrix_exp(W_sq)) - n

            # Augmented Lagrangian acyclicity term
            h_loss = (alpha * h + 0.5 * rho * h * h)

            # W0 prior loss
            prior_loss = torch.tensor(0.0)
            if W0_t is not None and M is not None:
                diff = (W_masked - W0_t) * M
                prior_loss = self.w0_alpha * torch.sum(diff ** 2)

            loss = data_loss + l1_loss + h_loss + prior_loss
            loss.backward()
            optimizer.step()

            # Update Lagrangian multiplier every 10 steps
            if iteration % 10 == 0:
                with torch.no_grad():
                    h_val = float(h.item())
                    alpha += rho * h_val
                    if abs(h_val) < self.h_tol:
                        break

        with torch.no_grad():
            adj = (W * (1 - torch.eye(n))).numpy()

        # Threshold small values
        adj[np.abs(adj) < 0.05] = 0.0
        # Keep only positive edges (W > 0 means i causes j)
        adj = np.maximum(adj, 0)

        return adj

    def _correlation_fallback(
        self,
        X: np.ndarray,
        service_names: List[str],
        W0: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Granger-style temporal correlation fallback.

        When NOTEARS fails, uses lagged correlation as a proxy for
        causality: corr(X_t[i], X_{t+1}[j]) > threshold → i causes j.
        """
        n = len(service_names)
        adj = np.zeros((n, n))

        if X.shape[0] > 1:
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    # Lagged correlation: does service i at t predict j at t+1?
                    xi = X[:-1, i]
                    xj = X[1:, j]
                    if np.std(xi) > 1e-8 and np.std(xj) > 1e-8:
                        corr = float(np.corrcoef(xi, xj)[0, 1])
                        adj[i][j] = max(0.0, corr)  # Only positive correlations

        # Inject W0 prior by blending
        if W0 is not None:
            w0_positive = np.maximum(W0, 0)
            adj = 0.5 * adj + 0.5 * w0_positive

        return self._build_result(adj, service_names, method="correlation_w0")

    def _build_result(
        self,
        adj: np.ndarray,
        service_names: List[str],
        method: str = "notears",
    ) -> Dict[str, Any]:
        """Convert adjacency matrix to structured result dict."""
        import networkx as nx

        n = len(service_names)
        G = nx.DiGraph()
        G.add_nodes_from(service_names)
        edges = []

        threshold = 0.15  # Minimum weight to be an edge

        for i in range(n):
            for j in range(n):
                if i != j and adj[i][j] > threshold:
                    src = service_names[i]
                    tgt = service_names[j]
                    strength = float(adj[i][j])
                    G.add_edge(src, tgt, weight=strength)
                    edges.append((src, tgt, strength))

        # Sort by strength
        edges.sort(key=lambda x: x[2], reverse=True)

        return {
            "adjacency": adj,
            "edges": edges,
            "dag": G,
            "method": method,
            "n_edges": len(edges),
        }


# Module-level singleton
deci_engine = DECIEngine()
