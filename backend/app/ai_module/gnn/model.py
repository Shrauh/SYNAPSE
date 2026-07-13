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

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        return_attention: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """Forward pass through GAT encoder.

        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Graph connectivity [2, num_edges]
            return_attention: Whether to return attention weights

        Returns:
            Tuple of (embeddings [num_nodes, latent_dim], attention_weights or None)
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

        # Return final layer attention
        return z, attn_2


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

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        return_attention: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]:
        """Full forward pass: encode → decode.

        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Graph connectivity [2, num_edges]
            return_attention: Whether to return GAT attention weights

        Returns:
            Tuple of (reconstructed_x, embeddings, attention_weights)
        """
        z, attn = self.encoder(x, edge_index, return_attention=return_attention)
        x_hat = self.decoder(z)
        return x_hat, z, attn

    def compute_anomaly_scores(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """Compute per-node anomaly scores as reconstruction error.

        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Graph connectivity [2, num_edges]

        Returns:
            Anomaly scores [num_nodes] — values in [0, 1] (sigmoid-scaled)
        """
        self.eval()
        with torch.no_grad():
            x_hat, _, _ = self.forward(x, edge_index)
            # Per-node MSE
            mse_per_node = torch.mean((x - x_hat) ** 2, dim=1)
            # Scale to [0, 1] using sigmoid with temperature
            scores = torch.sigmoid(mse_per_node * 3.0 - 1.5)
        return scores

    def get_attention_weights(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> Optional[torch.Tensor]:
        """Extract attention weights for interpretability."""
        self.eval()
        with torch.no_grad():
            _, _, attn = self.forward(x, edge_index, return_attention=True)
        return attn


class FallbackAnomalyDetector:
    """Simple statistical anomaly detector (no PyG dependency).

    Used as fallback when torch-geometric is not installed.
    Computes z-score based anomaly scores per node.
    """

    def __init__(self):
        self._baseline_mean: Optional[torch.Tensor] = None
        self._baseline_std: Optional[torch.Tensor] = None

    def fit(self, feature_matrices: list) -> None:
        """Fit baseline statistics from list of normal feature matrices.

        Args:
            feature_matrices: List of tensors, each [num_nodes, num_features]
        """
        all_data = torch.stack(feature_matrices)  # [N, nodes, features]
        self._baseline_mean = all_data.mean(dim=0)  # [nodes, features]
        self._baseline_std = all_data.std(dim=0).clamp(min=1e-6)

    def compute_anomaly_scores(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor:
        """Compute z-score based anomaly scores.

        Args:
            x: Node features [num_nodes, num_features]

        Returns:
            Anomaly scores [num_nodes] in [0, 1]
        """
        if self._baseline_mean is None:
            # No baseline — use simple variance-based scoring
            mean = x.mean(dim=1, keepdim=True)
            std = x.std(dim=1, keepdim=True).clamp(min=1e-6)
            z_scores = ((x - mean) / std).abs().mean(dim=1)
            return torch.sigmoid(z_scores - 2.0)

        z_scores = ((x - self._baseline_mean) / self._baseline_std).abs()
        avg_z = z_scores.mean(dim=1)
        return torch.sigmoid(avg_z - 2.0)


def create_detector(use_gnn: bool = True, **kwargs) -> nn.Module:
    """Factory function to create the appropriate anomaly detector.

    Falls back to statistical detector if PyG is unavailable.
    """
    if use_gnn and HAS_PYG:
        return GATAnomalyDetector(**kwargs)
    else:
        return FallbackAnomalyDetector()
