import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { fetchGraph } from "../api/endpoints";
import type { GraphResponse, GraphNode } from "../types/api";
import { ServiceGraph } from "../components/ServiceGraph";
import { Spinner, ScoreBar, StatusBadge, AnomalyChip, EmptyState } from "../components/UI";
import { Zap, RefreshCw, X, Server, Activity, Cpu, Clock } from "lucide-react";

export default function GraphPage() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const navigate = useNavigate();

  const load = useCallback(() => {
    setLoading(true);
    fetchGraph().then(setGraph).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); const iv = setInterval(load, 15000); return () => clearInterval(iv); }, [load]);

  const criticalNodes = graph?.nodes.filter(n => n.anomaly_score > 0.6) ?? [];

  return (
    <div style={{ paddingTop: 58, height: "100vh", display: "flex", flexDirection: "column" }}>

      {/* Toolbar */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "10px 1.5rem", borderBottom: "1px solid var(--border)",
        background: "rgba(4,4,15,0.9)", backdropFilter: "blur(20px)",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--text-primary)" }}>
              Service Dependency Graph
            </div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
              {graph
                ? `${graph.metadata.total_services} services · ${graph.metadata.total_edges} edges · auto-refreshes every 15s`
                : "Loading topology…"}
            </div>
          </div>

          {/* Legend */}
          <div style={{ display: "flex", gap: 12, alignItems: "center", paddingLeft: 16, borderLeft: "1px solid var(--border)" }}>
            {[
              { color: "var(--status-critical)", label: "Critical (>0.8)" },
              { color: "var(--status-warning)", label: "Warning (>0.6)" },
              { color: "var(--accent-amber)", label: "Degraded (>0.4)" },
              { color: "var(--accent-emerald)", label: "Healthy" },
            ].map(({ color, label }) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: "0.68rem", color: "var(--text-muted)" }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />
                {label}
              </div>
            ))}
          </div>

          {/* Alert count */}
          {criticalNodes.length > 0 && (
            <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }}
              className="badge badge-critical badge-dot"
              style={{ gap: 5, cursor: "pointer" }}>
              <span className="status-dot critical" style={{ width: 5, height: 5 }} />
              {criticalNodes.length} anomalous
            </motion.span>
          )}
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={12} className={loading ? "spin" : ""} /> Refresh
          </button>
          <button className="btn btn-gradient btn-sm" onClick={() => navigate("/simulate")}>
            <Zap size={12} /> Inject Fault
          </button>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", position: "relative" }}>

        {/* Graph Canvas */}
        <div style={{ flex: 1 }}>
          {loading && !graph ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 14,
              justifyContent: "center", alignItems: "center", height: "100%" }}>
              <Spinner size="lg" />
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Loading service topology…</p>
            </div>
          ) : graph ? (
            <ServiceGraph
              graph={graph}
              onNodeClick={(id) => setSelected(graph.nodes.find(n => n.id === id) ?? null)}
            />
          ) : (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
              <EmptyState
                icon={<Server size={40} color="var(--text-muted)" />}
                title="Backend Offline"
                desc="Start the FastAPI server to see the live service topology."
                action={
                  <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer"
                    className="btn btn-primary btn-sm">
                    Open API Docs
                  </a>
                }
              />
            </div>
          )}
        </div>

        {/* Side Panel */}
        {selected && (
          <motion.div
            initial={{ x: 300, opacity: 0 }} animate={{ x: 0, opacity: 1 }}
            exit={{ x: 300, opacity: 0 }}
            style={{
              width: 300, borderLeft: "1px solid var(--border)",
              background: "rgba(4,4,15,0.95)", backdropFilter: "blur(20px)",
              overflowY: "auto", flexShrink: 0,
            }}
          >
            {/* Node Header */}
            <div style={{ padding: "1.25rem", borderBottom: "1px solid var(--border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    width: 10, height: 10, borderRadius: "50%", flexShrink: 0,
                    background: selected.anomaly_score > 0.8 ? "var(--status-critical)"
                      : selected.anomaly_score > 0.6 ? "var(--status-warning)"
                      : selected.anomaly_score > 0.4 ? "var(--accent-amber)"
                      : "var(--accent-emerald)",
                  }} className={selected.anomaly_score > 0.8 ? "pulse-critical" : ""} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                      {selected.label}
                    </div>
                    <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      {selected.type}
                    </div>
                  </div>
                </div>
                <button onClick={() => setSelected(null)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4 }}>
                  <X size={16} />
                </button>
              </div>

              <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
                <StatusBadge status={selected.status} />
                <AnomalyChip score={selected.anomaly_score} />
              </div>
            </div>

            {/* Anomaly Score Bar */}
            <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid var(--border)" }}>
              <div className="section-label">Anomaly Score</div>
              <ScoreBar score={selected.anomaly_score} />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                <span>Normal</span>
                <AnomalyChip score={selected.anomaly_score} />
                <span>Critical</span>
              </div>
            </div>

            {/* Metrics */}
            <div style={{ padding: "1rem 1.25rem" }}>
              <div className="section-label">Live Metrics</div>
              {[
                { key: "latency",      label: "Latency",      unit: "ms",  Icon: Clock },
                { key: "error_rate",   label: "Error Rate",   unit: "%",   Icon: Activity },
                { key: "cpu",          label: "CPU Usage",    unit: "%",   Icon: Cpu },
                { key: "memory",       label: "Memory",       unit: "%",   Icon: Server },
                { key: "request_rate", label: "Request Rate", unit: "/s",  Icon: Activity },
              ].map(({ key, label, unit, Icon }) => {
                const val = selected.metrics[key as keyof typeof selected.metrics];
                return (
                  <div key={key} style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "0.6rem 0", borderBottom: "1px solid var(--border)",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Icon size={13} color="var(--text-muted)" />
                      <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{label}</span>
                    </div>
                    <span style={{ fontFamily: "JetBrains Mono", fontSize: "0.82rem", color: "var(--text-primary)", fontWeight: 600 }}>
                      {typeof val === "number" ? val.toFixed(2) : val}{unit}
                    </span>
                  </div>
                );
              })}
            </div>

            {selected.anomaly_score > 0.6 && (
              <div style={{ padding: "1rem 1.25rem" }}>
                <button className="btn btn-gradient btn-sm" style={{ width: "100%", justifyContent: "center" }}
                  onClick={() => navigate("/simulate")}>
                  <Zap size={13} /> Investigate this Service
                </button>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
