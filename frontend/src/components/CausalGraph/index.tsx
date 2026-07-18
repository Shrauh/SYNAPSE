import ReactFlow, { Background, type Node, type Edge } from "reactflow";
import "reactflow/dist/style.css";
import type { CausalGraph } from "../../types/api";

function CausalNode({ data }: { data: { id: string; score: number; is_root: boolean } }) {
  const c = data.is_root ? "#ef4444" : data.score > 0.6 ? "#f97316" : "#f59e0b";
  return (
    <div style={{
      background: "var(--bg-elevated)",
      border: `2px solid ${c}`,
      borderRadius: 10, padding: "8px 14px",
      boxShadow: data.is_root ? `0 0 16px ${c}60` : "none",
    }}>
      <div style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--text-primary)" }}>{data.id}</div>
      {data.is_root && (
        <div style={{ fontSize: "0.65rem", color: c, marginTop: 2, fontWeight: 600 }}>ROOT CAUSE</div>
      )}
      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>
        Score: {data.score.toFixed(2)}
      </div>
    </div>
  );
}

const nodeTypes = { causal: CausalNode };

export function CausalGraphViz({ graph }: { graph: CausalGraph }) {
  const nodes: Node[] = graph.causal_nodes.map((n, i) => ({
    id: n.id,
    type: "causal",
    position: { x: (i % 3) * 200 + 40, y: Math.floor(i / 3) * 140 + 40 },
    data: n,
  }));

  const edges: Edge[] = graph.causal_edges.map((e, i) => ({
    id: `ce${i}`,
    source: e.source,
    target: e.target,
    animated: true,
    label: `${(e.strength * 100).toFixed(0)}%`,
    labelStyle: { fill: "#8b5cf6", fontSize: 9 },
    style: { stroke: "#8b5cf6", strokeWidth: 2 },
    markerEnd: "url(#arrow)",
  }));

  return (
    <div style={{ height: 280, borderRadius: "var(--radius-md)", overflow: "hidden", background: "var(--bg-primary)" }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView proOptions={{ hideAttribution: true }}>
        <Background color="var(--border)" gap={20} size={1} />
      </ReactFlow>
    </div>
  );
}
