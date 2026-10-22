import { useCallback, useEffect, useMemo } from "react";
import ReactFlow, {
  Background, Controls, MiniMap, Handle, Position,
  useNodesState, useEdgesState,
  type Node, type Edge,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphResponse, GraphNode, GraphEdge } from "../../types/api";
import { useStore } from "../../store";

function scoreColor(score: number) {
  if (score > 0.8) return "#ef4444";
  if (score > 0.6) return "#f97316";
  if (score > 0.4) return "#f59e0b";
  return "#10b981";
}

function ServiceNode({ data }: { data: { label: string; score: number; type: string; metrics: Record<string, number> } }) {
  const c = scoreColor(data.score);
  const isCritical = data.score > 0.8;
  const isWarn = data.score > 0.6 && data.score <= 0.8;

  return (
    <div
      className={isCritical ? "pulse-critical" : isWarn ? "pulse-warning" : ""}
      style={{
        background: "var(--bg-elevated)",
        border: `2px solid ${c}`,
        borderRadius: 12,
        padding: "10px 16px",
        minWidth: 130,
        cursor: "pointer",
        boxShadow: `0 0 ${isCritical ? 18 : 8}px ${c}40`,
        position: "relative",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: c }} />
        <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)" }}>{data.label}</span>
      </div>
      <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginBottom: 6 }}>{data.type}</div>
      <div style={{
        background: `${c}18`, borderRadius: 6, padding: "3px 8px",
        fontSize: "0.7rem", fontFamily: "JetBrains Mono", color: c, textAlign: "center",
      }}>
        {(data.score * 100).toFixed(0)}% anomaly
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { service: ServiceNode };

interface Props { graph: GraphResponse; onNodeClick?: (id: string) => void; }

function getTier(node: GraphNode): "top" | "middle" | "bottom" {
  const name = `${node.id} ${node.label || ""}`.toLowerCase();
  const type = (node.type || "").toLowerCase();

  if (name.includes("gateway") || name.includes("frontend") || type === "gateway") {
    return "top";
  }
  if (
    name.includes("database") ||
    name.includes("db") ||
    name.includes("redis") ||
    name.includes("cache") ||
    type === "infrastructure"
  ) {
    return "bottom";
  }
  return "middle";
}

function computeTieredLayout(nodes: GraphNode[], edges: GraphEdge[]): Record<string, { x: number; y: number }> {
  // Build adjacency list for BFS
  const adj = new Map<string, string[]>();
  for (const edge of edges) {
    if (!adj.has(edge.source)) adj.set(edge.source, []);
    adj.get(edge.source)!.push(edge.target);
  }

  // Classify nodes into tiers using heuristics
  const topTier: GraphNode[] = [];
  const midTier: GraphNode[] = [];
  const bottomTier: GraphNode[] = [];

  for (const node of nodes) {
    const tier = getTier(node);
    if (tier === "top") topTier.push(node);
    else if (tier === "bottom") bottomTier.push(node);
    else midTier.push(node);
  }

  // Determine entry points for BFS traversal (top tier, or in-degree 0 fallback)
  const visited = new Set<string>();
  const bfsOrder: string[] = [];

  let startIds = topTier.map((n) => n.id).sort();
  if (startIds.length === 0) {
    const inDegrees = new Map<string, number>();
    for (const n of nodes) inDegrees.set(n.id, 0);
    for (const edge of edges) {
      inDegrees.set(edge.target, (inDegrees.get(edge.target) || 0) + 1);
    }
    const zeroIn = nodes.filter((n) => (inDegrees.get(n.id) || 0) === 0).map((n) => n.id);
    startIds = zeroIn.length > 0 ? zeroIn.sort() : nodes.map((n) => n.id).sort();
  }

  const queue: string[] = [...startIds];
  for (const id of startIds) visited.add(id);

  while (queue.length > 0) {
    const curr = queue.shift()!;
    bfsOrder.push(curr);

    const neighbors = (adj.get(curr) || []).slice().sort();
    for (const nbr of neighbors) {
      if (!visited.has(nbr)) {
        visited.add(nbr);
        queue.push(nbr);
      }
    }
  }

  // Add any unvisited/disconnected nodes
  const unvisited = nodes
    .filter((n) => !visited.has(n.id))
    .map((n) => n.id)
    .sort();
  for (const id of unvisited) {
    bfsOrder.push(id);
  }

  // Sort nodes within each tier according to BFS discovery order
  const bfsIndex = new Map<string, number>();
  bfsOrder.forEach((id, idx) => bfsIndex.set(id, idx));

  const sortByBfs = (a: GraphNode, b: GraphNode) =>
    (bfsIndex.get(a.id) ?? 0) - (bfsIndex.get(b.id) ?? 0);

  topTier.sort(sortByBfs);
  midTier.sort(sortByBfs);
  bottomTier.sort(sortByBfs);

  // Spread services evenly across x-axis within each tier
  const spacing = 200;
  const maxNodes = Math.max(topTier.length, midTier.length, bottomTier.length, 1);
  const totalWidth = Math.max(800, maxNodes * spacing);
  const centerX = totalWidth / 2;

  const positions: Record<string, { x: number; y: number }> = {};

  const layoutTier = (tierNodes: GraphNode[], y: number) => {
    const count = tierNodes.length;
    if (count === 0) return;
    const startX = centerX - ((count - 1) * spacing) / 2;
    tierNodes.forEach((node, idx) => {
      positions[node.id] = {
        x: Math.round(startX + idx * spacing),
        y,
      };
    });
  };

  layoutTier(topTier, 100);
  layoutTier(midTier, 300);
  layoutTier(bottomTier, 500);

  return positions;
}

export function ServiceGraph({ graph, onNodeClick }: Props) {
  const liveScores = useStore((s) => s.anomalyScores);

  const nodePositions = useMemo(
    () => computeTieredLayout(graph.nodes, graph.edges),
    [graph.nodes, graph.edges]
  );

  const toRFNodes = useCallback((): Node[] =>
    graph.nodes.map((n) => ({
      id: n.id,
      type: "service",
      position: nodePositions[n.id] ?? { x: 0, y: 0 },
      data: {
        label: n.label,
        score: liveScores[n.id] ?? n.anomaly_score,
        type: n.type,
        metrics: n.metrics,
      },
    }))
  , [graph, liveScores, nodePositions]);

  const toRFEdges = useCallback((): Edge[] =>
    graph.edges.map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      animated: true,
      style: { stroke: "var(--border-bright)", strokeWidth: 1.5 },
      label: e.call_type,
      labelStyle: { fill: "var(--text-muted)", fontSize: 9 },
    }))
  , [graph]);

  const [nodes, setNodes, onNodesChange] = useNodesState(toRFNodes());
  const [edges, , onEdgesChange] = useEdgesState(toRFEdges());

  // Re-render nodes when live scores update
  useEffect(() => { setNodes(toRFNodes()); }, [liveScores, toRFNodes]);

  return (
    <div style={{ width: "100%", height: "100%", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, n) => onNodeClick?.(n.id)}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--border)" gap={24} size={1} />
        <Controls style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }} />
        <MiniMap
          nodeColor={(n) => scoreColor((n.data as { score: number }).score ?? 0)}
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        />
      </ReactFlow>
    </div>
  );
}
