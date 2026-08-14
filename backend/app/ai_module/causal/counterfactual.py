"""
SYNAPSE Counterfactual Engine — Do-Calculus Interventional Reasoning.

Implements Pearl's do-calculus to answer counterfactual questions:
  "If we had fixed service X, what would have happened to Y?"

Uses the discovered causal DAG to:
  1. Compute interventional distributions P(Y | do(X = x))
  2. Estimate counterfactual impact of each root cause
  3. Rank services by how much fixing them would reduce downstream anomalies

References:
    - Pearl, J. (2000). Causality.
    - Peters et al. (2017). Elements of Causal Inference.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


class CounterfactualEngine:
    """Do-calculus counterfactual analysis on a causal DAG.

    Given a discovered DAG and current anomaly scores, computes
    counterfactual scenarios: "if service X were fixed, what
    would the expected reduction in overall anomaly score be?"
    """

    def __init__(self) -> None:
        pass

    def compute_interventional_effect(
        self,
        dag: nx.DiGraph,
        anomaly_scores: Dict[str, float],
        intervention_service: str,
        intervention_value: float = 0.0,
    ) -> Dict[str, float]:
        """Compute P(Y | do(intervention_service = intervention_value)).

        Simulates an intervention (e.g., fixing a service) by:
        1. Removing all incoming edges to the intervened node (do-operator)
        2. Propagating the new value through the causal graph
        3. Computing expected change in all downstream node values

        Args:
            dag: Directed causal graph (service dependencies).
            anomaly_scores: Current anomaly scores per service.
            intervention_service: Service being "fixed" (do(X = x)).
            intervention_value: Anomaly value after intervention (default 0.0 = fixed).

        Returns:
            Dict mapping each service to its counterfactual anomaly score.
        """
        if intervention_service not in dag.nodes:
            return dict(anomaly_scores)

        # Mutilated graph: remove incoming edges to intervention node
        mutilated = dag.copy()
        in_edges = list(mutilated.in_edges(intervention_service))
        mutilated.remove_edges_from(in_edges)

        # Start with intervention value
        counterfactual = dict(anomaly_scores)
        counterfactual[intervention_service] = intervention_value

        # Propagate through descendants using topological order
        try:
            topo_order = list(nx.topological_sort(mutilated))
        except nx.NetworkXUnfeasible:
            # Cycle exists — use BFS from intervention node
            topo_order = list(nx.bfs_tree(mutilated, intervention_service).nodes())

        # Propagation model: descendant anomaly reduces proportionally
        for node in topo_order:
            if node == intervention_service:
                continue

            predecessors = list(mutilated.predecessors(node))
            if not predecessors:
                continue

            # Weighted influence from predecessors
            total_weight = 0.0
            weighted_sum = 0.0
            for pred in predecessors:
                edge_weight = float(mutilated[pred][node].get("weight", 0.5))
                pred_score = counterfactual.get(pred, anomaly_scores.get(pred, 0.0))
                weighted_sum += edge_weight * pred_score
                total_weight += edge_weight

            if total_weight > 0:
                predecessor_influence = weighted_sum / total_weight
                # Node's score = blend of its own score and predecessor influence
                original_score = anomaly_scores.get(node, 0.0)
                # Causal attribution: what fraction is due to predecessors?
                causal_fraction = min(1.0, total_weight)
                counterfactual[node] = (
                    (1 - causal_fraction) * original_score
                    + causal_fraction * predecessor_influence * 0.7  # 70% propagation
                )

        return counterfactual

    def rank_interventions(
        self,
        dag: nx.DiGraph,
        anomaly_scores: Dict[str, float],
        candidates: Optional[List[str]] = None,
    ) -> List[Tuple[str, float, Dict[str, float]]]:
        """Rank services by counterfactual impact of fixing them.

        For each candidate service, computes the total anomaly reduction
        if that service were fixed (do(X = 0)).

        Args:
            dag: Directed causal graph.
            anomaly_scores: Current anomaly scores.
            candidates: Services to consider (default: all nodes).

        Returns:
            List of (service, impact_score, counterfactual_scores) sorted
            by impact_score descending (higher = fixing this helps more).
        """
        if candidates is None:
            candidates = list(dag.nodes())

        total_current = sum(anomaly_scores.values())
        if total_current == 0:
            return [(svc, 0.0, anomaly_scores) for svc in candidates]

        results = []
        for svc in candidates:
            counterfactual = self.compute_interventional_effect(
                dag=dag,
                anomaly_scores=anomaly_scores,
                intervention_service=svc,
                intervention_value=0.0,
            )
            total_counterfactual = sum(counterfactual.values())
            impact = (total_current - total_counterfactual) / total_current
            impact = max(0.0, impact)  # Can't be negative
            results.append((svc, float(impact), counterfactual))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def explain_counterfactual(
        self,
        original_scores: Dict[str, float],
        counterfactual_scores: Dict[str, float],
        intervention_service: str,
    ) -> str:
        """Generate a human-readable counterfactual explanation.

        Args:
            original_scores: Anomaly scores before intervention.
            counterfactual_scores: Anomaly scores after intervention.
            intervention_service: The service that was hypothetically fixed.

        Returns:
            Plain-English explanation of the counterfactual analysis.
        """
        improvements = []
        for svc in counterfactual_scores:
            orig = original_scores.get(svc, 0.0)
            cf = counterfactual_scores.get(svc, 0.0)
            if orig > 0.1 and cf < orig * 0.8:  # 20%+ improvement
                pct = (orig - cf) / orig * 100
                improvements.append((svc, pct))

        if not improvements:
            return (
                f"Fixing {intervention_service} would have minimal impact "
                f"on other services — it may not be the true root cause."
            )

        improvements.sort(key=lambda x: x[1], reverse=True)
        top_improvements = improvements[:3]
        affected_str = ", ".join(
            f"{svc} (-{pct:.0f}%)" for svc, pct in top_improvements
        )

        return (
            f"Had {intervention_service} been fixed at incident onset, "
            f"anomaly scores would have reduced for: {affected_str}. "
            f"This confirms {intervention_service} as a primary causal driver."
        )

    def get_causal_attribution(
        self,
        dag: nx.DiGraph,
        anomaly_scores: Dict[str, float],
        target_service: str,
    ) -> Dict[str, float]:
        """Compute causal attribution weights for a target service.

        Returns how much each ancestor service contributes to
        the target's anomaly score.

        Args:
            dag: Directed causal graph.
            anomaly_scores: Current anomaly scores.
            target_service: Service to attribute.

        Returns:
            Dict mapping ancestor service → attribution weight (sum ≤ 1.0).
        """
        attribution = {}
        if target_service not in dag.nodes:
            return attribution

        ancestors = nx.ancestors(dag, target_service)
        if not ancestors:
            return {}

        total_ancestor_score = sum(
            anomaly_scores.get(anc, 0.0) for anc in ancestors
        )

        if total_ancestor_score == 0:
            return {anc: 0.0 for anc in ancestors}

        for anc in ancestors:
            # Weight by path count and ancestor anomaly score
            try:
                n_paths = len(list(nx.all_simple_paths(dag, anc, target_service, cutoff=4)))
            except Exception:
                n_paths = 1
            score = anomaly_scores.get(anc, 0.0)
            attribution[anc] = score * n_paths

        # Normalize to sum to 1
        total = sum(attribution.values())
        if total > 0:
            attribution = {k: v / total for k, v in attribution.items()}

        return attribution


# Module-level singleton
counterfactual_engine = CounterfactualEngine()
