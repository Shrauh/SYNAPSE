"""
SYNAPSE Multi-Root-Cause Detection — Cluster-Level Causal Analysis.

For Level 3 systemic failures where 4+ services are anomalous and
no single confident root cause exists. Decomposes the problem into
service clusters and analyzes each independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from app.ai_module.causal.dag_utils import break_cycles, get_root_nodes
from app.ai_module.causal.discovery import CausalDiscoveryEngine


@dataclass
class ClusterRCA:
    """RCA result for a single service cluster."""
    cluster_id: int
    services: List[str]
    root_cause: Optional[str]
    confidence: float
    causal_edges: List[Tuple[str, str, float]]
    propagation_chain: List[str]


@dataclass
class MultiRootResult:
    """Combined result from multi-root-cause analysis."""
    num_clusters: int
    clusters: List[ClusterRCA]
    root_causes: List[str]  # All identified root causes
    overall_confidence: float
    is_multi_root: bool
    summary: str


class MultiRootCauseDetector:
    """Detects multiple simultaneous root causes in systemic failures.
    
    When 4+ services are anomalous and DECI/PC can't find a single
    confident root cause, this module:
    1. Clusters anomalous services by their topology connectivity
    2. Runs independent causal analysis on each cluster
    3. Identifies per-cluster root causes
    4. Merges results into a unified multi-root report
    """
    
    def __init__(self):
        """Initialize the multi-root cause detector."""
        self._causal_engine = CausalDiscoveryEngine(alpha=0.05)
    
    def decompose_into_clusters(
        self, 
        anomalous_services: List[str], 
        anomaly_scores: Dict[str, float], 
        topology: nx.DiGraph
    ) -> List[List[str]]:
        """Decompose anomalous services into connected clusters based on topology.
        
        Uses the service dependency graph to find groups of anomalous services
        that are directly connected. Each disconnected group becomes a cluster.
        
        Args:
            anomalous_services: List of anomalous service names.
            anomaly_scores: Dict of service -> anomaly score.
            topology: NetworkX DiGraph of service dependencies.
            
        Returns:
            List of clusters, where each cluster is a list of service names.
        """
        # Build subgraph of anomalous services only
        subgraph = topology.subgraph(anomalous_services).copy()
        
        # Find weakly connected components (clusters)
        components = list(nx.weakly_connected_components(subgraph))
        
        # If everything is one big connected component, try splitting by
        # removing the weakest edges (lowest anomaly score nodes)
        if len(components) == 1 and len(anomalous_services) >= 6:
            # Split into 2 clusters by median anomaly score
            sorted_services = sorted(anomalous_services, key=lambda s: anomaly_scores.get(s, 0), reverse=True)
            mid = len(sorted_services) // 2
            components = [set(sorted_services[:mid]), set(sorted_services[mid:])]
        
        # Convert sets to sorted lists
        clusters = [sorted(list(c)) for c in components]
        
        # Remove single-service clusters (those are L1, not multi-root)
        # But keep them if that's all we have
        if len(clusters) > 1:
            clusters = [c for c in clusters if len(c) >= 2] or clusters
        
        return clusters
    
    def analyze_cluster(
        self, 
        cluster_id: int, 
        services: List[str], 
        time_series_matrix: np.ndarray, 
        anomaly_scores: Dict[str, float]
    ) -> ClusterRCA:
        """Run causal analysis on a single cluster of services.
        
        Args:
            cluster_id: Unique identifier for this cluster.
            services: Service names in this cluster.
            time_series_matrix: Time-series data [timesteps x num_services].
            anomaly_scores: Dict of service -> anomaly score.
            
        Returns:
            ClusterRCA with root cause and causal edges for this cluster.
        """
        if len(services) < 2:
            # Single service cluster — it's its own root cause
            return ClusterRCA(
                cluster_id=cluster_id,
                services=services,
                root_cause=services[0] if services else None,
                confidence=anomaly_scores.get(services[0], 0.0) if services else 0.0,
                causal_edges=[],
                propagation_chain=services,
            )
        
        # Run causal discovery on this cluster
        causal_result = self._causal_engine.discover(
            time_series_matrix=time_series_matrix,
            service_names=services,
        )
        
        dag = causal_result.get('dag', {})
        edges = causal_result.get('edges', [])
        
        # Break cycles
        cluster_scores = {s: anomaly_scores.get(s, 0) for s in services}
        dag = break_cycles(dag, cluster_scores)
        
        # Find root cause
        root_candidates = get_root_nodes(dag, cluster_scores)
        root_cause = root_candidates[0][0] if root_candidates else services[0]
        confidence = root_candidates[0][1] if root_candidates else 0.0
        
        # Build propagation chain
        chain = [root_cause]
        visited = {root_cause}
        current = root_cause
        while current in dag:
            neighbors = [n for n in dag[current] if n not in visited]
            if not neighbors:
                break
            next_node = max(neighbors, key=lambda n: anomaly_scores.get(n, 0))
            chain.append(next_node)
            visited.add(next_node)
            current = next_node
        
        return ClusterRCA(
            cluster_id=cluster_id,
            services=services,
            root_cause=root_cause,
            confidence=confidence,
            causal_edges=edges,
            propagation_chain=chain,
        )
    
    def analyze(
        self, 
        anomalous_services: List[str], 
        anomaly_scores: Dict[str, float], 
        topology: nx.DiGraph, 
        time_series_data: Dict[str, np.ndarray]
    ) -> MultiRootResult:
        """Full multi-root-cause analysis pipeline.
        
        Args:
            anomalous_services: List of anomalous service names.
            anomaly_scores: Dict of service -> anomaly score.
            topology: NetworkX DiGraph of service dependencies.
            time_series_data: Dict mapping service name -> 1D time-series array.
            
        Returns:
            MultiRootResult with all identified root causes and clusters.
        """
        # Step 1: Decompose into clusters
        clusters = self.decompose_into_clusters(anomalous_services, anomaly_scores, topology)
        
        # Step 2: Analyze each cluster
        cluster_results = []
        for idx, cluster_services in enumerate(clusters):
            # Build time-series matrix for this cluster
            ts_cols = []
            for svc in cluster_services:
                if svc in time_series_data:
                    ts_cols.append(time_series_data[svc])
                else:
                    # Generate zero signal as fallback
                    ts_cols.append(np.zeros(60))
            
            ts_matrix = np.column_stack(ts_cols) if ts_cols else np.zeros((60, len(cluster_services)))
            # Add small noise
            ts_matrix += np.random.normal(0, 1e-6, ts_matrix.shape)
            
            cluster_rca = self.analyze_cluster(idx, cluster_services, ts_matrix, anomaly_scores)
            cluster_results.append(cluster_rca)
        
        # Step 3: Merge results
        root_causes = [c.root_cause for c in cluster_results if c.root_cause]
        overall_confidence = np.mean([c.confidence for c in cluster_results]) if cluster_results else 0.0
        is_multi_root = len(root_causes) > 1
        
        if is_multi_root:
            summary = f"Multiple root causes detected across {len(clusters)} clusters: {', '.join(root_causes)}"
        elif root_causes:
            summary = f"Single root cause: {root_causes[0]} (despite {len(anomalous_services)} anomalous services)"
        else:
            summary = "Unable to determine root cause"
        
        return MultiRootResult(
            num_clusters=len(clusters),
            clusters=cluster_results,
            root_causes=root_causes,
            overall_confidence=float(overall_confidence),
            is_multi_root=is_multi_root,
            summary=summary,
        )

# Module-level singleton
multi_root_detector = MultiRootCauseDetector()
