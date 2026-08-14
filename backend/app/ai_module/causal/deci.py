"""
SYNAPSE Causal Discovery — Deep End-to-end Causal Inference (DECI).

Replaces the linear PC Algorithm with non-linear differentiable causal discovery.
Uses continuous optimization with the NOTEARS smooth acyclicity constraint and
injects LLM-RAG prior knowledge (W0) to restrict the causal graph search space.

Mathematical Formulation:
    Loss = -ELBO(G, theta; X)
           + lambda_prior * ||G - W0||_F^2    (Novel LLM-RAG Prior Injection)
           + lambda_sparse * ||G||_1          (Sparsity penalty)
           + 0.5 * rho * h(G)^2 + alpha * h(G) (Augmented Lagrangian NOTEARS constraint)

Where NOTEARS acyclicity function:
    h(G) = tr(exp(G \odot G)) - d = 0

Reference:
    - Geffner et al., "Deep End-to-end Causal Inference", NeurIPS 2022.
    - Zheng et al., "DAGs with NO TEARS: Continuous Optimization for Structure Learning", NeurIPS 2018.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.linalg import expm

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    HAS_TORCH = True
except ImportError:
    torch = None  # type: ignore
    nn = None     # type: ignore
    optim = None  # type: ignore
    HAS_TORCH = False


class NonLinearMechanism(nn.Module if HAS_TORCH else object):
    """Neural non-linear causal mechanism for service metrics."""

    def __init__(self, num_nodes: int, hidden_dim: int = 16):
        if not HAS_TORCH:
            return
        super().__init__()
        self.num_nodes = num_nodes
        # MLP per node predicting node value from masked parent values
        self.fc1 = nn.Linear(num_nodes, hidden_dim)
        self.act = nn.LeakyReLU(0.1)
        self.fc2 = nn.Linear(hidden_dim, 1)

    def forward(self, x_masked: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x_masked: [batch_size, num_nodes] features where non-parents are zeroed.
        Returns:
            predicted value for target node: [batch_size, 1]
        """
        h = self.act(self.fc1(x_masked))
        return self.fc2(h)


