import { useCallback, useEffect } from "react";
import ReactFlow, {
  Background, Controls, MiniMap, Handle, Position,
  useNodesState, useEdgesState,
  MarkerType,
  type Node, type Edge, type NodeProps,
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

function ServiceNode({ data }: NodeProps<{ label: string; score: number; type: string }>) {
  const c = scoreColor(data.score);
  const isCritical = data.score > 0.8;
  const isWarn = data.score > 0.6 && data.score <= 0.8;

  return (
    <>
      <Handle type="target" position={Position.Top} style={{ background: "#334155", width: 8, height: 8 }} />
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
      <Handle type="source" position={Position.Bottom} style={{ background: "#334155", width: 8, height: 8 }} />
    </>
  );
}

const nodeTypes = { service: ServiceNode };

interface Props { graph: GraphResponse; onNodeClick?: (id: string) => void; }

// Online Boutique layered DAG positions
const POSITIONS: Record<string, { x: number; y: number }> = {
  "frontend":  { x: 380, y:  20 },
  "checkout":  { x: 140, y: 180 },
  "cart":      { x: 400, y: 180 },
  "catalog":   { x: 620, y: 180 },
  "ad":        { x: 830, y: 180 },
  "payment":   { x:  40, y: 360 },
  "order":     { x: 260, y: 360 },
  "redis":     { x: 460, y: 360 },
  "orderdb":   { x: 150, y: 520 },
  "email":     { x: 370, y: 520 },
};

export function ServiceGraph({ graph, onNodeClick }: Props) {
  const liveScores = useStore((s) => s.anomalyScores);

  const toRFNodes = useCallback((): Node[] =>
    graph.nodes.map((n) => ({
      id: n.id,
      type: "service",
      position: POSITIONS[n.id] ?? { x: Math.random() * 700, y: Math.random() * 400 },
      data: {
        label: n.label,
        score: liveScores[n.id] ?? n.anomaly_score,
        type: n.type,
      },
    }))
  , [graph, liveScores]);

  const toRFEdges = useCallback((): Edge[] =>
    graph.edges.map((e, i) => ({
      id: `edge-${i}`,
      source: e.source,
      target: e.target,
      type: "smoothstep",
      animated: false,
      style: { stroke: "#475569", strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#64748b", width: 16, height: 16 },
    }))
  , [graph]);

  const [nodes, setNodes, onNodesChange] = useNodesState(toRFNodes());
  const [edges, , onEdgesChange] = useEdgesState(toRFEdges());

  useEffect(() => { setNodes(toRFNodes()); }, [liveScores, toRFNodes]);

  return (
    <div style={{ width: "100%", height: "100%", overflow: "hidden" }}>
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
        <Background color="#1e293b" gap={24} size={1} />
        <Controls style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }} />
        <MiniMap
          nodeColor={(n) => scoreColor((n.data as { score: number }).score ?? 0)}
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        />
      </ReactFlow>
    </div>
  );
}
