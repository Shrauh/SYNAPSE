"""
SYNAPSE GNN Graph Builder — NetworkX to PyTorch Geometric Conversion.

Converts the service dependency graph (NetworkX DiGraph) and feature
DataFrames into PyTorch Geometric Data objects for GNN input.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

try:
    from torch_geometric.data import Data
    HAS_PYG = True
except ImportError:
    HAS_PYG = False

from app.services.graph_builder import ServiceGraphBuilder

# Feature columns (must match ingestion service)
FEATURE_COLUMNS = ["latency", "error_rate", "cpu", "memory", "request_rate"]
NUM_FEATURES = len(FEATURE_COLUMNS)


def networkx_to_pyg(
    graph_builder: ServiceGraphBuilder,
    feature_matrix: np.ndarray,
    normalize: bool = False,
) -> "Data":
    """Convert NetworkX graph + feature matrix to PyG Data object.

    Args:
        graph_builder: The service graph builder instance.
        feature_matrix: Node features [num_nodes, num_features], ordered
            by graph_builder.service_names.
        normalize: Whether to z-score normalize features.

    Returns:
        PyG Data object with x (features) and edge_index.
    """
    if not HAS_PYG:
        raise ImportError("torch_geometric required. Install with: pip install torch-geometric")

    edge_index_list, node_map = graph_builder.get_edge_index_tensor()

    # Convert features to tensor
    x = torch.tensor(feature_matrix, dtype=torch.float32)

    if normalize:
        mean = x.mean(dim=0, keepdim=True)
        std = x.std(dim=0, keepdim=True).clamp(min=1e-8)
        x = (x - mean) / std

    # Edge index tensor
    edge_index = torch.tensor(edge_index_list, dtype=torch.long)

    data = Data(x=x, edge_index=edge_index)
    data.num_nodes = len(node_map)

    return data


def features_from_dataframe(
    df,  # pd.DataFrame
    service_order: List[str],
) -> np.ndarray:
    """Extract feature matrix from an aggregated DataFrame.

    Expects one row per service with FEATURE_COLUMNS.

    Args:
        df: Aggregated DataFrame with 'service' column and feature columns.
        service_order: Ordered list of service names.

    Returns:
        numpy array of shape (num_services, num_features).
    """
    matrix = np.zeros((len(service_order), NUM_FEATURES))
    svc_to_idx = {svc: i for i, svc in enumerate(service_order)}

    for _, row in df.iterrows():
        svc = row["service"]
        if svc in svc_to_idx:
            idx = svc_to_idx[svc]
            for j, col in enumerate(FEATURE_COLUMNS):
                if col in row.index:
                    matrix[idx, j] = float(row[col])

    return matrix


def build_pyg_data(
    graph_builder: ServiceGraphBuilder,
    df,  # pd.DataFrame — aggregated metrics
    normalize: bool = True,
) -> "Data":
    """One-step convenience: DataFrame + graph → PyG Data.

    Args:
        graph_builder: Graph builder instance.
        df: Aggregated metrics DataFrame.
        normalize: Whether to normalize features.

    Returns:
        PyG Data object ready for GNN inference.
    """
    service_order = graph_builder.service_names
    feature_matrix = features_from_dataframe(df, service_order)
    return networkx_to_pyg(graph_builder, feature_matrix, normalize=normalize)


def build_feature_tensor(
    feature_matrix: np.ndarray,
    normalize: bool = True,
) -> torch.Tensor:
    """Convert raw feature matrix to normalized tensor (no PyG needed).

    Args:
        feature_matrix: numpy array [num_nodes, num_features]
        normalize: Whether to z-score normalize.

    Returns:
        Tensor of shape [num_nodes, num_features]
    """
    x = torch.tensor(feature_matrix, dtype=torch.float32)
    if normalize:
        mean = x.mean(dim=0, keepdim=True)
        std = x.std(dim=0, keepdim=True).clamp(min=1e-8)
        x = (x - mean) / std
    return x
