"""
SYNAPSE GNN Inference — Anomaly Score Computation.

Takes the trained GAT autoencoder and computes per-service anomaly
scores for a given time window of metrics.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
try:
    import torch
    HAS_TORCH = True
except ImportError:
    torch = None  # type: ignore
    HAS_TORCH = False

from app.ai_module.gnn.model import GATAnomalyDetector, FallbackAnomalyDetector, HAS_PYG

if HAS_PYG:
    from torch_geometric.data import Data


class GNNInference:
    """Handles GNN-based anomaly score computation."""

    def __init__(self, model, device: Optional[str] = None):
        self.model = model
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if HAS_PYG and isinstance(model, GATAnomalyDetector):
            self.model.to(self.device)
        self._use_pyg = HAS_PYG and isinstance(model, GATAnomalyDetector)

    def compute_scores(
        self,
        feature_matrix: np.ndarray,
        edge_index: Optional[List[List[int]]] = None,
        service_names: Optional[List[str]] = None,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Compute anomaly scores for all services.

        Args:
            feature_matrix: Node features [num_nodes, num_features]
            edge_index: Edge connectivity [[sources], [targets]] (required for GNN)
            service_names: Ordered list of service names for the output dict

        Returns:
            Tuple of (scores_dict, uncertainty_dict) mapping service_name → value
        """
        x = torch.tensor(feature_matrix, dtype=torch.float32)
        uncertainty = None

        if self._use_pyg and edge_index is not None:
            x = x.to(self.device)
            ei = torch.tensor(edge_index, dtype=torch.long).to(self.device)
            scores, uncertainty = self.model.compute_anomaly_scores(x, ei)
        elif isinstance(self.model, FallbackAnomalyDetector):
            scores = self.model.compute_anomaly_scores(x)
        else:
            # Final fallback: use variance-based scoring
            mean = x.mean(dim=1)
            std = x.std(dim=1).clamp(min=1e-6)
            scores = torch.sigmoid(std / mean - 1.0)

        scores_np = scores.cpu().numpy()
        uncertainty_np = uncertainty.cpu().numpy() if uncertainty is not None else np.zeros_like(scores_np)

        if service_names is None:
            service_names = [f"service_{i}" for i in range(len(scores_np))]

        scores_dict = {
            name: float(round(score, 4))
            for name, score in zip(service_names, scores_np)
        }
        uncertainty_dict = {
            name: float(round(unc, 4))
            for name, unc in zip(service_names, uncertainty_np)
        }
        
        return scores_dict, uncertainty_dict

    def compute_scores_with_attention(
        self,
        feature_matrix: np.ndarray,
        edge_index: List[List[int]],
        service_names: List[str],
    ) -> Tuple[Dict[str, float], Dict[str, float], Optional[Dict]]:
        """Compute scores + attention weights for interpretability.

        Returns:
            Tuple of (anomaly_scores dict, uncertainty dict, attention_info dict or None)
        """
        scores, uncertainty = self.compute_scores(feature_matrix, edge_index, service_names)

        attention_info = None
        if self._use_pyg:
            x = torch.tensor(feature_matrix, dtype=torch.float32).to(self.device)
            ei = torch.tensor(edge_index, dtype=torch.long).to(self.device)
            attn = self.model.get_attention_weights(x, ei)
            if attn is not None:
                attention_info = {
                    "weights": attn.cpu().numpy().tolist(),
                    "edge_index": edge_index,
                }

        return scores, uncertainty, attention_info

    def get_top_anomalous(
        self,
        scores: Dict[str, float],
        threshold: float = 0.6,
        top_k: Optional[int] = None,
    ) -> List[Tuple[str, float]]:
        """Filter and rank anomalous services.

        Args:
            scores: Dict of service → anomaly_score.
            threshold: Minimum score to be considered anomalous.
            top_k: Optional limit on number of returned services.

        Returns:
            List of (service_name, score) sorted by score descending.
        """
        anomalous = [
            (svc, score)
            for svc, score in scores.items()
            if score >= threshold
        ]
        anomalous.sort(key=lambda x: x[1], reverse=True)

        if top_k is not None:
            anomalous = anomalous[:top_k]

        return anomalous
