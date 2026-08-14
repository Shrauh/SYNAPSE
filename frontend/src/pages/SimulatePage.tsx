import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence, useAnimation } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  Zap, CheckCircle, AlertCircle, RotateCcw,
  Info, ChevronRight, Database, Brain, Network,
  Search, GitBranch, MessageSquare, Activity, Shield,
  Play, Loader2,
} from "lucide-react";
import { simulateFault, fetchReport } from "../api/endpoints";
import type { SimulateRequest, SimulateResponse } from "../types/api";
import { useStore } from "../store";

/* ── Pipeline step definitions ── */
const PIPELINE_STEPS = [
  {
    label: "Fault Injection",
    desc: "Inject synthetic failure into microservice topology",
    icon: Zap,
    color: "#f43f5e",
    bg: "rgba(244,63,94,0.1)",
    border: "rgba(244,63,94,0.3)",
    duration: 800,
  },
  {
    label: "Metric Simulation",
    desc: "Generate 60 time-step telemetry series per service",
    icon: Activity,
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.1)",
    border: "rgba(245,158,11,0.3)",
    duration: 1000,
  },
  {
    label: "Graph Construction",
    desc: "Build service dependency graph with NetworkX",
    icon: Network,
    color: "#06b6d4",
    bg: "rgba(6,182,212,0.1)",
    border: "rgba(6,182,212,0.3)",
    duration: 600,
  },
  {
    label: "GAT Training",
    desc: "Train Graph Attention autoencoder on normal baseline",
    icon: Brain,
    color: "#8b5cf6",
    bg: "rgba(139,92,246,0.1)",
    border: "rgba(139,92,246,0.3)",
    duration: 2500,
  },
  {
    label: "Anomaly Scoring",
    desc: "Infer per-service anomaly scores via GNN",
    icon: Search,
    color: "#6366f1",
    bg: "rgba(99,102,241,0.1)",
    border: "rgba(99,102,241,0.3)",
    duration: 1200,
  },
  {
    label: "Causal Discovery",
    desc: "Run PC / DECI causal inference algorithm",
    icon: GitBranch,
    color: "#10b981",
    bg: "rgba(16,185,129,0.1)",
    border: "rgba(16,185,129,0.3)",
    duration: 1800,
  },
  {
    label: "Edge Validation",
    desc: "Validate causal edges against known topology",
    icon: Shield,
    color: "#06b6d4",
    bg: "rgba(6,182,212,0.1)",
    border: "rgba(6,182,212,0.3)",
    duration: 600,
  },
  {
    label: "LLM Report",
    desc: "Generate natural-language RCA + action plan",
    icon: MessageSquare,
    color: "#10b981",
    bg: "rgba(16,185,129,0.1)",
    border: "rgba(16,185,129,0.3)",
    duration: 1500,
  },
];

const SERVICES = [
  "frontend", "checkout", "cart", "payment", "order",
  "catalog", "ad", "redis", "email", "orderdb",
];
const FAULT_TYPES = [
  { value: "latency_spike",            label: "Latency Spike",      icon: "⏱️" },
  { value: "error_burst",              label: "Error Burst",         icon: "💥" },
  { value: "resource_exhaustion",      label: "Resource Exhaustion", icon: "📈" },
  { value: "connection_pool_exhaustion", label: "Connection Pool",   icon: "🔌" },
];
const SCENARIOS = [
  {
    title: "OrderDB Cascade",
    service: "orderdb", type: "latency_spike", severity: "critical",
    desc: "Database slowdown cascades upstream through payment → checkout → frontend",
    icon: Database, color: "#f43f5e", badge: "critical",
  },
  {
    title: "Payment Error Burst",
    service: "payment", type: "error_burst", severity: "high",
    desc: "High 5xx error rate in payment — disrupts checkout & order flow",
    icon: Activity, color: "#f97316", badge: "high",
  },
  {
    title: "Redis Cache OOM",
    service: "redis", type: "resource_exhaustion", severity: "medium",
    desc: "Cache memory exhaustion causes cart degradation and checkout timeouts",
    icon: Brain, color: "#f59e0b", badge: "medium",
  },
  {
    title: "Frontend Slowdown",
    service: "frontend", type: "latency_spike", severity: "high",
    desc: "Entry-point latency spike — all downstream services affected",
    icon: Network, color: "#6366f1", badge: "high",
  },
];

