"""
SYNAPSE Causal Discovery — PC Algorithm Wrapper for Root Cause Analysis.

Uses the PC algorithm (constraint-based causal discovery) from causal-learn
to determine directional cause-effect relationships between anomalous
services. Runs only on the anomalous subset (computational optimization).
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from causallearn.search.ConstraintBased.PC import pc
    from causallearn.utils.cit import chisq, fisherz, gsq, kci, mv_fisherz
    HAS_CAUSAL = True
except ImportError:
    HAS_CAUSAL = False


class CausalDiscoveryEngine:
    """Discovers causal structure among anomalous services using the PC algorithm."""

    def __init__(
        self,
        alpha: float = 0.05,
        indep_test: str = "fisherz",
    ):
        """
        Args:
            alpha: Significance level for conditional independence tests.
            indep_test: Independence test method ('fisherz', 'chisq', 'gsq', 'kci').
        """
        self.alpha = alpha
        self.indep_test = indep_test

    def discover(
        self,
        time_series_matrix: np.ndarray,
        service_names: List[str],
    ) -> Dict[str, Any]:
        """Run causal discovery on time-series of anomalous services.

        Args:
            time_series_matrix: Shape [num_timesteps, num_anomalous_services].
                Each column is the metric time-series for one anomalous service.
            service_names: Names of the anomalous services (column labels).

        Returns:
            Dict containing:
                - "adjacency": Adjacency matrix (numpy array)
                - "edges": List of (source, target, strength) tuples
                - "nodes": service_names
                - "dag": Adjacency as dict {source: [targets]}
        """
        n_services = len(service_names)
        n_timesteps = time_series_matrix.shape[0]

        # Need at least some data points for statistical tests
        if n_services < 2:
            return self._single_node_result(service_names)

        if n_timesteps < 5:
            return self._fallback_correlation(time_series_matrix, service_names)

        if HAS_CAUSAL:
            return self._run_pc_algorithm(time_series_matrix, service_names)
        else:
            return self._fallback_correlation(time_series_matrix, service_names)

    def _run_pc_algorithm(
        self,
        data: np.ndarray,
        names: List[str],
    ) -> Dict[str, Any]:
        """Run the PC algorithm using causal-learn.

        The PC algorithm discovers the causal DAG by:
        1. Starting with a fully connected undirected graph
        2. Removing edges via conditional independence tests
        3. Orienting remaining edges using v-structures and orientation rules
        """
        # Select the independence test
        test_map = {
            "fisherz": fisherz,
            "chisq": chisq,
            "gsq": gsq,
        }
        cit = test_map.get(self.indep_test, fisherz)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                result = pc(
                    data=data,
                    alpha=self.alpha,
                    indep_test=cit,
                    stable=True,
                    uc_rule=0,       # Standard orientation rules
                    uc_priority=2,   # Prioritize existing orientations
                    show_progress=False,
                )
                adj_matrix = result.G.graph  # Adjacency matrix
            except Exception:
                # PC failed (e.g., singular matrix) — fall back
                return self._fallback_correlation(data, names)

        # Parse edges from adjacency matrix
        # In causal-learn: adj[i,j] = -1 and adj[j,i] = 1 means i → j
        # adj[i,j] = -1 and adj[j,i] = -1 means i — j (undirected)
        edges = []
        dag_adj: Dict[str, List[str]] = {n: [] for n in names}

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if adj_matrix[i, j] == -1 and adj_matrix[j, i] == 1:
                    # i → j (directed)
                    strength = abs(np.corrcoef(data[:, i], data[:, j])[0, 1])
                    edges.append((names[i], names[j], float(round(strength, 3))))
                    dag_adj[names[i]].append(names[j])
                elif adj_matrix[i, j] == 1 and adj_matrix[j, i] == -1:
                    # j → i (directed)
                    strength = abs(np.corrcoef(data[:, i], data[:, j])[0, 1])
                    edges.append((names[j], names[i], float(round(strength, 3))))
                    dag_adj[names[j]].append(names[i])
                elif adj_matrix[i, j] == -1 and adj_matrix[j, i] == -1:
                    # Undirected — orient by temporal precedence (earlier anomaly → later)
                    # Use variance of first differences as proxy for which changed first
                    diff_i = np.diff(data[:, i])
                    diff_j = np.diff(data[:, j])
                    var_i = np.var(diff_i[:len(diff_i)//2])
                    var_j = np.var(diff_j[:len(diff_j)//2])
                    strength = abs(np.corrcoef(data[:, i], data[:, j])[0, 1])

                    if var_i > var_j:
                        edges.append((names[i], names[j], float(round(strength, 3))))
                        dag_adj[names[i]].append(names[j])
                    else:
                        edges.append((names[j], names[i], float(round(strength, 3))))
                        dag_adj[names[j]].append(names[i])

        return {
            "adjacency": adj_matrix.tolist() if hasattr(adj_matrix, 'tolist') else adj_matrix,
            "edges": edges,
            "nodes": names,
            "dag": dag_adj,
        }

    def _fallback_correlation(
        self,
        data: np.ndarray,
        names: List[str],
    ) -> Dict[str, Any]:
        """Fallback: use Granger-like temporal correlation to infer causality.

        For each pair of services, check if one's metric changes precede the other's.
        The service whose changes come first is the likely cause.
        """
        n = len(names)
        edges = []
        dag_adj: Dict[str, List[str]] = {n_: [] for n_ in names}

        for i in range(n):
            for j in range(i + 1, n):
                corr = abs(np.corrcoef(data[:, i], data[:, j])[0, 1])
                if corr < 0.3 or np.isnan(corr):
                    continue  # Not correlated enough

                # Temporal precedence: correlate lag-1 of i with j, and vice versa
                lag_corr_ij = abs(np.corrcoef(data[:-1, i], data[1:, j])[0, 1])
                lag_corr_ji = abs(np.corrcoef(data[:-1, j], data[1:, i])[0, 1])

                if np.isnan(lag_corr_ij):
                    lag_corr_ij = 0.0
                if np.isnan(lag_corr_ji):
                    lag_corr_ji = 0.0

                strength = float(round(corr, 3))
                if lag_corr_ij > lag_corr_ji + 0.05:
                    edges.append((names[i], names[j], strength))
                    dag_adj[names[i]].append(names[j])
                elif lag_corr_ji > lag_corr_ij + 0.05:
                    edges.append((names[j], names[i], strength))
                    dag_adj[names[j]].append(names[i])
                # If roughly equal, skip (ambiguous direction)

        return {
            "adjacency": None,
            "edges": edges,
            "nodes": names,
            "dag": dag_adj,
        }

    def _single_node_result(
        self, names: List[str]
    ) -> Dict[str, Any]:
        """Result when there's 0 or 1 anomalous node."""
        return {
            "adjacency": None,
            "edges": [],
            "nodes": names,
            "dag": {n: [] for n in names},
        }
