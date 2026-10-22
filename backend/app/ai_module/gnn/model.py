"""
SYNAPSE GNN — Graph Attention Network Autoencoder for Anomaly Detection.

Architecture:
    Encoder: 2-layer GAT → latent embeddings
    Decoder: MLP reconstructing input features from embeddings

Anomaly scoring: reconstruction error per node — high error = anomalous.
Attention weights provide interpretability (which neighbors influenced the score).
"""

from __future__ import annotations

from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from torch_geometric.nn import GATConv
    HAS_PYG = True
except ImportError:
    HAS_PYG = False


class GATEncoder(nn.Module):
    """2-layer Graph Attention Network encoder.

    Produces per-node latent embeddings from input features using
    multi-head attention over the graph structure.
    """

    def __init__(
        self,
        in_features: int = 5,
        hidden_dim: int = 32,
        latent_dim: int = 16,
        heads: int = 4,
        dropout: float = 0.2,
    ):
        super().__init__()
        if not HAS_PYG:
            raise ImportError(
                "torch_geometric is required for GNN. "
                "Install with: pip install torch-geometric"
            )

        self.conv1 = GATConv(
            in_channels=in_features,
            out_channels=hidden_dim,
            heads=heads,
            dropout=dropout,
            concat=True,
        )
        self.conv2 = GATConv(
            in_channels=hidden_dim * heads,
            out_channels=latent_dim,
            heads=1,
            dropout=dropout,
            concat=False,
        )
        self.dropout = nn.Dropout(dropout)
        self.norm1 = nn.LayerNorm(hidden_dim * heads)
        self.norm2 = nn.LayerNorm(latent_dim)
        
        self.mu_layer = nn.Linear(latent_dim, latent_dim)
        self.logvar_layer = nn.Linear(latent_dim, latent_dim)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        return_attention: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], torch.Tensor, torch.Tensor]:
        """Forward pass through GAT encoder.

        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Graph connectivity [2, num_edges]
            return_attention: Whether to return attention weights

        Returns:
            Tuple of (embeddings [num_nodes, latent_dim], attention_weights or None, mu, logvar)
        """
        # Layer 1
        if return_attention:
            h, (edge_idx_1, attn_1) = self.conv1(
                x, edge_index, return_attention_weights=True
            )
        else:
            h = self.conv1(x, edge_index)
            attn_1 = None

        h = self.norm1(h)
        h = F.elu(h)
        h = self.dropout(h)

        # Layer 2
        if return_attention:
            z, (edge_idx_2, attn_2) = self.conv2(
                h, edge_index, return_attention_weights=True
            )
        else:
            z = self.conv2(h, edge_index)
            attn_2 = None

        z = self.norm2(z)
        
        mu = self.mu_layer(z)
        logvar = self.logvar_layer(z)

        # Return final layer attention
        return z, attn_2, mu, logvar


class FeatureDecoder(nn.Module):
    """MLP decoder that reconstructs input features from latent embeddings."""

    def __init__(
        self,
        latent_dim: int = 16,
        hidden_dim: int = 32,
        out_features: int = 5,
    ):
        super().__init__()
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ELU(),
            nn.Linear(hidden_dim, out_features),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """Reconstruct features from latent embeddings.

        Args:
            z: Latent embeddings [num_nodes, latent_dim]

        Returns:
            Reconstructed features [num_nodes, out_features]
        """
        return self.decoder(z)


