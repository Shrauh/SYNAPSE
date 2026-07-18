import { useEffect, useState } from "react";
import { fetchGraph } from "../api/endpoints";
import type { GraphResponse, GraphNode } from "../types/api";
import { ServiceGraph } from "../components/ServiceGraph";
import { Spinner, ScoreBar } from "../components/UI";
import { SimulateModal } from "../components/SimulateModal";
import { Zap, RefreshCw } from "lucide-react";

export default function GraphPage() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [showSim, setShowSim] = useState(false);

  const load = () => {
    setLoading(true);
    fetchGraph().then(setGraph).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div style={{ padding: "56px 0 0", height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "12px 1.5rem", borderBottom: "1px solid var(--border)", background: "var(--bg-card)" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: "1rem" }}>Service Dependency Graph</div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
            {graph ? `${graph.metadata.total_services} services · ${graph.metadata.total_edges} edges` : "Loading..."}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-ghost" onClick={load}><RefreshCw size={13} /> Refresh</button>
          <button className="btn btn-danger" onClick={() => setShowSim(true)}><Zap size={13} /> Simulate Fault</button>
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Graph */}
        <div style={{ flex: 1 }}>
          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
              <Spinner />
            </div>
          ) : graph ? (
            <ServiceGraph
              graph={graph}
              onNodeClick={(id) => setSelected(graph.nodes.find(n => n.id === id) ?? null)}
            />
          ) : (
            <div style={{ padding: "2rem", color: "var(--text-muted)" }}>Failed to load graph. Is the backend running?</div>
          )}
        </div>

        {/* Side panel */}
        {selected && (
          <div style={{ width: 280, borderLeft: "1px solid var(--border)", padding: "1.2rem",
            background: "var(--bg-card)", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: "0.95rem" }}>{selected.label}</div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  {selected.type}
                </div>
              </div>
              <button className="btn btn-ghost" style={{ padding: "3px 8px", fontSize: "0.72rem" }}
                onClick={() => setSelected(null)}>✕</button>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 6 }}>ANOMALY SCORE</div>
              <ScoreBar score={selected.anomaly_score} />
            </div>

            <div>
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 10 }}>METRICS</div>
              {Object.entries(selected.metrics).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between",
                  padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: "0.8rem" }}>
                  <span style={{ color: "var(--text-secondary)", textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</span>
                  <span style={{ fontFamily: "JetBrains Mono", color: "var(--text-primary)" }}>
                    {typeof v === "number" ? v.toFixed(2) : v}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {showSim && <SimulateModal onClose={() => setShowSim(false)} />}
    </div>
  );
}
