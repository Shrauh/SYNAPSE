import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertTriangle, Activity, Clock, Cpu,
  ArrowRight, Zap, TrendingUp, Server,
  CheckCircle, BarChart2
} from "lucide-react";
import { fetchHealth, fetchMetrics, fetchIncidents } from "../api/endpoints";
import type { HealthResponse, MetricsResponse, IncidentSummary } from "../types/api";
import { StatCard, StatusBadge, Spinner, SectionHeader, EmptyState, ScoreBar, AnomalyChip, LiveBadge } from "../components/UI";
import { useStore } from "../store";
import { format, formatDistanceToNow } from "date-fns";
import RCAPanel from "../components/RCAPanel";
import RemediationPanel from "../components/RemediationPanel";
import LearningStats from "../components/LearningStats";
import EventLog from "../components/EventLog";
import MetricsPanel from "../components/MetricsPanel";

const FADE_UP = (delay: number) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay },
});

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const anomalyScores = useStore(s => s.anomalyScores);
  const wsConnected = useStore(s => s.wsConnected);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      const [h, m, i] = await Promise.all([fetchHealth(), fetchMetrics(), fetchIncidents(1)]);
      setHealth(h);
      setMetrics(m);
      setIncidents(i.incidents.slice(0, 8));
    } catch { /* backend offline — show placeholder UI */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 12000);
    return () => clearInterval(iv);
  }, [load]);

  const topServices = Object.entries(anomalyScores).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const criticalCount = Object.values(anomalyScores).filter(s => s > 0.8).length;

  return (
    <div className="page-content">
      <div className="page-bg" />

      {/* ── Header ── */}
      <motion.div {...FADE_UP(0)} style={{ marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <h1 className="page-title">Operations Dashboard</h1>
            {criticalCount > 0 && (
              <motion.span
                initial={{ scale: 0 }} animate={{ scale: 1 }}
                className="badge badge-critical badge-dot"
                style={{ gap: 5 }}
              >
                <span className="status-dot critical" style={{ width: 5, height: 5 }} />
                {criticalCount} Critical
              </motion.span>
            )}
          </div>
          <p className="page-subtitle">
            Real-time AIOps monitoring · SYNAPSE v{health?.version ?? "1.0.0"}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <LiveBadge connected={wsConnected} />
          <button className="btn btn-gradient btn-sm" onClick={() => navigate("/simulate")}>
            <Zap size={13} /> Inject Fault
          </button>
        </div>
      </motion.div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "40vh", gap: 16 }}>
          <div className="spinner spinner-lg" />
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Connecting to SYNAPSE backend…</p>
        </div>
      ) : (
        <>
          {/* ── Stat Cards ── */}
          <motion.div
            {...FADE_UP(0.05)}
            style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 20 }}
            className="stats-grid"
          >
            <StatCard
              title="Total Incidents"
              value={metrics?.total_incidents ?? 0}
              icon={<AlertTriangle size={18} color="var(--accent-indigo)" />}
              color="indigo"
              sub="All time"
              trend={{ value: "+2 today", up: true }}
            />
            <StatCard
              title="Active Analysis"
              value={metrics?.active_incidents ?? 0}
              icon={<Activity size={18} color="var(--accent-violet)" />}
              color="violet"
              sub="Analyzing now"
            />
            <StatCard
              title="Avg RCA Time"
              value={`${(metrics?.avg_resolution_time_sec ?? 0).toFixed(1)}s`}
              icon={<Clock size={18} color="var(--accent-cyan)" />}
              color="cyan"
              sub="vs 1–2 hrs manual"
              trend={{ value: "52s avg", up: false }}
            />
            <StatCard
              title="Services Monitored"
              value={10}
              icon={<Server size={18} color="var(--accent-emerald)" />}
              color="emerald"
              sub="10-service topology"
            />
          </motion.div>

          {/* ── Main Grid ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16, marginBottom: 16 }}>

            {/* Recent Incidents */}
            <motion.div {...FADE_UP(0.1)} className="card">
              <SectionHeader
                label="Real-time"
                title="Recent Incidents"
                action={
                  <Link to="/incidents" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.78rem", color: "var(--accent-indigo)", textDecoration: "none", fontWeight: 600 }}>
                    All Incidents <ArrowRight size={13} />
                  </Link>
                }
              />
              {incidents.length === 0 ? (
                <EmptyState
                  icon="🛡️"
                  title="No Incidents Yet"
                  desc="Go to Simulate to inject a fault and run the full RCA pipeline."
                  action={
                    <button className="btn btn-primary btn-sm" onClick={() => navigate("/simulate")}>
                      <Zap size={13} /> Inject Fault
                    </button>
                  }
                />
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Incident</th>
                        <th>Status</th>
                        <th>Root Cause</th>
                        <th>Confidence</th>
                        <th>Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {incidents.map((inc, i) => (
                        <motion.tr
                          key={inc.id}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.04 }}
                          onClick={() => navigate(`/incidents/${inc.id}`)}
                        >
                          <td>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <div style={{
                                width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                                background: inc.severity === "critical" ? "var(--status-critical)"
                                  : inc.severity === "high" ? "var(--status-warning)"
                                  : "var(--accent-amber)",
                              }} />
                              <span style={{ color: "var(--text-primary)", fontWeight: 500, fontSize: "0.875rem" }}>
                                {inc.title}
                              </span>
                            </div>
                          </td>
                          <td><StatusBadge status={inc.status} /></td>
                          <td>
                            <span style={{ fontFamily: "JetBrains Mono", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                              {inc.root_cause_service ?? <span style={{ color: "var(--text-muted)" }}>analyzing…</span>}
                            </span>
                          </td>
                          <td>
                            {inc.confidence != null ? (
                              <span style={{ color: "var(--accent-indigo)", fontWeight: 700, fontSize: "0.85rem" }}>
                                {(inc.confidence * 100).toFixed(0)}%
                              </span>
                            ) : <span style={{ color: "var(--text-muted)" }}>—</span>}
                          </td>
                          <td>
                            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                              {formatDistanceToNow(new Date(inc.detected_at), { addSuffix: true })}
                            </span>
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </motion.div>

            {/* Live Anomaly Feed */}
            <motion.div {...FADE_UP(0.15)} className="card" style={{ display: "flex", flexDirection: "column" }}>
              <SectionHeader
                label="WebSocket"
                title="Anomaly Scores"
                action={<LiveBadge connected={wsConnected} />}
              />
              {topServices.length === 0 ? (
                <EmptyState
                  icon="📡"
                  title="Waiting for Live Data"
                  desc="Start the backend to see real-time anomaly scores."
                />
              ) : (
                <div style={{ flex: 1 }}>
                  {topServices.map(([svc, score], i) => (
                    <motion.div
                      key={svc}
                      layout
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          {score > 0.8 ? (
                            <span className="status-dot critical pulse-critical" style={{ flexShrink: 0 }} />
                          ) : score > 0.6 ? (
                            <span className="status-dot warning" style={{ flexShrink: 0 }} />
                          ) : (
                            <span className="status-dot healthy" style={{ flexShrink: 0 }} />
                          )}
                          <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>{svc}</span>
                        </div>
                        <AnomalyChip score={score} />
                      </div>
                      <ScoreBar score={score} size="sm" />
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>

          {/* ── System Components + Quick Stats ── */}
          <motion.div {...FADE_UP(0.2)} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

            {/* System Health */}
            <div className="card">
              <SectionHeader label="Infrastructure" title="System Components" />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {health ? (
                  Object.entries(health.components).map(([key, val]) => {
                    const ok = val === true || val === "up" || val === "healthy" || val === "connected";
                    return (
                      <div key={key} style={{
                        display: "flex", alignItems: "center", gap: 10,
                        padding: "0.75rem", borderRadius: "var(--radius-md)",
                        background: ok ? "rgba(16,185,129,0.04)" : "rgba(239,68,68,0.04)",
                        border: `1px solid ${ok ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.15)"}`,
                      }}>
                        {ok
                          ? <CheckCircle size={14} color="var(--accent-emerald)" />
                          : <AlertTriangle size={14} color="var(--status-critical)" />
                        }
                        <div>
                          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "capitalize" }}>
                            {key.replace(/_/g, " ")}
                          </div>
                          <div style={{ fontSize: "0.78rem", fontWeight: 600, color: ok ? "#34d399" : "#f87171" }}>
                            {String(val)}
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div style={{ gridColumn: "1/-1" }}>
                    <EmptyState title="Backend offline" desc="Start the FastAPI server to see system status." />
                  </div>
                )}
              </div>
            </div>

            {/* Key Metrics / Innovation Summary */}
            <div className="card">
              <SectionHeader label="Platform" title="SYNAPSE Innovations" />
              <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                {[
                  { icon: "🧠", label: "GNN Anomaly Detection", desc: "GAT Autoencoder — no labeled data", color: "var(--accent-indigo)" },
                  { icon: "🔗", label: "Causal Inference (DECI)", desc: "PC Algorithm + Do-Calculus", color: "var(--accent-violet)" },
                  { icon: "💬", label: "LLM Reasoning (GPT-4)", desc: "Plain English RCA reports", color: "var(--accent-cyan)" },
                  { icon: "📚", label: "Continual Learning (EWC)", desc: "Zero catastrophic forgetting", color: "var(--accent-emerald)" },
                  { icon: "⚡", label: "MAML Zero-Shot", desc: "Adapts to new services in 5 steps", color: "var(--accent-amber)" },
                ].map(({ icon, label, desc, color }, i) => (
                  <motion.div
                    key={label}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.25 + i * 0.06 }}
                    style={{
                      display: "flex", alignItems: "center", gap: 12,
                      padding: "0.7rem 0", borderBottom: "1px solid var(--border)",
                    }}
                  >
                    <div style={{
                      width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      background: `${color}15`,
                      fontSize: "1rem",
                    }}>
                      {icon}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>{label}</div>
                      <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>{desc}</div>
                    </div>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: color, flexShrink: 0 }} />
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* ── AI Intelligence Row ── */}
          <motion.div {...FADE_UP(0.25)} style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 16, alignItems: "start" }} className="ai-grid">
            <RCAPanel />
            <RemediationPanel />
            <LearningStats />
            <EventLog />
          </motion.div>

          {/* ── Metrics Row ── */}
          <motion.div {...FADE_UP(0.3)} style={{ marginTop: 16 }}>
            <MetricsPanel />
          </motion.div>
        </>
      )}

      <style>{`
        @media (max-width: 900px) {
          .stats-grid { grid-template-columns: 1fr 1fr !important; }
          .ai-grid { grid-template-columns: 1fr 1fr !important; }
        }
        @media (max-width: 600px) {
          .stats-grid { grid-template-columns: 1fr !important; }
          .ai-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
