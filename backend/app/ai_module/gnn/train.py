"""
SYNAPSE GNN Training — Autoencoder training loop.

Trains the GAT autoencoder on normal-behavior data to learn baseline
feature reconstruction. High reconstruction error at inference time
indicates anomalous behavior.

Training approach: Self-supervised (autoencoder reconstruction).
Loss: MSE between input features and reconstructed features.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from app.ai_module.gnn.model import GATAnomalyDetector, FallbackAnomalyDetector, HAS_PYG

if HAS_PYG:
    from torch_geometric.data import Data


class GNNTrainer:
    """Training manager for the GAT anomaly detector."""

    def __init__(
        self,
        in_features: int = 5,
        hidden_dim: int = 32,
        latent_dim: int = 16,
        heads: int = 4,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-5,
        device: Optional[str] = None,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        if HAS_PYG:
            self.model = GATAnomalyDetector(
                in_features=in_features,
                hidden_dim=hidden_dim,
                latent_dim=latent_dim,
                heads=heads,
            ).to(self.device)
            self.optimizer = optim.Adam(
                self.model.parameters(),
                lr=learning_rate,
                weight_decay=weight_decay,
            )
        else:
            self.model = FallbackAnomalyDetector()
            self.optimizer = None

        self.criterion = nn.MSELoss()
        self.training_losses: List[float] = []
        self._trained = False

    @property
    def is_trained(self) -> bool:
        return self._trained

    def train_epoch(
        self,
        data_list: List["Data"],
    ) -> float:
        """Train one epoch over a list of PyG Data objects.

        Args:
            data_list: List of PyG Data objects (normal behavior windows).

        Returns:
            Average loss for this epoch.
        """
        if not HAS_PYG:
            # Fallback: fit statistical model
            matrices = [d.x for d in data_list]
            self.model.fit(matrices)
            self._trained = True
            return 0.0

        self.model.train()
        total_loss = 0.0

        for data in data_list:
            data = data.to(self.device)
            self.optimizer.zero_grad()

            x_hat, z, _ = self.model(data.x, data.edge_index)
            loss = self.criterion(x_hat, data.x)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / max(len(data_list), 1)
        self.training_losses.append(avg_loss)
        self._trained = True
        return avg_loss

    def train(
        self,
        data_list: List["Data"],
        epochs: int = 50,
        early_stop_patience: int = 10,
        verbose: bool = True,
    ) -> Dict[str, float]:
        """Full training loop with early stopping.

        Args:
            data_list: Training data (normal behavior windows).
            epochs: Maximum number of epochs.
            early_stop_patience: Stop if loss doesn't improve for N epochs.
            verbose: Print progress.

        Returns:
            Dict with training stats.
        """
        best_loss = float("inf")
        patience_counter = 0
        best_state = None

        for epoch in range(epochs):
            loss = self.train_epoch(data_list)

            if loss < best_loss:
                best_loss = loss
                patience_counter = 0
                if HAS_PYG:
                    best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
            else:
                patience_counter += 1

            if verbose and (epoch % 10 == 0 or epoch == epochs - 1):
                print(f"  Epoch {epoch+1}/{epochs} — Loss: {loss:.6f} (best: {best_loss:.6f})")

            if patience_counter >= early_stop_patience:
                if verbose:
                    print(f"  Early stopping at epoch {epoch+1}")
                break

        # Restore best model
        if best_state is not None and HAS_PYG:
            self.model.load_state_dict(best_state)

        return {
            "final_loss": best_loss,
            "epochs_trained": len(self.training_losses),
            "early_stopped": patience_counter >= early_stop_patience,
        }

    def save_model(self, path: str) -> None:
        """Save model weights to disk."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if HAS_PYG:
            torch.save({
                "model_state": self.model.state_dict(),
                "training_losses": self.training_losses,
            }, path)
        print(f"  Model saved to {path}")

    def load_model(self, path: str) -> bool:
        """Load model weights from disk.

        Returns:
            True if loaded successfully, False otherwise.
        """
        if not os.path.exists(path) or not HAS_PYG:
            return False

        try:
            checkpoint = torch.load(path, map_location=self.device, weights_only=False)
            self.model.load_state_dict(checkpoint["model_state"])
            self.training_losses = checkpoint.get("training_losses", [])
            self._trained = True
            print(f"  Model loaded from {path}")
            return True
        except Exception as e:
            print(f"  Failed to load model: {e}")
            return False

    def get_model(self):
        """Return the underlying model."""
        return self.model
