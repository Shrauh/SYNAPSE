import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft, Target, GitBranch, Wrench,
  BarChart2, Loader, Copy, CheckCheck,
  AlertTriangle, Clock, TrendingUp
} from "lucide-react";
import { fetchIncident, fetchCausalGraph, fetchReport } from "../api/endpoints";
import type { IncidentDetail, CausalGraph, RCAReport } from "../types/api";
import {
  StatusBadge, ScoreBar, Spinner, SectionHeader,
  ConfidenceGauge, AnomalyChip, Tag
} from "../components/UI";
import { CausalGraphViz } from "../components/CausalGraph";
import { usePollReport } from "../hooks/usePollReport";
import { format } from "date-fns";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [causal, setCausal] = useState<CausalGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [inc, cg] = await Promise.all([
        fetchIncident(id),
        fetchCausalGraph(id).catch(() => null),
      ]);
      setIncident(inc);
      setCausal(cg);
    } catch { /* backend offline */ }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const isAnalyzing = incident?.status === "analyzing";
  const { report } = usePollReport(id!, !!isAnalyzing);

  const copyReport = () => {
    if (!report) return;
    const text = [
      `SYNAPSE RCA Report — Incident ${id}`,
      `Root Cause: ${report.root_cause.service} (${report.root_cause.fault_type})`,
      `Confidence: ${(report.root_cause.confidence * 100).toFixed(1)}%`,
      `\nExplanation:\n${report.explanation}`,
      `\nPropagation: ${report.propagation_chain}`,
      `\nRecommended Actions:\n${report.recommended_actions.map((a, i) => `${i + 1}. ${a}`).join("\n")}`,
    ].join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
      <Spinner size="lg" />
    </div>
  );

  if (!incident) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "80vh", gap: 16 }}>
      <AlertTriangle size={40} color="var(--text-muted)" />
      <p style={{ color: "var(--text-muted)" }}>Incident not found.</p>
      <button className="btn btn-ghost" onClick={() => navigate("/incidents")}><ArrowLeft size={14} /> Back</button>
    </div>
  );

  const topScores = Object.entries(incident.anomaly_scores ?? {}).sort((a, b) => b[1] - a[1]);
  const rootCause = report?.root_cause ?? incident.root_cause;

  return (
    <div className="page-content">
      <div className="page-bg" />

      {/* Back */}
      <Link to="/incidents" style={{ display: "inline-flex", alignItems: "center", gap: 6,
        color: "var(--text-muted)", fontSize: "0.82rem", textDecoration: "none", marginBottom: 20,
        transition: "color 0.15s" }}
        onMouseOver={e => (e.currentTarget.style.color = "var(--text-primary)")}
        onMouseOut={e => (e.currentTarget.style.color = "var(--text-muted)")}>
        <ArrowLeft size={14} /> All Incidents
      </Link>

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
        style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <h1 className="page-title" style={{ fontSize: "1.4rem" }}>{incident.title}</h1>
            <StatusBadge status={incident.severity} />
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <StatusBadge status={incident.status} />
            <span style={{ fontSize: "0.72rem", fontFamily: "JetBrains Mono", color: "var(--text-muted)" }}>#{id?.slice(0, 12)}</span>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
              {format(new Date(incident.detected_at), "MMM d, HH:mm:ss")}
            </span>
          </div>
        </div>

        {rootCause && (
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <ConfidenceGauge value={rootCause.confidence} />
            {report && (
              <button className="btn btn-ghost btn-sm" onClick={copyReport}>
                {copied ? <><CheckCheck size={13} /> Copied</> : <><Copy size={13} /> Copy Report</>}
              </button>
            )}
          </div>
        )}
      </motion.div>

      {/* Main 2-col layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

        {/* Root Cause Card */}
        <motion.div className="card" initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.05 }}
          style={{ borderColor: "rgba(239,68,68,0.2)" }}>
          <SectionHeader label="AI Analysis" title="Root Cause" action={<Target size={16} color="var(--status-critical)" />} />

          {isAnalyzing && !report ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14, padding: "2rem 0" }}>
              <div style={{ position: "relative" }}>
                <div className="spinner spinner-lg" />
                <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent-indigo)" }} className="blink" />
                </div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)", fontWeight: 500 }}>AI Pipeline Running</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>GNN → Causal → LLM…</div>
              </div>
            </div>
          ) : rootCause ? (
            <>
              <div style={{ fontSize: "1.6rem", fontWeight: 800, fontFamily: "JetBrains Mono",
                color: "var(--status-critical)", marginBottom: 8, letterSpacing: "-0.02em" }}>
                {rootCause.service}
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
                <Tag color="indigo">{rootCause.fault_type?.replace(/_/g, " ") ?? "unknown"}</Tag>
                <Tag color="cyan">
                  {(rootCause.confidence * 100).toFixed(1)}% confidence
                </Tag>
              </div>
              {report?.explanation && (
                <p style={{ fontSize: "0.86rem", color: "var(--text-secondary)", lineHeight: 1.7,
                  borderLeft: "2px solid rgba(99,102,241,0.4)", paddingLeft: 12 }}>
                  {report.explanation}
                </p>
              )}
            </>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No RCA report available yet.</div>
          )}
        </motion.div>

        {/* Propagation Chain + Anomaly Scores */}
        <motion.div className="card" initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.08 }}>
          <SectionHeader label="Causal Chain" title="Propagation Path" action={<GitBranch size={16} color="var(--accent-violet)" />} />

          {report?.propagation_chain ? (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginBottom: 20 }}>
              {report.propagation_chain.split("→").map((s, i, arr) => (
                <span key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{
                    padding: "5px 12px", borderRadius: 7,
                    background: i === 0 ? "rgba(239,68,68,0.12)" : "rgba(255,255,255,0.05)",
                    color: i === 0 ? "#f87171" : "var(--text-secondary)",
                    fontSize: "0.78rem", fontFamily: "JetBrains Mono", fontWeight: 600,
                    border: `1px solid ${i === 0 ? "rgba(239,68,68,0.3)" : "var(--border)"}`,
                  }}>
                    {i === 0 && "⚠ "}{s.trim()}
                  </span>
                  {i < arr.length - 1 && (
                    <span style={{ color: "var(--text-muted)", fontSize: "1rem" }}>→</span>
                  )}
                </span>
              ))}
            </div>
          ) : (
            <p style={{ color: "var(--text-muted)", fontSize: "0.82rem", marginBottom: 16 }}>
              {isAnalyzing ? "Awaiting causal discovery…" : "No propagation data."}
            </p>
          )}

          {topScores.length > 0 && (
            <>
              <div className="section-label">Anomaly Scores</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {topScores.map(([svc, score]) => (
                  <div key={svc} style={{ display: "grid", gridTemplateColumns: "140px 1fr 50px", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontFamily: "JetBrains Mono",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{svc}</span>
                    <ScoreBar score={score} />
                    <AnomalyChip score={score} />
                  </div>
                ))}
              </div>
            </>
          )}
        </motion.div>
      </div>

      {/* Causal Graph */}
      {causal && causal.causal_nodes.length > 0 && (
        <motion.div className="card" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}
          style={{ marginBottom: 16 }}>
          <SectionHeader label="Graph Neural Network" title="Causal Graph" action={<BarChart2 size={16} color="var(--accent-cyan)" />} />
          <CausalGraphViz graph={causal} />
        </motion.div>
      )}

      {/* Actions + Deltas */}
      {report && (
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}
        >
          {/* Recommended Actions */}
          {report.recommended_actions && report.recommended_actions.length > 0 && (
            <div className="card">
              <SectionHeader label="CQL Agent" title="Recommended Actions" action={<Wrench size={16} color="var(--accent-emerald)" />} />
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {report.recommended_actions.map((action, i) => (
                  <motion.div key={i}
                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.18 + i * 0.06 }}
                    style={{ display: "flex", gap: 10, alignItems: "flex-start",
                      padding: "0.75rem", borderRadius: "var(--radius-md)",
                      background: "rgba(16,185,129,0.04)", border: "1px solid rgba(16,185,129,0.12)" }}>
                    <div style={{ width: 22, height: 22, borderRadius: "50%", background: "rgba(16,185,129,0.15)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "0.68rem", fontWeight: 800, color: "#34d399", flexShrink: 0 }}>
                      {i + 1}
                    </div>
                    <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>{action}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Metric Deltas */}
          {report.metric_deltas && Object.keys(report.metric_deltas).length > 0 && (
            <div className="card">
              <SectionHeader label="Service Impact" title="Metric Deltas" action={<TrendingUp size={16} color="var(--accent-amber)" />} />
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {Object.entries(report.metric_deltas).map(([svc, deltas]) => (
                  <div key={svc}>
                    <div style={{ fontSize: "0.78rem", fontFamily: "JetBrains Mono",
                      color: "var(--accent-indigo)", marginBottom: 6, fontWeight: 600 }}>
                      {svc}
                    </div>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {Object.entries(deltas).map(([k, v]) => (
                        <span key={k} style={{
                          padding: "3px 9px", borderRadius: 6,
                          background: String(v).startsWith("+") ? "rgba(239,68,68,0.08)" : "rgba(16,185,129,0.08)",
                          border: `1px solid ${String(v).startsWith("+") ? "rgba(239,68,68,0.2)" : "rgba(16,185,129,0.2)"}`,
                          color: String(v).startsWith("+") ? "#f87171" : "#34d399",
                          fontSize: "0.72rem", fontWeight: 600,
                        }}>
                          {k}: {v}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
