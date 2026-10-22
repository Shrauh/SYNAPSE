"""
SYNAPSE Causal DAG Utilities — Root Cause Extraction & Validation.

Provides functions to extract root cause candidates from the causal DAG,
check for cycles, and compute propagation chains.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


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

    # Filter: root must have out-degree > 0 (it causes downstream effects)
    roots = {n for n in (all_nodes - has_incoming) if dag.get(n)}
    # Fallback: if no valid roots, use all non-isolated nodes
    if not roots:
        roots = {n for n in all_nodes if dag.get(n) or n in has_incoming}
    if not roots:
        roots = all_nodes  # absolute fallback

    # Sort by anomaly score
    root_list = [
        (svc, anomaly_scores.get(svc, 0.0))
        for svc in roots
    ]
    root_list.sort(key=lambda x: x[1], reverse=True)

    return root_list


def get_propagation_chain(
    dag: Optional[Dict[str, List[str]]],
    root_cause: str = "",
    topology_graph=None,
    root: Optional[str] = None,
) -> List[str]:
    """BFS from root to get the propagation chain (order of impact).

    When the causal DAG has no outgoing edges from the root cause, falls back
    to the service topology graph to trace cascading failure via reverse-edge
    (predecessor) BFS.

    Args:
        dag: Adjacency dict from causal discovery.
        root_cause: Root cause service name.
        topology_graph: Optional networkx DiGraph for fallback traversal.
        root: Alias for root_cause (backwards compatibility).

    Returns:
        Ordered list of services in propagation order (root first).
    """
    actual_root = root_cause or root or ""
    if not actual_root:
        return []

    dag = dag or {}
    visited = set()
    chain = []
    queue = [actual_root]

    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        chain.append(node)
        for target in dag.get(node, []):
            if target not in visited:
                queue.append(target)

    # If chain is just the root, use topology to build cascading failure chain
    if len(chain) <= 1 and topology_graph is not None:
        try:
            # BFS walking reverse edges in topology (callers that depend on root_cause)
            topo_visited = {actual_root}
            topo_chain = [actual_root]
            topo_queue = [actual_root]

            while topo_queue:
                curr = topo_queue.pop(0)
                if hasattr(topology_graph, "predecessors") and curr in topology_graph:
                    preds = sorted(topology_graph.predecessors(curr))
                elif isinstance(topology_graph, dict):
                    preds = sorted([
                        src for src, tgts in topology_graph.items()
                        if isinstance(tgts, (list, set, tuple)) and curr in tgts
                    ])
                else:
                    preds = []

                for pred in preds:
                    if pred not in topo_visited:
                        topo_visited.add(pred)
                        topo_chain.append(pred)
                        topo_queue.append(pred)

            if len(topo_chain) > 1:
                chain = topo_chain
            else:
                # Fallback: if root has no predecessors (e.g. gateway at top level),
                # walk forward edges (successors) to show downstream cascade
                succ_visited = {actual_root}
                succ_chain = [actual_root]
                succ_queue = [actual_root]

                while succ_queue:
                    curr = succ_queue.pop(0)
                    if hasattr(topology_graph, "successors") and curr in topology_graph:
                        succs = sorted(topology_graph.successors(curr))
                    elif isinstance(topology_graph, dict):
                        succs = sorted(list(topology_graph.get(curr, [])))
                    else:
                        succs = []

                    for succ in succs:
                        if succ not in succ_visited:
                            succ_visited.add(succ)
                            succ_chain.append(succ)
                            succ_queue.append(succ)

                if len(succ_chain) > 1:
                    chain = succ_chain
        except Exception:
            pass

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
    anomaly_scores: Optional[Dict[str, float]] = None,
    edges: Optional[List[Any]] = None,
) -> Dict[str, List[str]]:
    """Break cycles in the DAG by removing the weakest edges.

    Weakest = edge with lowest causal strength (lowest edge weight).

    Args:
        dag: Potentially cyclic adjacency dict.
        anomaly_scores: Optional {service: score} for fallback prioritization.
        edges: Optional list of edges (dicts or tuples) with causal strength weights.

    Returns:
        Acyclic DAG.
    """
    if isinstance(anomaly_scores, list) and edges is None:
        edges = anomaly_scores
        anomaly_scores = None

    valid_dag = {k: list(v) for k, v in dag.items()}  # Deep copy
    cycles = detect_cycles(valid_dag)

    for cycle in cycles:
        if len(cycle) < 2:
            continue
        cycle_nodes = cycle[:-1] if (len(cycle) > 1 and cycle[0] == cycle[-1]) else cycle
        # Find the weakest edge in the cycle to break
        min_weight = float("inf")
        min_edge = None
        for i in range(len(cycle_nodes)):
            src = cycle_nodes[i]
            tgt = cycle_nodes[(i + 1) % len(cycle_nodes)]
            # Get edge weight from the edges list
            edge_weight = 1.0
            if edges:
                for e in edges:
                    if isinstance(e, dict):
                        if (e.get("source") == src and e.get("target") == tgt) or \
                           (len(e) >= 2 and e.get(0) == src and e.get(1) == tgt):
                            edge_weight = e.get("weight", e.get("strength", 1.0))
                            break
                    elif isinstance(e, (list, tuple)) and len(e) >= 2:
                        if e[0] == src and e[1] == tgt:
                            edge_weight = e[2] if len(e) > 2 else 1.0
                            break
            elif anomaly_scores:
                edge_weight = anomaly_scores.get(src, 1.0)

            if edge_weight < min_weight:
                min_weight = edge_weight
                min_edge = (src, tgt)

        if min_edge:
            src, tgt = min_edge
            if src in valid_dag and tgt in valid_dag[src]:
                valid_dag[src].remove(tgt)

    return valid_dag


def to_causal_graph_json(
    dag: Dict[str, List[str]],
    edges_with_strength: List[Tuple[str, str, float]],
    anomaly_scores: Dict[str, float],
    root_candidates: List[Tuple[str, float]],
) -> Dict[str, Any]:
    """Convert causal analysis results to JSON format for DB storage.

    Only includes edges still present in the acyclic dag (after cycle-breaking)
    to keep the graph consistent with the root cause analysis.

    Returns dict matching the CausalGraphResponse schema:
        {"nodes": [...], "edges": [...]}
    """
    root_services = {r[0] for r in root_candidates}

    # Valid edges from the post-cycle-break acyclic dag
    valid_edge_set = {
        (src, tgt)
        for src, targets in dag.items()
        for tgt in targets
    }

    nodes = [
        {
            "id": svc,
            "anomaly_score": round(anomaly_scores.get(svc, 0.0), 4),
            "is_root": svc in root_services,
        }
        for svc in dag.keys()
    ]

    # Only include edges that survived cycle-breaking
    edges = [
        {
            "source": src,
            "target": tgt,
            "strength": round(strength, 4),
        }
        for src, tgt, strength in edges_with_strength
        if (src, tgt) in valid_edge_set
    ]

    return {"nodes": nodes, "edges": edges}
