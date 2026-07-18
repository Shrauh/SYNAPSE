import { useCallback, useEffect } from "react";
import ReactFlow, {
  Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  type Node, type Edge,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphResponse } from "../../types/api";
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
      }}
    >
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
    </div>
  );
}

const nodeTypes = { service: ServiceNode };

interface Props { graph: GraphResponse; onNodeClick?: (id: string) => void; }

const POSITIONS: Record<string, { x: number; y: number }> = {
  "api-gateway":          { x: 400, y: 20  },
  "auth-service":         { x: 180, y: 150 },
  "user-service":         { x: 380, y: 150 },
  "order-service":        { x: 600, y: 150 },
  "search-service":       { x: 780, y: 150 },
  "payment-service":      { x: 520, y: 300 },
  "inventory-service":    { x: 680, y: 300 },
  "notification-service": { x: 400, y: 400 },
  "cache-service":        { x: 160, y: 350 },
  "database":             { x: 320, y: 350 },
};

export function ServiceGraph({ graph, onNodeClick }: Props) {
  const liveScores = useStore((s) => s.anomalyScores);

  const toRFNodes = useCallback((): Node[] =>
    graph.nodes.map((n) => ({
      id: n.id,
      type: "service",
      position: POSITIONS[n.id] ?? { x: Math.random() * 600, y: Math.random() * 400 },
      data: {
        label: n.label,
        score: liveScores[n.id] ?? n.anomaly_score,
        type: n.type,
        metrics: n.metrics,
      },
    }))
  , [graph, liveScores]);

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