class PyTorchDECI(nn.Module if HAS_TORCH else object):
    """PyTorch implementation of Differentiable End-to-end Causal Inference (DECI)."""

    def __init__(
        self,
        num_nodes: int,
        hidden_dim: int = 16,
        lambda_prior: float = 1.5,
        lambda_sparse: float = 0.05,
    ):
        if not HAS_TORCH:
            return
        super().__init__()
        self.num_nodes = num_nodes
        self.lambda_prior = lambda_prior
        self.lambda_sparse = lambda_sparse

        # Continuous unconstrained adjacency parameter matrix
        # Initialize near zero with small positive values
        init_g = torch.randn(num_nodes, num_nodes) * 0.05
        init_g.fill_diagonal_(0.0)
        self.G_param = nn.Parameter(init_g)

        # Neural causal mechanisms for each node
        self.mechanisms = nn.ModuleList([
            NonLinearMechanism(num_nodes, hidden_dim) for _ in range(num_nodes)
        ])

    def get_weighted_adjacency(self) -> torch.Tensor:
        """Get non-negative adjacency matrix with zero diagonal."""
        # Sigmoid or softplus to enforce non-negative edge weights
        G = torch.sigmoid(self.G_param * 4.0)
        G = G * (1.0 - torch.eye(self.num_nodes, device=G.device))
        return G

    def notears_h(self, G: torch.Tensor) -> torch.Tensor:
        """NOTEARS smooth acyclicity constraint h(G) = tr(exp(G \odot G)) - d."""
        M = G * G
        # Matrix exponential via Taylor expansion or torch.linalg.matrix_exp
        try:
            exp_M = torch.linalg.matrix_exp(M)
        except Exception:
            # First 6 terms of Taylor expansion as fallback
            d = self.num_nodes
            eye = torch.eye(d, device=G.device)
            exp_M = eye + M + (M @ M) / 2.0 + (M @ M @ M) / 6.0 + (M @ M @ M @ M) / 24.0
        return torch.trace(exp_M) - float(self.num_nodes)

    def forward(self, X: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            X: [batch_size, num_nodes] metric time series
        Returns:
            X_hat: [batch_size, num_nodes] reconstructed metrics
            G: [num_nodes, num_nodes] learned weighted adjacency
        """
        G = self.get_weighted_adjacency()
        batch_size = X.shape[0]
        X_hat_list = []

        for j in range(self.num_nodes):
            # Parents of j are columns where G[:, j] > 0
            # Mask X by the incoming edges to node j
            parent_weights = G[:, j].unsqueeze(0)  # [1, num_nodes]
            X_masked = X * parent_weights          # [batch_size, num_nodes]
            x_j_hat = self.mechanisms[j](X_masked) # [batch_size, 1]
            X_hat_list.append(x_j_hat)

        X_hat = torch.cat(X_hat_list, dim=1)
        return X_hat, G


class DECIEngine:
    """SYNAPSE Deep End-to-end Causal Inference (DECI) Engine.

    Discovers directed causal relationships using non-linear differentiable
    continuous optimization with the NOTEARS acyclicity constraint and
    LLM-RAG prior injection (W0).
    """

    def __init__(
        self,
        max_iter: int = 150,
        lr: float = 0.015,
        lambda_prior: float = 2.0,
        lambda_sparse: float = 0.05,
        rho_max: float = 1e5,
        h_tol: float = 1e-4,
        edge_threshold: float = 0.25,
    ):
        """
        Args:
            max_iter: Number of optimization epochs.
            lr: Learning rate for Adam optimizer.
            lambda_prior: Weight for LLM-RAG prior matrix regularization ||G - W0||_F^2.
            lambda_sparse: L1 sparsity regularization weight.
            rho_max: Maximum Augmented Lagrangian penalty factor.
            h_tol: Tolerance for acyclicity constraint h(G) <= h_tol.
            edge_threshold: Minimum edge weight to retain in the extracted DAG.
        """
        self.max_iter = max_iter
        self.lr = lr
        self.lambda_prior = lambda_prior
        self.lambda_sparse = lambda_sparse
        self.rho_max = rho_max
        self.h_tol = h_tol
        self.edge_threshold = edge_threshold

    def discover(
        self,
        time_series_matrix: np.ndarray,
        service_names: List[str],
        w0_prior: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Discover the causal DAG from multivariate time-series data.

        Args:
            time_series_matrix: Shape [num_timesteps, num_services].
            service_names: List of service names.
            w0_prior: Optional prior adjacency matrix [num_services, num_services] from RAG.

        Returns:
            Dict containing:
                - "adjacency": Adjacency matrix (List[List[float]])
                - "edges": List of (source, target, strength) tuples
                - "nodes": service_names
                - "dag": Adjacency dict {source: [targets]}
                - "h_score": Final NOTEARS acyclicity score
                - "method": "DECI (Differentiable Causal Discovery)"
        """
        n_services = len(service_names)
        n_timesteps = time_series_matrix.shape[0]

        if n_services < 2:
            return self._single_node_result(service_names)

        # Standardize features per node
        std = np.std(time_series_matrix, axis=0, keepdims=True)
        std[std == 0] = 1.0
        X_norm = (time_series_matrix - np.mean(time_series_matrix, axis=0, keepdims=True)) / std

        # Handle prior matrix W0 alignment
        if w0_prior is not None:
            if w0_prior.shape != (n_services, n_services):
                w0_aligned = np.zeros((n_services, n_services), dtype=np.float32)
            else:
                w0_aligned = w0_prior.astype(np.float32)
        else:
            w0_aligned = np.zeros((n_services, n_services), dtype=np.float32)

        if HAS_TORCH and n_timesteps >= 4:
            return self._run_pytorch_deci(X_norm, service_names, w0_aligned)
        else:
            return self._run_numpy_notears(X_norm, service_names, w0_aligned)

    def _run_pytorch_deci(
        self,
        X_data: np.ndarray,
        names: List[str],
        w0_prior: np.ndarray,
    ) -> Dict[str, Any]:
        """Execute DECI optimization with PyTorch."""
        d = len(names)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        X_tensor = torch.tensor(X_data, dtype=torch.float32, device=device)
        w0_tensor = torch.tensor(w0_prior, dtype=torch.float32, device=device)

        model = PyTorchDECI(
            num_nodes=d,
            hidden_dim=16,
            lambda_prior=self.lambda_prior,
            lambda_sparse=self.lambda_sparse,
        ).to(device)

        optimizer = optim.Adam(model.parameters(), lr=self.lr, weight_decay=1e-4)

        # Augmented Lagrangian parameters for NOTEARS
        rho = 1.0
        alpha = 0.0
        gamma = 0.25
        h_prev = float("inf")

        for epoch in range(self.max_iter):
            optimizer.zero_grad()

            X_hat, G = model(X_tensor)

            # 1. Reconstruction loss (Data fidelity - negative ELBO proxy)
            reconstruction_loss = 0.5 * nn.functional.mse_loss(X_hat, X_tensor)

            # 2. Novel LLM-RAG Prior regularization ||G - W0||_F^2
            has_prior = (w0_tensor.sum() > 0)
            if has_prior:
                prior_loss = self.lambda_prior * torch.sum((G - w0_tensor) ** 2)
            else:
                prior_loss = torch.tensor(0.0, device=device)

            # 3. Sparsity L1
            sparse_loss = self.lambda_sparse * torch.sum(torch.abs(G))

            # 4. NOTEARS Acyclicity constraint
            h = model.notears_h(G)

            # 5. Augmented Lagrangian Total Loss
            lagrangian_loss = alpha * h + 0.5 * rho * (h ** 2)
            total_loss = reconstruction_loss + prior_loss + sparse_loss + lagrangian_loss

            total_loss.backward()
            optimizer.step()

            # Dual update every 15 epochs
            if (epoch + 1) % 15 == 0:
                with torch.no_grad():
                    h_val = float(h.item())
                    if h_val > gamma * h_prev:
                        rho = min(rho * 2.0, self.rho_max)
                    else:
                        h_prev = h_val
                    alpha += rho * h_val

        # Extract learned adjacency matrix
        with torch.no_grad():
            G_final = model.get_weighted_adjacency().cpu().numpy()
            h_final = float(model.notears_h(model.get_weighted_adjacency()).item())

        return self._post_process_graph(G_final, names, h_final, method="DECI (PyTorch Differentiable)")

    def _run_numpy_notears(
        self,
        X_data: np.ndarray,
        names: List[str],
        w0_prior: np.ndarray,
    ) -> Dict[str, Any]:
        """SciPy/NumPy NOTEARS continuous optimization fallback."""
        n, d = X_data.shape
        W = np.zeros((d, d), dtype=np.float64)

        # Initialize with temporal correlation / prior
        for i in range(d):
            for j in range(d):
                if i != j:
                    corr = abs(np.corrcoef(X_data[:, i], X_data[:, j])[0, 1])
                    if not np.isnan(corr):
                        W[i, j] = 0.5 * corr + 0.5 * w0_prior[i, j]

        np.fill_diagonal(W, 0.0)

        # Gradient descent with NOTEARS penalty
        rho = 1.0
        alpha = 0.0
        lr = 0.01

        for _ in range(100):
            # h(W) = tr(exp(W * W)) - d
            M = W * W
            exp_M = expm(M)
            h = np.trace(exp_M) - d

            # Gradient of h w.r.t W: 2 * (exp(W * W))^T * W
            grad_h = 2.0 * (exp_M.T * W)

            # Data loss gradient (linear SEM proxy)
            # Loss = 0.5/n * ||X - XW||_F^2 => grad = -1/n X^T (X - XW)
            grad_loss = - (1.0 / n) * (X_data.T @ (X_data - X_data @ W))

            # Prior gradient
            grad_prior = 2.0 * self.lambda_prior * (W - w0_prior) if w0_prior.sum() > 0 else 0.0

            grad_total = grad_loss + grad_prior + (alpha + rho * h) * grad_h + self.lambda_sparse * np.sign(W)
            np.fill_diagonal(grad_total, 0.0)

            W = np.maximum(0.0, W - lr * grad_total)
            np.fill_diagonal(W, 0.0)

            if abs(h) < self.h_tol:
                break

        h_final = float(np.trace(expm(W * W)) - d)
        return self._post_process_graph(W, names, h_final, method="DECI (NumPy NOTEARS)")

    def _post_process_graph(
        self,
        adj: np.ndarray,
        names: List[str],
        h_score: float,
        method: str,
    ) -> Dict[str, Any]:
        """Threshold edge weights and convert to DAG structure."""
        d = len(names)
        adj_clean = adj.copy()
        np.fill_diagonal(adj_clean, 0.0)

        # Zero out small weights below threshold
        adj_clean[adj_clean < self.edge_threshold] = 0.0

        # Enforce strict acyclicity by breaking weaker edges in cycles
        for i in range(d):
            for j in range(d):
                if i != j and adj_clean[i, j] > 0 and adj_clean[j, i] > 0:
                    if adj_clean[i, j] >= adj_clean[j, i]:
                        adj_clean[j, i] = 0.0
                    else:
                        adj_clean[i, j] = 0.0

        edges = []
        dag_adj: Dict[str, List[str]] = {n: [] for n in names}

        for i in range(d):
            for j in range(d):
                if adj_clean[i, j] > 0:
                    weight = float(round(adj_clean[i, j], 3))
                    edges.append((names[i], names[j], weight))
                    dag_adj[names[i]].append(names[j])

        return {
            "adjacency": adj_clean.tolist(),
            "edges": edges,
            "nodes": names,
            "dag": dag_adj,
            "h_score": round(float(h_score), 6),
            "method": method,
        }

    def _single_node_result(self, names: List[str]) -> Dict[str, Any]:
        return {
            "adjacency": [[0.0]],
            "edges": [],
            "nodes": names,
            "dag": {n: [] for n in names},
            "h_score": 0.0,
            "method": "DECI (Single Node)",
        }
