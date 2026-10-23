import { useEffect, useState, Fragment } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Target,
  GitBranch,
  Wrench,
  BarChart2,
  Loader,
  AlertTriangle,
  Terminal,
  ArrowRight,
  Clock,
  Activity,
  Cpu,
  Sparkles,
  CheckCircle2,
  Check,
  Zap,
} from "lucide-react";
import { fetchIncident, fetchCausalGraph } from "../api/endpoints";
import type { IncidentDetail, CausalGraph } from "../types/api";
import { StatusBadge, ScoreBar, Spinner } from "../components/UI";
import { CausalGraphViz } from "../components/CausalGraph";
import { usePollReport } from "../hooks/usePollReport";

const PIPELINE_STAGES = [
  { id: 1, label: "Data Ingestion", desc: "Telemetry & metrics ingestion", icon: Activity },
  { id: 2, label: "GNN Detection", desc: "Spatio-temporal graph topology", icon: Cpu },
  { id: 3, label: "Causal Inference", desc: "PCMCI+ directed graph discovery", icon: GitBranch },
  { id: 4, label: "LLM Reasoning", desc: "Deep multi-agent RCA synthesis", icon: Sparkles },
  { id: 5, label: "Complete", desc: "Root cause & remediation ready", icon: CheckCircle2 },
];

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
  const [pipelineStep, setPipelineStep] = useState(1);

  useEffect(() => {
    if (!isAnalyzing) return;
    const interval = setInterval(() => {
      setPipelineStep(prev => (prev >= 4 ? 1 : prev + 1));
    }, 2400);
    return () => clearInterval(interval);
  }, [isAnalyzing]);

  const currentStep = report ? 5 : (isAnalyzing ? pipelineStep : 5);

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
      <Spinner />
    </div>
  );

  if (!incident) return (
    <div style={{ padding: "5rem", textAlign: "center", color: "var(--text-muted)" }}>Incident not found.</div>
  );

  const topScores = Object.entries(incident.anomaly_scores ?? {}).sort((a, b) => b[1] - a[1]);

  const modelInfo = (report?.model_info || {}) as Record<string, any>;
  const recoveryAction = report?.recovery?.action_type || report?.recovery?.action || modelInfo.recovery_action;
  const recoveryTarget = report?.recovery?.target || report?.root_cause?.service || incident.root_cause?.service;
  const recoverySuccess = report?.recovery ? report.recovery.success : (modelInfo.recovery_success ?? (recoveryAction ? true : false));
  let recoveryCommand = report?.recovery?.kubectl_command || (report?.recommended_actions?.find(a => a.trim().startsWith("kubectl")));
  if (!recoveryCommand && recoveryAction && recoveryTarget) {
    if (recoveryAction.includes("restart")) {
      recoveryCommand = `kubectl rollout restart deployment/${recoveryTarget} -n default`;
    } else if (recoveryAction.includes("scale")) {
      recoveryCommand = `kubectl scale deployment/${recoveryTarget} --replicas=3 -n default`;
    }
  }
  const recommendedActions = report?.recommended_actions || [];
  const hasRecovery = Boolean(report && (recoveryAction || recoveryCommand || recommendedActions.length > 0));

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
          <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 4 }}>CONFIDENCE</div>
              <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--accent-blue)" }}>
                {(incident.root_cause.confidence * 100).toFixed(0)}%
              </div>
            </div>
            <Link
              to={`/incidents/${id}/actions`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 14px",
                background: "var(--primary)",
                color: "#fff",
                borderRadius: "var(--radius-sm)",
                textDecoration: "none",
                fontSize: "13px",
                fontWeight: 600,
                marginTop: "4px",
                whiteSpace: "nowrap",
              }}
            >
              ▷ Actions Workspace
            </Link>
          </div>
        )}
      </div>


      {/* Animated Multi-Step Pipeline Progress Indicator (Task 1) */}
      {isAnalyzing && (
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="card"
          style={{
            marginBottom: 24,
            background: "linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.75) 100%)",
            border: "1px solid rgba(99, 102, 241, 0.35)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.06), 0 0 20px rgba(99, 102, 241, 0.15)",
            overflow: "hidden",
            position: "relative",
          }}
        >
          {/* Ambient background glow */}
          <div style={{
            position: "absolute",
            top: -40,
            left: "25%",
            width: 320,
            height: 100,
            background: "rgba(99, 102, 241, 0.15)",
            filter: "blur(48px)",
            pointerEvents: "none",
            borderRadius: "50%",
          }} />

          {/* Top Status */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span className="status-dot blue" />
              <span style={{ fontSize: "0.78rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--accent-blue)" }}>
                AIOps Analysis Pipeline
              </span>
              <span className="badge badge-analyzing" style={{ fontSize: "0.68rem" }}>
                Active Inference
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
              <Loader size={13} style={{ animation: "spin 1s linear infinite" }} />
              <span>Stage <strong style={{ color: "var(--accent-blue)" }}>{currentStep}</strong> of 5 ({Math.round((currentStep / 5) * 100)}%)</span>
            </div>
          </div>

          {/* Stages visual tracker */}
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", position: "relative", marginBottom: 18 }}>
            {PIPELINE_STAGES.map((stg, idx) => {
              const isDone = stg.id < currentStep;
              const isActive = stg.id === currentStep;
              const Icon = stg.icon;

              return (
                <div key={stg.id} style={{ display: "flex", flex: 1, alignItems: "center", position: "relative" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", zIndex: 3, minWidth: 96 }}>
                    <div
                      className={isActive ? "pipeline-step-active" : ""}
                      style={{
                        width: 38,
                        height: 38,
                        borderRadius: "50%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: isDone
                          ? "linear-gradient(135deg, #10b981, #059669)"
                          : isActive
                          ? "linear-gradient(135deg, #6366f1, #4f46e5)"
                          : "var(--bg-elevated)",
                        border: isDone
                          ? "2px solid #10b981"
                          : isActive
                          ? "2px solid #818cf8"
                          : "2px solid var(--border)",
                        color: isDone || isActive ? "#fff" : "var(--text-muted)",
                        boxShadow: isDone
                          ? "0 0 12px rgba(16, 185, 129, 0.45)"
                          : isActive
                          ? "0 0 20px rgba(99, 102, 241, 0.7)"
                          : "none",
                        transition: "all 0.35s ease",
                      }}
                    >
                      {isDone ? <Check size={18} strokeWidth={2.5} /> : <Icon size={18} />}
                    </div>
                    <div style={{
                      fontSize: "0.78rem",
                      fontWeight: isActive ? 700 : 600,
                      color: isDone ? "var(--status-healthy)" : isActive ? "var(--text-primary)" : "var(--text-muted)",
                      marginTop: 8,
                      whiteSpace: "nowrap"
                    }}>
                      {stg.label}
                    </div>
                    <div style={{
                      fontSize: "0.68rem",
                      color: isActive ? "var(--accent-blue)" : "var(--text-muted)",
                      marginTop: 2,
                      maxWidth: 100,
                      lineHeight: 1.2
                    }}>
                      {stg.desc}
                    </div>
                  </div>

                  {idx < PIPELINE_STAGES.length - 1 && (
                    <div style={{
                      flex: 1,
                      height: 3,
                      background: isDone ? "#10b981" : "rgba(99, 102, 241, 0.08)",
                      position: "relative",
                      top: -16,
                      borderRadius: 2,
                      overflow: "hidden",
                      boxShadow: isDone ? "0 0 8px rgba(16, 185, 129, 0.4)" : "none",
                      transition: "background 0.4s ease"
                    }}>
                      {isActive && <div className="pipeline-beam" />}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Bottom Progress Bar */}
          <div style={{
            height: 4,
            borderRadius: 99,
            background: "rgba(255, 255, 255, 0.06)",
            overflow: "hidden",
            position: "relative"
          }}>
            <div
              className="pipeline-progress-bar-animated"
              style={{
                height: "100%",
                width: `${(currentStep / 5) * 100}%`,
                transition: "width 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
                boxShadow: "0 0 10px rgba(59, 130, 246, 0.6)"
              }}
            />
          </div>
        </motion.div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
        {/* Root Cause Card */}
        <div className="card" style={{ borderColor: "rgba(239,68,68,0.3)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <Target size={15} color="var(--status-critical)" />
            <span className="section-title" style={{ marginBottom: 0 }}>Root Cause</span>
          </div>
          {isAnalyzing && !report ? (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--accent-blue)", fontSize: "0.9rem", fontWeight: 600 }}>
                <Loader size={16} style={{ animation: "spin 1s linear infinite" }} />
                <span>AI Pipeline: {PIPELINE_STAGES[currentStep - 1]?.label}</span>
              </div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.78rem", marginTop: 8, lineHeight: 1.5 }}>
                Autonomous correlation & diagnostic models are actively processing telemetry...
              </p>
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
        <div className="card" style={{ borderColor: 'rgba(99,102,241,0.3)', marginBottom: 20 }}>
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
                  background: i === 0 ? 'rgba(239,68,68,0.15)' : 'rgba(99,102,241,0.1)',
                  border: `1px solid ${i === 0 ? 'rgba(239,68,68,0.3)' : 'rgba(99,102,241,0.2)'}`,
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

      {/* Recovery Actions */}
      {hasRecovery && (
        <div
          className="card"
          style={{
            marginBottom: 20,
            borderColor: "rgba(99, 102, 241, 0.35)",
            background: "rgba(255, 255, 255, 0.85)",
            boxShadow: "0 4px 24px rgba(99,102,241,0.04), 0 0 16px rgba(99, 102, 241, 0.12)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "rgba(99, 102, 241, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#6366f1",
                border: "1px solid rgba(99, 102, 241, 0.3)",
              }}
            >
              <Terminal size={16} />
            </div>
            <div>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: 0, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
                Recovery Actions
              </h2>
              <span style={{ fontSize: "0.74rem", color: "var(--text-muted)" }}>
                Automated mitigation and recommended runbook execution
              </span>
            </div>
          </div>

          {/* Auto-Recovery Action Status */}
          {(recoveryAction || recoveryCommand) && (
            <div
              style={{
                marginBottom: recommendedActions.length > 0 ? 16 : 0,
                padding: "14px 16px",
                background: "rgba(99,102,241,0.03)",
                borderRadius: 10,
                border: "1px solid rgba(99, 102, 241, 0.2)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <div
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    color: "#818cf8",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  <Zap size={13} color="#818cf8" />
                  <span>Auto-Recovery Action</span>
                </div>
                <span
                  style={{
                    fontSize: "0.72rem",
                    fontWeight: 700,
                    fontFamily: "var(--font-mono, JetBrains Mono, monospace)",
                    padding: "3px 10px",
                    borderRadius: 4,
                    background: recoverySuccess !== false ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)",
                    color: recoverySuccess !== false ? "#10b981" : "#f59e0b",
                    border: `1px solid ${recoverySuccess !== false ? "rgba(16, 185, 129, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                    letterSpacing: "0.03em",
                  }}
                >
                  {recoverySuccess !== false ? "EXECUTED ✓" : "PENDING ⏳"}
                </span>
              </div>

              {recoveryAction && (
                <div
                  style={{
                    fontSize: "0.82rem",
                    color: "var(--text-primary)",
                    marginBottom: recoveryCommand ? 12 : 0,
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>Action:</span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono, JetBrains Mono, monospace)",
                      fontWeight: 600,
                      color: "#818cf8",
                      background: "rgba(99, 102, 241, 0.12)",
                      padding: "2px 8px",
                      borderRadius: 4,
                      border: "1px solid rgba(99, 102, 241, 0.25)",
                    }}
                  >
                    {recoveryAction.replace(/_/g, " ")}
                  </span>
                  {recoveryTarget && (
                    <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
                      on <strong style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono, JetBrains Mono, monospace)" }}>{recoveryTarget}</strong>
                    </span>
                  )}
                </div>
              )}

              {recoveryCommand && (
                <div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
                    Kubectl Command
                  </div>
                  <div
                    style={{
                      background: "rgba(241, 245, 249, 0.95)",
                      border: "1px solid rgba(99, 102, 241, 0.2)",
                      borderRadius: 6,
                      padding: "10px 14px",
                      fontFamily: "var(--font-mono, JetBrains Mono, monospace)",
                      fontSize: "0.82rem",
                      color: "#10b981",
                      wordBreak: "break-all",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <span style={{ color: "var(--text-muted)", userSelect: "none" }}>$</span>
                    <span>{recoveryCommand}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Recommended Actions */}
          {recommendedActions.length > 0 && (
            <div
              style={{
                padding: "14px 16px",
                background: "rgba(99,102,241,0.03)",
                borderRadius: 10,
                border: "1px solid var(--border)",
              }}
            >
              <div
                style={{
                  fontSize: "0.78rem",
                  fontWeight: 700,
                  color: "var(--text-secondary)",
                  marginBottom: 10,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <Wrench size={13} color="#6366f1" />
                <span>Recommended Recovery Actions</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {recommendedActions.map((action: string, i: number) => {
                  const isKubectl = action.trim().startsWith("kubectl");
                  return (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 8,
                        padding: "8px 12px",
                        background: i === 0 ? "rgba(99, 102, 241, 0.06)" : "transparent",
                        borderRadius: 6,
                        border: i === 0 ? "1px solid rgba(99, 102, 241, 0.15)" : "none",
                      }}
                    >
                      <span style={{ color: i === 0 ? "#6366f1" : "var(--text-muted)", flexShrink: 0, marginTop: 1 }}>
                        {i === 0 ? "▶" : "○"}
                      </span>
                      <span
                        style={{
                          fontSize: "0.82rem",
                          color: isKubectl ? "#10b981" : "var(--text-primary)",
                          fontFamily: isKubectl ? "var(--font-mono, JetBrains Mono, monospace)" : "inherit",
                          wordBreak: "break-all",
                          lineHeight: 1.5,
                        }}
                      >
                        {action}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: (report?.metric_deltas && Object.keys(report.metric_deltas).length > 0 && report?.severity) ? "1fr 1fr" : "1fr", gap: 20 }}>

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
            {/* Timeline vertical bar background track */}
            <div style={{
              position: 'absolute',
              top: 10,
              bottom: 10,
              left: 8,
              width: 2,
              background: 'rgba(255, 255, 255, 0.06)',
              borderRadius: 2
            }} />

            {/* Animated connecting line drawing itself on page load */}
            <motion.div
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
              style={{
                position: 'absolute',
                top: 10,
                bottom: 10,
                left: 8,
                width: 2,
                background: 'linear-gradient(180deg, var(--accent-blue) 0%, #8b5cf6 50%, var(--status-critical) 100%)',
                transformOrigin: 'top',
                borderRadius: 2,
                boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)',
              }}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              {incident.timeline.map((item, idx) => {
                const isLast = idx === incident.timeline.length - 1;
                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -18, y: 8 }}
                    animate={{ opacity: 1, x: 0, y: 0 }}
                    transition={{
                      duration: 0.45,
                      delay: 0.15 + idx * 0.12,
                      ease: "easeOut"
                    }}
                    style={{ position: 'relative' }}
                  >
                    {/* Dot with spring scale-in */}
                    <motion.div
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{
                        delay: 0.15 + idx * 0.12 + 0.1,
                        type: "spring",
                        stiffness: 350,
                        damping: 20
                      }}
                      style={{
                        position: 'absolute',
                        left: -28,
                        top: 3,
                        width: 16,
                        height: 16,
                        borderRadius: '50%',
                        background: isLast ? 'var(--status-critical)' : 'var(--accent-blue)',
                        border: '3px solid var(--bg-card)',
                        boxShadow: isLast 
                          ? '0 0 12px rgba(239,68,68,0.85), 0 0 4px #ef4444' 
                          : '0 0 8px rgba(59,130,246,0.6)',
                        zIndex: 2,
                      }}
                      className={isLast ? "pulse-critical" : ""}
                    />

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
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
