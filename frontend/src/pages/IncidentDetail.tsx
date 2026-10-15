import { useEffect, useState, Fragment } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Target, GitBranch, Wrench, BarChart2, Loader, AlertTriangle, Terminal, ArrowRight, Clock } from "lucide-react";
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
                <span className="badge badge-healthy">
                  {(report.root_cause.confidence * 100).toFixed(0)}% Confidence
                </span>
              </div>
            </>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No RCA report yet.</div>
          )}
        </div>

        {/* Anomaly Scores Card */}
        <div className="card">
          <div className="section-title">Anomaly Scores</div>
          {topScores.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {topScores.map(([svc, score]) => (
                <div key={svc} style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span style={{ width: 130, fontSize: "0.75rem", color: "var(--text-secondary)", fontFamily: "JetBrains Mono", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{svc}</span>
                  <div style={{ flex: 1 }}><ScoreBar score={score} /></div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No anomaly scores recorded.</div>
          )}
        </div>
      </div>

      {/* AI Analysis */}
      {report?.explanation && (
        <div className="card" style={{ borderColor: 'rgba(59,130,246,0.3)', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <span style={{ fontSize: '1.2rem' }}>🧠</span>
            <span className="section-title" style={{ marginBottom: 0 }}>AI Analysis</span>
          </div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.8, fontStyle: 'italic' }}>
            {report.explanation}
          </p>
        </div>
      )}

      {/* Propagation Chain */}
      {report?.propagation_chain && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="section-title">Propagation Chain</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            {(report.propagation_chain.includes(' → ')
              ? report.propagation_chain.split(' → ')
              : report.propagation_chain.split('→').map(s => s.trim())
            ).map((svc, i, arr) => (
              <Fragment key={`${svc}-${i}`}>
                <div style={{ 
                  padding: '8px 16px', 
                  borderRadius: 8, 
                  background: i === 0 ? 'rgba(239,68,68,0.15)' : 'rgba(59,130,246,0.1)',
                  border: `1px solid ${i === 0 ? 'rgba(239,68,68,0.3)' : 'rgba(59,130,246,0.2)'}`,
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  color: i === 0 ? 'var(--status-critical)' : 'var(--accent-blue)'
                }}>
                  {svc}
                </div>
                {i < arr.length - 1 && (
                  <ArrowRight size={16} color="var(--text-muted)" />
                )}
              </Fragment>
            ))}
          </div>
        </div>
      )}

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

      {/* Recovery Action */}
      {report?.recovery && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <Terminal size={15} color="var(--accent)" />
            <span className="section-title" style={{ marginBottom: 0 }}>Recovery Action</span>
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <span className={`badge badge-${report.recovery.success ? 'healthy' : 'warning'}`}>
              {report.recovery.action_type || report.recovery.action}
            </span>
            <span className={`badge badge-${report.recovery.success ? 'healthy' : 'critical'}`}>
              {report.recovery.success ? '✓ EXECUTED' : '⏳ PENDING'}
            </span>
            {report.recovery.target && (
              <span className="badge badge-degraded" style={{ fontFamily: 'var(--font-mono)' }}>
                {report.recovery.target}
              </span>
            )}
          </div>
          {report.recovery.kubectl_command && (
            <div style={{ 
              background: '#0a0e17', 
              border: '1px solid var(--border)', 
              borderRadius: 8, 
              padding: '12px 16px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.82rem',
              color: '#10b981',
              position: 'relative'
            }}>
              <span style={{ color: 'var(--text-muted)' }}>$ </span>
              {report.recovery.kubectl_command}
            </div>
          )}
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

        {/* Severity Classification */}
        {report?.severity && (
          <div className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <AlertTriangle size={15} color="var(--status-warning)" />
              <span className="section-title" style={{ marginBottom: 0 }}>Severity Classification</span>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
              <span className={`badge badge-${report.severity.level === 'L4' || report.severity.level === 'L3' ? 'critical' : report.severity.level === 'L2' ? 'warning' : 'healthy'}`}>
                {report.severity.level}
              </span>
              {report.severity.is_recurring && (
                <span className="badge badge-warning">Recurring ({report.severity.recurring_count}x)</span>
              )}
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 8 }}>
              <strong>Reason:</strong> {report.severity.reason}
            </p>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              <strong>Response:</strong> {report.severity.response_strategy}
            </p>
          </div>
        )}
      </div>

      {/* Incident Timeline */}
      {incident.timeline && incident.timeline.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <Clock size={16} color="var(--accent-blue)" />
            <span className="section-title" style={{ marginBottom: 0 }}>Incident Timeline</span>
          </div>
          <div style={{ position: 'relative', paddingLeft: 28 }}>
            {/* Timeline vertical bar */}
            <div style={{
              position: 'absolute',
              top: 8,
              bottom: 8,
              left: 8,
              width: 2,
              background: 'var(--border)'
            }} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              {incident.timeline.map((item, idx) => {
                const isLast = idx === incident.timeline.length - 1;
                return (
                  <div key={idx} style={{ position: 'relative' }}>
                    {/* Dot */}
                    <div style={{
                      position: 'absolute',
                      left: -28,
                      top: 3,
                      width: 16,
                      height: 16,
                      borderRadius: '50%',
                      background: isLast ? 'var(--status-critical)' : 'var(--accent-blue)',
                      border: '3px solid var(--bg-card)',
                      boxShadow: isLast 
                        ? '0 0 10px rgba(239,68,68,0.7)' 
                        : '0 0 8px rgba(59,130,246,0.5)',
                    }} />

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                      <div>
                        <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                          {item.event}
                        </div>
                        {item.score != null && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                            Score / Latency: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>{typeof item.score === 'number' ? item.score.toFixed(3) : item.score}</span>
                          </div>
                        )}
                      </div>
                      <span style={{
                        fontSize: '0.75rem',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-muted)',
                        whiteSpace: 'nowrap',
                        background: 'var(--bg-elevated)',
                        padding: '2px 8px',
                        borderRadius: 4,
                        border: '1px solid var(--border)'
                      }}>
                        {item.time}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