class GATAnomalyDetector(nn.Module):
    """Complete GAT Autoencoder for anomaly detection.

    Encoder: GAT layers learn topology-aware embeddings
    Decoder: MLP reconstructs original features
    Anomaly score = per-node reconstruction error
    """

    def __init__(
        self,
        in_features: int = 5,
        hidden_dim: int = 32,
        latent_dim: int = 16,
        heads: int = 4,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.encoder = GATEncoder(
            in_features=in_features,
            hidden_dim=hidden_dim,
            latent_dim=latent_dim,
            heads=heads,
            dropout=dropout,
        )
        self.decoder = FeatureDecoder(
            latent_dim=latent_dim,
            hidden_dim=hidden_dim,
            out_features=in_features,
        )
        self.in_features = in_features
        self.latent_dim = latent_dim

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Reparameterize latent embeddings."""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        return_attention: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor], torch.Tensor, torch.Tensor]:
        """Full forward pass: encode → decode.

        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Graph connectivity [2, num_edges]
            return_attention: Whether to return GAT attention weights

        Returns:
            Tuple of (reconstructed_x, embeddings, attention_weights, mu, logvar)
        """
        z_raw, attn, mu, logvar = self.encoder(x, edge_index, return_attention=return_attention)
        if self.training:
            z = self.reparameterize(mu, logvar)
        else:
            z = mu
        x_hat = self.decoder(z)
        return x_hat, z, attn, mu, logvar

    def compute_loss(self, x: torch.Tensor, edge_index: torch.Tensor, beta: float = 0.5) -> torch.Tensor:
        """Compute VAE loss combining reconstruction and KL divergence."""
        x_hat, _, _, mu, logvar = self.forward(x, edge_index)
        recon_loss = F.mse_loss(x_hat, x)
        kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
        return recon_loss + beta * kl_loss

    def compute_anomaly_scores(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute per-node anomaly scores as reconstruction error and uncertainty.

        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Graph connectivity [2, num_edges]

        Returns:
            Tuple of (Anomaly scores [num_nodes], uncertainty [num_nodes])
        """
        self.eval()
        with torch.no_grad():
            x_hat, _, _, mu, logvar = self.forward(x, edge_index)
            # Per-node MSE
            mse_per_node = torch.mean((x - x_hat) ** 2, dim=1)
            # Scale to [0, 1] using sigmoid with temperature
            scores = torch.sigmoid(mse_per_node * 3.0 - 1.5)
            # Uncertainty
            uncertainty = logvar.exp().mean(dim=1)
        return scores, uncertainty

    def get_attention_weights(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> Optional[torch.Tensor]:
        """Extract attention weights for interpretability."""
        self.eval()
        with torch.no_grad():
            _, _, attn, _, _ = self.forward(x, edge_index, return_attention=True)
        return attn


class FallbackAnomalyDetector:
    """Calibrated statistical anomaly detector (no PyG dependency).

    Each service's anomaly score reflects how abnormal it is relative
    to its OWN baseline - not compared to other services. This prevents
    services with inherently extreme metrics (e.g., database with
    request_rate=800) from always dominating the anomaly ranking.

    Supports dynamic topologies by mapping active services to simulator baselines.
    """

    def __init__(self):
        self._baseline_mean = None   # [nodes, features]
        self._baseline_std = None    # [nodes, features]
        self._normal_maxz_mean = None  # [nodes] - each service's normal max-z
        self._normal_maxz_std = None   # [nodes] - std of each service's normal max-z
        self._service_baselines = {}
        self._init_simulator_baselines()

    def _init_simulator_baselines(self) -> None:
        """Initialize default baselines from simulator constants."""
        try:
            from data.simulator import BASELINES
            from app.services.ingestion import FEATURE_COLUMNS
            for svc, b in BASELINES.items():
                mean = torch.tensor([b[col] for col in FEATURE_COLUMNS], dtype=torch.float32)
                std = (mean * 0.08).clamp(min=0.1)
                self._service_baselines[svc] = {
                    "mean": mean,
                    "std": std,
                    "normal_maxz_mean": torch.tensor(1.5),
                    "normal_maxz_std": torch.tensor(0.5),
                }
        except Exception:
            pass

    def fit(self, feature_matrices: list, service_names=None) -> None:
        """Fit baseline statistics from list of normal feature matrices.

        Args:
            feature_matrices: List of tensors, ndarrays, or objects with .x
            service_names: Optional list of service names corresponding to rows
        """
        import numpy as np
        converted = []
        for fm in feature_matrices:
            val = fm.x if hasattr(fm, "x") else fm
            if isinstance(val, np.ndarray):
                converted.append(torch.tensor(val, dtype=torch.float32))
            elif isinstance(val, torch.Tensor):
                converted.append(val.float())
            else:
                converted.append(torch.as_tensor(val, dtype=torch.float32))

        all_data = torch.stack(converted)  # [N, nodes, features]
        self._baseline_mean = all_data.mean(dim=0)  # [nodes, features]
        self._baseline_std = all_data.std(dim=0).clamp(min=1e-6)

        # Calibrate: compute each service's normal max-z distribution
        normal_maxzs = []
        for fm in converted:
            z = ((fm - self._baseline_mean) / self._baseline_std).abs()
            normal_maxzs.append(z.max(dim=1).values)
        stacked = torch.stack(normal_maxzs)  # [N, nodes]
        self._normal_maxz_mean = stacked.mean(dim=0)   # [nodes]
        self._normal_maxz_std = stacked.std(dim=0).clamp(min=0.5)  # [nodes]

        names = service_names
        if not names and self._baseline_mean.shape[0] == 10:
            try:
                from app.services.graph_builder import graph_builder
                names = graph_builder.service_names
            except Exception:
                pass

        if names and len(names) == self._baseline_mean.shape[0]:
            for idx, name in enumerate(names):
                self._service_baselines[name] = {
                    "mean": self._baseline_mean[idx],
                    "std": self._baseline_std[idx],
                    "normal_maxz_mean": self._normal_maxz_mean[idx],
                    "normal_maxz_std": self._normal_maxz_std[idx],
                }

    def compute_anomaly_scores(self, x, service_names=None) -> torch.Tensor:
        """Compute CALIBRATED anomaly scores.

        For each service, computes max z-score across features relative to its own baseline.
        """
        import numpy as np
        if isinstance(x, np.ndarray):
            x = torch.tensor(x, dtype=torch.float32)
        elif not isinstance(x, torch.Tensor):
            x = torch.as_tensor(x, dtype=torch.float32)

        # Per-service baseline lookup (preferred for dynamic topologies)
        if service_names and len(service_names) == x.shape[0]:
            try:
                from app.services.system_switcher import map_to_simulator
                scores = []
                for i, s in enumerate(service_names):
                    sim_s = map_to_simulator(s)
                    base = self._service_baselines.get(s) or self._service_baselines.get(sim_s)
                    if base is not None:
                        mean = base["mean"].to(x.device)
                        std = base["std"].to(x.device)
                        z = ((x[i] - mean) / std).abs()
                        max_z = z.max()
                        norm_mean = base.get("normal_maxz_mean", 1.5)
                        norm_std = base.get("normal_maxz_std", 0.5)
                        cal = ((max_z - norm_mean) / norm_std).clamp(min=0.0)
                        scores.append(cal)
                    else:
                        scores.append(torch.tensor(0.0, device=x.device))
                return torch.stack(scores)
            except Exception:
                pass

        if self._baseline_mean is None or self._baseline_mean.shape[0] != x.shape[0]:
            # No baseline - use per-feature cross-service normalization
            mean = x.mean(dim=0, keepdim=True)
            std = x.std(dim=0, keepdim=True).clamp(min=1e-6)
            z_scores = ((x - mean) / std).abs()
            return z_scores.max(dim=1).values

        z_scores = ((x - self._baseline_mean) / self._baseline_std).abs()
        max_z = z_scores.max(dim=1).values  # [nodes]

        # Calibrate: how many std-devs above normal is this service?
        if self._normal_maxz_mean is not None:
            calibrated = (max_z - self._normal_maxz_mean) / self._normal_maxz_std
            # Clamp to [0, inf) - negative means below normal, not anomalous
            calibrated = calibrated.clamp(min=0.0)
            return calibrated

        return max_z

def create_detector(use_gnn: bool = True, **kwargs) -> nn.Module:
    """Factory function to create the appropriate anomaly detector.

    Falls back to statistical detector if PyG is unavailable.
    """
    if use_gnn and HAS_PYG:
        return GATAnomalyDetector(**kwargs)
    else:
        return FallbackAnomalyDetector()
