"""
SYNAPSE Causal Validation — Cross-check Causal Edges Against Dependency Graph.

Validates that discovered causal edges are consistent with the known
service dependency topology. Removes spurious edges that contradict
actual service call relationships.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import networkx as nx

from app.services.graph_builder import ServiceGraphBuilder


def validate_causal_edges(
    causal_result: Dict[str, Any],
    graph_builder: ServiceGraphBuilder,
    strict: bool = False,
) -> Dict[str, Any]:
    """Validate and filter causal edges against the dependency graph.

    A causal edge A → B is valid if there's a path between A and B in
    the dependency graph (either direction — A calls B or B calls A).

    In strict mode, A → B is only valid if A is upstream of B
    (A's failure can affect B through the call chain).

    Args:
        causal_result: Output from CausalDiscoveryEngine.discover().
        graph_builder: The service graph builder with the dependency topology.
        strict: If True, only allow edges aligned with call direction.

    Returns:
        Filtered causal result with invalid edges removed.
    """
    graph = graph_builder.graph
    edges = causal_result.get("edges", [])
    dag = causal_result.get("dag", {})

    valid_edges = []
    valid_dag: Dict[str, List[str]] = {n: [] for n in causal_result.get("nodes", [])}
    removed_edges = []

    for edge in edges:
        src, tgt = edge[0], edge[1]
        strength = edge[2] if len(edge) > 2 else 0.0

        if strict:
            # Check if src can affect tgt: src must be callable by tgt,
            # or tgt must call src (reverse dependency impact)
            is_valid = _has_dependency_path(graph, src, tgt)
        else:
            # Lenient: any path between them in the undirected graph
            is_valid = _has_undirected_path(graph, src, tgt)

        if is_valid:
            valid_edges.append((src, tgt, strength))
            valid_dag[src].append(tgt)
        else:
            removed_edges.append((src, tgt, strength))

    result = dict(causal_result)
    result["edges"] = valid_edges
    result["dag"] = valid_dag
    result["removed_edges"] = removed_edges
    result["validation_stats"] = {
        "total_edges": len(edges),
        "valid_edges": len(valid_edges),
        "removed_edges": len(removed_edges),
    }

    return result


def _has_dependency_path(
    graph: nx.DiGraph,
    source: str,
    target: str,
    max_hops: int = 5,
) -> bool:
    """Check if there's a directed path from source to target OR target to source.

    In microservices, if database fails, auth-service (which calls database)
    is affected. So database→auth-service is a valid causal edge even though
    the call direction is auth-service→database.
    """
    if source not in graph or target not in graph:
        return True  # Don't filter unknown services

    try:
        # Check both directions
        if nx.has_path(graph, source, target):
            path = nx.shortest_path(graph, source, target)
            return len(path) - 1 <= max_hops
        if nx.has_path(graph, target, source):
            path = nx.shortest_path(graph, target, source)
            return len(path) - 1 <= max_hops
    except nx.NetworkXError:
        pass

    return False


def _has_undirected_path(
    graph: nx.DiGraph,
    source: str,
    target: str,
) -> bool:
    """Check if there's any path (ignoring direction) between two services."""
    if source not in graph or target not in graph:
        return True

    undirected = graph.to_undirected()
    try:
        return nx.has_path(undirected, source, target)
    except nx.NetworkXError:
        return False


def reorient_by_topology(
    causal_result: Dict[str, Any],
    graph_builder: ServiceGraphBuilder,
) -> Dict[str, Any]:
    """Re-orient ambiguous causal edges using the dependency graph.

    If causal discovery says A→B but the dependency graph shows B calls A
    (B→A), re-orient to A→B (A failing causes B's call to A to fail,
    which makes A the root cause — this is correct).

    This is mainly a validation step to confirm directionality.
    """
    graph = graph_builder.graph
    result = dict(causal_result)
    reoriented = []

    for edge in result.get("edges", []):
        src, tgt = edge[0], edge[1]
        strength = edge[2] if len(edge) > 2 else 0.0

        # If tgt calls src (tgt→src in dep graph), then src failing
        # causes tgt to fail — causal direction src→tgt is correct
        if graph.has_edge(tgt, src):
            reoriented.append((src, tgt, strength))
        # If src calls tgt (src→tgt in dep graph), then tgt failing
        # causes src to fail — reverse the causal edge
        elif graph.has_edge(src, tgt):
            reoriented.append((tgt, src, strength))
        else:
            # No direct edge — keep as discovered
            reoriented.append((src, tgt, strength))

    result["edges"] = reoriented

    # Rebuild DAG from reoriented edges
    dag = {n: [] for n in result.get("nodes", [])}
    for src, tgt, _ in reoriented:
        if src in dag:
            dag[src].append(tgt)
    result["dag"] = dag

    return result
