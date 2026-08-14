"""
SYNAPSE Causal DAG Utilities — Root Cause Extraction & Validation.

Provides functions to extract root cause candidates from the causal DAG,
check for cycles, and compute propagation chains.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


def get_root_nodes(
    dag: Dict[str, List[str]],
    anomaly_scores: Dict[str, float],
) -> List[Tuple[str, float]]:
    """Extract root cause candidates from the causal DAG.

    Root nodes are services that:
    1. Have no incoming causal edges from other anomalous services
    2. Only have outgoing edges (they cause others, not caused by others)

    Args:
        dag: Adjacency dict {source: [targets]} from causal discovery.
        anomaly_scores: {service: score} for anomalous services.

    Returns:
        List of (service_name, anomaly_score) sorted by score descending.
    """
    all_nodes = set(dag.keys())
    # Find nodes that appear as targets (have incoming edges)
    has_incoming: Set[str] = set()
    for source, targets in dag.items():
        for t in targets:
            if t in all_nodes:
                has_incoming.add(t)

    # Root nodes = nodes with no incoming edges
    roots = all_nodes - has_incoming

    # If no clear roots (fully connected), fall back to highest anomaly score
    if not roots:
        roots = all_nodes

    # Sort by anomaly score
    root_list = [
        (svc, anomaly_scores.get(svc, 0.0))
        for svc in roots
    ]
    root_list.sort(key=lambda x: x[1], reverse=True)

    return root_list


def get_propagation_chain(
    dag: Dict[str, List[str]],
    root: str,
) -> List[str]:
    """BFS from root to get the propagation chain (order of impact).

    Args:
        dag: Adjacency dict from causal discovery.
        root: Root cause service.

    Returns:
        Ordered list of services in propagation order (root first).
    """
    visited = set()
    chain = []
    queue = [root]

    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        chain.append(node)
        for target in dag.get(node, []):
            if target not in visited:
                queue.append(target)

    return chain


def detect_cycles(dag: Dict[str, List[str]]) -> List[List[str]]:
    """Detect cycles in the causal DAG.

    Uses DFS-based cycle detection. Returns list of cycles found.
    Cycles indicate potential issues with causal discovery.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in dag}
    cycles = []

    def dfs(node: str, path: List[str]):
        color[node] = GRAY
        path.append(node)

        for neighbor in dag.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
            elif color[neighbor] == WHITE:
                dfs(neighbor, path)

        path.pop()
        color[node] = BLACK

    for node in dag:
        if color[node] == WHITE:
            dfs(node, [])

    return cycles


def break_cycles(
    dag: Dict[str, List[str]],
    anomaly_scores: Dict[str, float],
) -> Dict[str, List[str]]:
    """Break cycles in the DAG by removing the weakest edges.

    Weakest = edge from the node with lower anomaly score.

    Args:
        dag: Potentially cyclic adjacency dict.
        anomaly_scores: {service: score} for prioritization.

    Returns:
        Acyclic DAG.
    """
    dag = {k: list(v) for k, v in dag.items()}  # Deep copy
    cycles = detect_cycles(dag)

    for cycle in cycles:
        if len(cycle) < 2:
            continue
        # Find the edge with the lowest-scoring source
        min_score = float("inf")
        min_edge = None
        for i in range(len(cycle) - 1):
            src, tgt = cycle[i], cycle[i + 1]
            score = anomaly_scores.get(src, 0.0)
            if score < min_score:
                min_score = score
                min_edge = (src, tgt)

        if min_edge:
            src, tgt = min_edge
            if tgt in dag.get(src, []):
                dag[src].remove(tgt)

    return dag


def to_causal_graph_json(
    dag: Dict[str, List[str]],
    edges_with_strength: List[Tuple[str, str, float]],
    anomaly_scores: Dict[str, float],
    root_candidates: List[Tuple[str, float]],
) -> Dict[str, Any]:
    """Convert causal analysis results to JSON format for DB storage.

    Returns dict matching the CausalGraphResponse schema:
        {"nodes": [...], "edges": [...]}
    """
    root_services = {r[0] for r in root_candidates}

    nodes = [
        {
            "id": svc,
            "anomaly_score": anomaly_scores.get(svc, 0.0),
            "is_root": svc in root_services,
        }
        for svc in dag.keys()
    ]

    edges = [
        {
            "source": src,
            "target": tgt,
            "strength": strength,
        }
        for src, tgt, strength in edges_with_strength
    ]

    return {"nodes": nodes, "edges": edges}
