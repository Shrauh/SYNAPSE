import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Target, GitBranch, Wrench, BarChart2, Loader } from "lucide-react";
import { fetchIncident, fetchCausalGraph } from "../api/endpoints";
import type { IncidentDetail, CausalGraph } from "../types/api";
import { StatusBadge, ScoreBar, Spinner } from "../components/UI";
import { CausalGraphViz } from "../components/CausalGraph";
import { usePollReport } from "../hooks/usePollReport";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [causal, setCausal] = useState<CausalGraph | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      fetchIncident(id),
      fetchCausalGraph(id).catch(() => null),
    ]).then(([inc, cg]) => {
      setIncident(inc);
      setCausal(cg);
    }).finally(() => setLoading(false));
  }, [id]);

  const isAnalyzing = incident?.status === "analyzing";
  const { report } = usePollReport(id!, !!isAnalyzing);

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
      <Spinner />
    </div>
  );

  if (!incident) return (
    <div style={{ padding: "5rem", textAlign: "center", color: "var(--text-muted)" }}>Incident not found.</div>
  );

  const topScores = Object.entries(incident.anomaly_scores ?? {}).sort((a, b) => b[1] - a[1]);

  return (
    <div style={{ padding: "84px 2rem 3rem", maxWidth: 1100, margin: "0 auto" }}>
      {/* Back + Header */}
      <Link to="/incidents" style={{ display: "inline-flex", alignItems: "center", gap: 6,
        color: "var(--text-muted)", fontSize: "0.82rem", textDecoration: "none", marginBottom: 20 }}>
        <ArrowLeft size={14} /> All Incidents
      </Link>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: "1.4rem", fontWeight: 800, letterSpacing: "-0.02em", marginBottom: 6 }}>
            {incident.title}
          </h1>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <StatusBadge status={incident.status} />
            <span style={{ fontSize: "0.72rem", fontFamily: "JetBrains Mono", color: "var(--text-muted)" }}>{id}</span>
          </div>
        </div>
        {incident.root_cause && (
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 4 }}>CONFIDENCE</div>
            <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--accent-blue)" }}>
              {(incident.root_cause.confidence * 100).toFixed(0)}%
            </div>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
        {/* Root Cause Card */}
        <div className="card" style={{ borderColor: "rgba(239,68,68,0.3)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <Target size={15} color="var(--status-critical)" />
            <span className="section-title" style={{ marginBottom: 0 }}>Root Cause</span>
          </div>
          {isAnalyzing && !report ? (
            <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--text-muted)", fontSize: "0.85rem" }}>
              <Loader size={16} style={{ animation: "spin 1s linear infinite" }} />
              AI pipeline analyzing...
            </div>
          ) : report ? (
            <>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, fontFamily: "JetBrains Mono",
                color: "var(--status-critical)", marginBottom: 6 }}>
                {report.root_cause.service}
              </div>
              <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                <span className={`badge badge-${report.root_cause.fault_type === "latency_spike" ? "warning" : report.root_cause.fault_type === "error_burst" ? "critical" : "degraded"}`}>
                  {report.root_cause.fault_type?.replace(/_/g, " ")}
                </span>
              </div>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {report.explanation}
              </p>
            </>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No RCA report yet.</div>
          )}
        </div>

        {/* Propagation Chain */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <GitBranch size={15} color="var(--accent-purple)" />
            <span className="section-title" style={{ marginBottom: 0 }}>Propagation Chain</span>
          </div>
          {report?.propagation_chain ? (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
              {report.propagation_chain.split("→").map((s, i, arr) => (
                <span key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{
                    padding: "4px 10px", borderRadius: 6,
                    background: i === 0 ? "rgba(239,68,68,0.15)" : "var(--bg-elevated)",
                    color: i === 0 ? "var(--status-critical)" : "var(--text-secondary)",
                    fontSize: "0.8rem", fontFamily: "JetBrains Mono", fontWeight: 600,
                    border: `1px solid ${i === 0 ? "rgba(239,68,68,0.3)" : "var(--border)"}`,
                  }}>
                    {s.trim()}
                  </span>
                  {i < arr.length - 1 && <span style={{ color: "var(--text-muted)" }}>→</span>}
                </span>
              ))}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              {isAnalyzing ? "Awaiting causal analysis..." : "No propagation chain."}
            </div>
          )}

          {/* Anomaly Scores */}
          {topScores.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: 10,
                textTransform: "uppercase", letterSpacing: "0.07em" }}>Anomaly Scores</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {topScores.map(([svc, score]) => (
                  <div key={svc} style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <span style={{ width: 130, fontSize: "0.75rem", color: "var(--text-secondary)", fontFamily: "JetBrains Mono", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{svc}</span>
                    <div style={{ flex: 1 }}><ScoreBar score={score} /></div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Causal Graph */}
      {causal && causal.causal_nodes.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <BarChart2 size={15} color="var(--accent-cyan)" />
            <span className="section-title" style={{ marginBottom: 0 }}>Causal Graph</span>
          </div>
          <CausalGraphViz graph={causal} />
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Recommended Actions */}
        {report?.recommended_actions && (
          <div className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <Wrench size={15} color="var(--accent-blue)" />
              <span className="section-title" style={{ marginBottom: 0 }}>Recommended Actions</span>
            </div>
            <ol style={{ paddingLeft: 18, display: "flex", flexDirection: "column", gap: 10 }}>
              {report.recommended_actions.map((a, i) => (
                <motion.li key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.08 }}
                  style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {a}
                </motion.li>
              ))}
            </ol>
          </div>
        )}

        {/* Metric Deltas */}
        {report?.metric_deltas && Object.keys(report.metric_deltas).length > 0 && (
          <div className="card">
            <div className="section-title">Metric Deltas</div>
            {Object.entries(report.metric_deltas).map(([svc, deltas]) => (
              <div key={svc} style={{ marginBottom: 12 }}>
                <div style={{ fontSize: "0.78rem", fontFamily: "JetBrains Mono", color: "var(--accent-blue)", marginBottom: 4 }}>{svc}</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {Object.entries(deltas).map(([k, v]) => (
                    <span key={k} style={{ padding: "2px 8px", background: "var(--bg-elevated)",
                      borderRadius: 4, fontSize: "0.72rem", color: v.startsWith("+") ? "var(--status-critical)" : "var(--status-healthy)" }}>
                      {k}: {v}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