/* ── Animated particle for active connector ── */
function FlowParticle({ delay = 0, color }: { delay?: number; color: string }) {
  return (
    <motion.div
      initial={{ scaleX: 0, opacity: 0, x: "-100%" }}
      animate={{ scaleX: 1, opacity: [0, 1, 1, 0], x: "100%" }}
      transition={{ duration: 1.2, delay, repeat: Infinity, repeatDelay: 0.4, ease: "easeInOut" }}
      style={{
        position: "absolute", top: "50%", left: 0, right: 0, height: 3,
        background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
        borderRadius: 99, pointerEvents: "none",
      }}
    />
  );
}

/* ── Single pipeline node card ── */
function PipelineNode({
  step, index, status, isLast,
}: {
  step: typeof PIPELINE_STEPS[0];
  index: number;
  status: "idle" | "active" | "done" | "error";
  isLast: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  const Icon = step.icon;

  const borderColor = status === "done" ? "#10b981"
    : status === "active" ? step.color
    : status === "error" ? "#ef4444"
    : "var(--border)";

  const bgColor = status === "done" ? "rgba(16,185,129,0.06)"
    : status === "active" ? step.bg
    : status === "error" ? "rgba(239,68,68,0.06)"
    : "var(--bg-card)";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
      {/* Node card */}
      <motion.div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        animate={{
          borderColor,
          backgroundColor: bgColor,
          boxShadow: status === "active"
            ? `0 0 20px ${step.color}40, 0 4px 16px rgba(0,0,0,0.3)`
            : status === "done"
            ? "0 0 12px rgba(16,185,129,0.2), 0 2px 8px rgba(0,0,0,0.2)"
            : hovered
            ? "0 4px 20px rgba(0,0,0,0.2)"
            : "0 2px 8px rgba(0,0,0,0.1)",
        }}
        transition={{ duration: 0.3 }}
        style={{
          border: `1.5px solid`,
          borderRadius: 16,
          padding: "1rem",
          width: "100%",
          maxWidth: 160,
          cursor: "default",
          position: "relative",
          overflow: "hidden",
          backdropFilter: "blur(12px)",
        }}
      >
        {/* Shimmer on active */}
        {status === "active" && (
          <div
            className="pipeline-shimmer"
            style={{ position: "absolute", inset: 0, borderRadius: 16, opacity: 0.4 }}
          />
        )}

        {/* Step number */}
        <div style={{
          position: "absolute", top: 8, right: 10,
          fontSize: "0.6rem", fontWeight: 700,
          color: status === "idle" ? "var(--text-muted)" : step.color,
          opacity: 0.7,
          fontFamily: "JetBrains Mono",
        }}>
          {String(index + 1).padStart(2, "0")}
        </div>

        {/* Icon */}
        <div style={{
          width: 40, height: 40, borderRadius: 12,
          background: status === "idle" ? "var(--bg-elevated)" : step.bg,
          border: `1px solid ${status === "idle" ? "var(--border)" : step.border}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          marginBottom: 10,
          transition: "all 0.3s",
        }}>
          {status === "done"
            ? <CheckCircle size={18} color="#10b981" />
            : status === "active"
            ? <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}>
                <Loader2 size={18} color={step.color} />
              </motion.div>
            : status === "error"
            ? <AlertCircle size={18} color="#ef4444" />
            : <Icon size={18} color={status === "idle" ? "var(--text-muted)" : step.color} />
          }
        </div>

        {/* Label */}
        <div style={{
          fontSize: "0.72rem", fontWeight: 700,
          color: status === "idle" ? "var(--text-muted)" : "var(--text-primary)",
          lineHeight: 1.3, marginBottom: 4,
          transition: "color 0.3s",
        }}>
          {step.label}
        </div>

        {/* Progress bar for active */}
        {status === "active" && (
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: "100%" }}
            transition={{ duration: step.duration / 1000, ease: "linear" }}
            style={{
              height: 2, borderRadius: 99, marginTop: 6,
              background: `linear-gradient(90deg, ${step.color}, ${step.color}80)`,
            }}
          />
        )}

        {/* Hover tooltip */}
        <AnimatePresence>
          {hovered && (
            <motion.div
              initial={{ opacity: 0, y: 6, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              style={{
                position: "absolute", bottom: "calc(100% + 8px)", left: "50%",
                transform: "translateX(-50%)",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-bright)",
                borderRadius: 10, padding: "8px 12px",
                fontSize: "0.68rem", color: "var(--text-secondary)",
                whiteSpace: "nowrap", maxWidth: 200, textAlign: "center",
                backdropFilter: "blur(20px)",
                boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
                zIndex: 10,
                pointerEvents: "none",
              }}
            >
              <div style={{ fontWeight: 700, color: step.color, marginBottom: 2 }}>{step.label}</div>
              <div style={{ whiteSpace: "normal", lineHeight: 1.4 }}>{step.desc}</div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Connector line below (except last) */}
      {!isLast && (
        <div style={{ position: "relative", width: 2, height: 28, flexShrink: 0 }}>
          <div style={{
            width: 2, height: "100%",
            background: status === "done" ? "rgba(16,185,129,0.5)" : "var(--border-bright)",
            borderRadius: 99,
            transition: "background 0.4s",
          }} />
          {status === "active" && (
            <motion.div
              initial={{ scaleY: 0, opacity: 0 }}
              animate={{ scaleY: [0, 1, 0], opacity: [0, 1, 0] }}
              transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut" }}
              style={{
                position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
                background: `linear-gradient(180deg, transparent, ${step.color}, transparent)`,
                borderRadius: 99,
              }}
            />
          )}
          {status === "done" && (
            <motion.div
              initial={{ scaleY: 0 }} animate={{ scaleY: 1 }}
              transition={{ duration: 0.3 }}
              style={{
                position: "absolute", top: 0, bottom: 0, left: 0, right: 0,
                background: "rgba(16,185,129,0.6)", borderRadius: 99,
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}

/* ── Main page ── */
export default function SimulatePage() {
  const navigate = useNavigate();
  const theme = useStore(s => s.theme);
  const [form, setForm] = useState<SimulateRequest>({
    root_cause_service: "orderdb",
    fault_type: "latency_spike",
    severity: "critical",
    duration_minutes: 5,
  });
  const [running, setRunning] = useState(false);
  const [stepIdx, setStepIdx] = useState(-1);
  const [done, setDone] = useState<SimulateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hoveredScenario, setHoveredScenario] = useState<number | null>(null);

  const applyScenario = (s: typeof SCENARIOS[0]) => {
    setForm({ root_cause_service: s.service, fault_type: s.type, severity: s.badge, duration_minutes: 5 });
    setDone(null); setError(null); setStepIdx(-1);
  };

  const run = useCallback(async () => {
    setRunning(true); setError(null); setDone(null); setStepIdx(0);
    for (let i = 0; i < PIPELINE_STEPS.length; i++) {
      setStepIdx(i);
      await new Promise(r => setTimeout(r, PIPELINE_STEPS[i].duration));
    }
    try {
      const resp = await simulateFault(form);
      setDone(resp);
      setStepIdx(PIPELINE_STEPS.length);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Backend offline — start the FastAPI server on port 8000.");
      setStepIdx(-1);
    } finally {
      setRunning(false);
    }
  }, [form]);

  const isLight = theme === "light";

  return (
    <div className="page-content">
      <div className="page-bg" />

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 32 }}>
        <h1 className="page-title" style={{ background: "var(--grad-brand)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
          Fault Simulation
        </h1>
        <p className="page-subtitle">
          Inject synthetic failures and watch the 8-stage SYNAPSE RCA pipeline execute in real time
        </p>
      </motion.div>

      {/* Error Banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "1rem 1.25rem", borderRadius: 12, marginBottom: 20,
              background: isLight ? "rgba(220,38,38,0.06)" : "rgba(239,68,68,0.07)",
              border: "1px solid rgba(239,68,68,0.3)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <AlertCircle size={18} color="#ef4444" />
              <div>
                <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#ef4444" }}>Pipeline Error</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>{error}</div>
              </div>
            </div>
            <button
              onClick={() => { setError(null); run(); }}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "6px 14px", borderRadius: 8,
                background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)",
                color: "#f87171", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer",
              }}
            >
              <RotateCcw size={13} /> Retry
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Success Banner */}
      <AnimatePresence>
        {done && (
          <motion.div
            initial={{ opacity: 0, scale: 0.97, height: 0 }}
            animate={{ opacity: 1, scale: 1, height: "auto" }}
            exit={{ opacity: 0, scale: 0.97, height: 0 }}
            style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "1rem 1.25rem", borderRadius: 12, marginBottom: 20,
              background: isLight ? "rgba(5,150,105,0.06)" : "rgba(16,185,129,0.07)",
              border: "1px solid rgba(16,185,129,0.3)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300 }}>
                <CheckCircle size={20} color="#10b981" />
              </motion.div>
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#10b981" }}>RCA Complete!</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "JetBrains Mono" }}>
                  {done.incident_id?.slice(0, 20)}…
                </div>
              </div>
            </div>
            <button
              onClick={() => navigate(`/incidents/${done.incident_id}`)}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "6px 16px", borderRadius: 8,
                background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)",
                color: "#34d399", fontSize: "0.8rem", fontWeight: 600, cursor: "pointer",
              }}
            >
              View Report <ChevronRight size={14} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 420px", gap: 24, alignItems: "start" }}>

        {/* ── LEFT: Scenarios + Form + Run ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

          {/* Quick Scenarios */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
            <div className="section-label" style={{ marginBottom: 12 }}>Quick Scenarios</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {SCENARIOS.map((s, i) => {
                const ScenarioIcon = s.icon;
                const isSelected = form.root_cause_service === s.service && form.fault_type === s.type;
                return (
                  <motion.button
                    key={s.title}
                    onHoverStart={() => setHoveredScenario(i)}
                    onHoverEnd={() => setHoveredScenario(null)}
                    whileHover={{ scale: 1.02, y: -2 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => applyScenario(s)}
                    style={{
                      textAlign: "left", cursor: "pointer", fontFamily: "inherit",
                      background: isSelected
                        ? (isLight ? `rgba(${s.color === "#f43f5e" ? "220,38,38" : s.color === "#f97316" ? "234,88,12" : s.color === "#f59e0b" ? "180,83,9" : "79,70,229"},0.08)` : `${s.color}15`)
                        : "var(--bg-card)",
                      border: `1.5px solid ${isSelected ? s.color + "60" : "var(--border)"}`,
                      borderRadius: 16, padding: "1.1rem",
                      transition: "all 0.2s ease",
                      boxShadow: isSelected
                        ? `0 0 20px ${s.color}20, 0 2px 12px rgba(0,0,0,0.15)`
                        : "0 2px 8px rgba(0,0,0,0.06)",
                      backdropFilter: "blur(12px)",
                      position: "relative", overflow: "hidden",
                    }}
                  >
                    {/* Selected glow line */}
                    {isSelected && (
                      <motion.div
                        initial={{ scaleX: 0 }} animate={{ scaleX: 1 }}
                        style={{
                          position: "absolute", top: 0, left: 0, right: 0, height: 2,
                          background: `linear-gradient(90deg, transparent, ${s.color}, transparent)`,
                          borderRadius: "16px 16px 0 0",
                        }}
                      />
                    )}

                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                      <div style={{
                        width: 36, height: 36, borderRadius: 10,
                        background: `${s.color}18`, border: `1px solid ${s.color}35`,
                        display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                      }}>
                        <ScenarioIcon size={16} color={s.color} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--text-primary)" }}>{s.title}</div>
                        <span style={{
                          fontSize: "0.63rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em",
                          color: s.badge === "critical" ? "#f43f5e" : s.badge === "high" ? "#f97316" : "#f59e0b",
                        }}>
                          {s.badge}
                        </span>
                      </div>
                    </div>
                    <p style={{ fontSize: "0.73rem", color: "var(--text-muted)", lineHeight: 1.5, margin: 0 }}>{s.desc}</p>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>

          {/* Custom Config */}
          <motion.div className="card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <div className="section-label" style={{ marginBottom: 14 }}>Custom Configuration</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              {[
                {
                  label: "Root Cause Service",
                  content: (
                    <select className="input" value={form.root_cause_service}
                      onChange={e => setForm(f => ({ ...f, root_cause_service: e.target.value }))}>
                      {SERVICES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  ),
                },
                {
                  label: "Fault Type",
                  content: (
                    <select className="input" value={form.fault_type}
                      onChange={e => setForm(f => ({ ...f, fault_type: e.target.value }))}>
                      {FAULT_TYPES.map(ft => <option key={ft.value} value={ft.value}>{ft.icon} {ft.label}</option>)}
                    </select>
                  ),
                },
                {
                  label: "Severity",
                  content: (
                    <select className="input" value={form.severity}
                      onChange={e => setForm(f => ({ ...f, severity: e.target.value }))}>
                      {["critical", "high", "medium", "low"].map(s => (
                        <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                      ))}
                    </select>
                  ),
                },
                {
                  label: "Duration (minutes)",
                  content: (
                    <input type="number" className="input" min={1} max={60} value={form.duration_minutes}
                      onChange={e => setForm(f => ({ ...f, duration_minutes: Number(e.target.value) }))} />
                  ),
                },
              ].map(({ label, content }) => (
                <div key={label}>
                  <label style={{ fontSize: "0.73rem", color: "var(--text-muted)", fontWeight: 600, display: "block", marginBottom: 6 }}>
                    {label}
                  </label>
                  {content}
                </div>
              ))}
            </div>

            <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 8,
              padding: "10px 12px", borderRadius: 8,
              background: isLight ? "rgba(79,70,229,0.05)" : "rgba(99,102,241,0.06)",
              border: "1px solid rgba(99,102,241,0.15)" }}>
              <Info size={14} color="var(--accent-indigo)" />
              <span style={{ fontSize: "0.73rem", color: "var(--text-muted)" }}>
                SYNAPSE will simulate the fault, run GNN anomaly detection, causal inference, and generate an LLM RCA report.
              </span>
            </div>
          </motion.div>

          {/* Run Button */}
          <motion.button
            className="btn btn-gradient btn-lg"
            onClick={run}
            disabled={running}
            whileHover={{ scale: running ? 1 : 1.02, boxShadow: running ? undefined : "0 0 32px rgba(99,102,241,0.4)" }}
            whileTap={{ scale: 0.98 }}
            style={{ width: "100%", justifyContent: "center", fontSize: "1rem", position: "relative", overflow: "hidden" }}
          >
            {running && (
              <motion.div
                initial={{ x: "-100%" }} animate={{ x: "100%" }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                style={{
                  position: "absolute", inset: 0,
                  background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent)",
                  pointerEvents: "none",
                }}
              />
            )}
            {running
              ? <><Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> Running Pipeline…</>
              : <><Play size={16} /> Run RCA Pipeline</>
            }
          </motion.button>
        </div>

        {/* ── RIGHT: Animated Pipeline ── */}
        <motion.div
          initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.08 }}
          style={{ position: "sticky", top: 78 }}
        >
          <div className="card" style={{ padding: "1.5rem 1.25rem" }}>
            {/* Header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 8,
                  background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.3)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <Activity size={14} color="var(--accent-indigo)" />
                </div>
                <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                  Pipeline Execution
                </span>
              </div>
              <AnimatePresence>
                {running && (
                  <motion.span
                    initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    style={{
                      display: "flex", alignItems: "center", gap: 5,
                      fontSize: "0.65rem", fontWeight: 700,
                      color: "var(--accent-indigo)", letterSpacing: "0.05em",
                    }}
                  >
                    <motion.span
                      animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                      style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor", display: "inline-block" }}
                    />
                    LIVE
                  </motion.span>
                )}
                {done && (
                  <motion.span
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    style={{ fontSize: "0.65rem", fontWeight: 700, color: "#10b981" }}
                  >
                    ✓ COMPLETE
                  </motion.span>
                )}
              </AnimatePresence>
            </div>

            {/* Pipeline Nodes (vertical) */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              {PIPELINE_STEPS.map((step, i) => {
                const isDone = stepIdx > i || (!running && done != null);
                const isActive = stepIdx === i && running;
                const isError = !running && error != null && stepIdx === -1 && i === 0;
                const status = isError ? "error" : isDone ? "done" : isActive ? "active" : "idle";
                return (
                  <PipelineNode
                    key={i}
                    step={step}
                    index={i}
                    status={status}
                    isLast={i === PIPELINE_STEPS.length - 1}
                  />
                );
              })}
            </div>

            {/* Overall Progress Bar */}
            <div style={{ marginTop: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                <span>Overall Progress</span>
                <span style={{ fontFamily: "JetBrains Mono", color: "var(--accent-indigo)" }}>
                  {done ? "100" : stepIdx < 0 ? "0" : Math.round((stepIdx / PIPELINE_STEPS.length) * 100)}%
                </span>
              </div>
              <div style={{ height: 4, borderRadius: 99, background: "var(--bg-elevated)", overflow: "hidden" }}>
                <motion.div
                  animate={{
                    width: done ? "100%"
                      : stepIdx < 0 ? "0%"
                      : `${(stepIdx / PIPELINE_STEPS.length) * 100}%`,
                  }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                  style={{
                    height: "100%", borderRadius: 99,
                    background: done
                      ? "linear-gradient(90deg, #10b981, #34d399)"
                      : "linear-gradient(90deg, #6366f1, #8b5cf6)",
                  }}
                />
              </div>
            </div>

            {/* Result summary */}
            <AnimatePresence>
              {done && (
                <motion.div
                  initial={{ opacity: 0, height: 0, marginTop: 0 }}
                  animate={{ opacity: 1, height: "auto", marginTop: 16 }}
                  style={{
                    padding: "12px 14px", borderRadius: 10,
                    background: "rgba(16,185,129,0.07)", border: "1px solid rgba(16,185,129,0.2)",
                  }}
                >
                  <div style={{ fontSize: "0.7rem", color: "#34d399", fontWeight: 700, marginBottom: 8, letterSpacing: "0.06em" }}>
                    PIPELINE RESULT
                  </div>
                  {[
                    ["Service", done.injected_fault?.service],
                    ["Fault", done.injected_fault?.type?.replace(/_/g, " ")],
                    ["Incident ID", done.incident_id?.slice(0, 14) + "…"],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.73rem", marginBottom: 3 }}>
                      <span style={{ color: "var(--text-muted)" }}>{k}</span>
                      <span style={{ fontFamily: "JetBrains Mono", color: "var(--text-primary)", fontWeight: 600 }}>{v}</span>
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Architecture legend */}
            <div style={{
              marginTop: 16, padding: "10px 12px", borderRadius: 10,
              background: isLight ? "rgba(79,70,229,0.04)" : "rgba(255,255,255,0.02)",
              border: "1px solid var(--border)",
            }}>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.08em", marginBottom: 8, textTransform: "uppercase" }}>
                Architecture
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {[
                  { icon: "📡", label: "Data Simulator → Ingestion" },
                  { icon: "🧠", label: "GAT Autoencoder (GNN)" },
                  { icon: "🔗", label: "PC Algorithm (Causal)" },
                  { icon: "💬", label: "LLM Reasoner (mock/GPT-4)" },
                  { icon: "📋", label: "SQLite → API Response" },
                ].map(({ icon, label }) => (
                  <div key={label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    <span>{icon}</span>
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .simulate-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
