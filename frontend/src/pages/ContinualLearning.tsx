import { useEffect, useState, useCallback } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell, PieChart, Pie, Legend,
} from "recharts";
import {
  Brain, RefreshCw, Zap, Database, Shield, Play,
  CheckCircle, AlertCircle, Info, ChevronRight,
} from "lucide-react";
import {
  fetchCLStatus, fetchCLForgettingHistory,
  fetchCLReplayStats, fetchCLEWCStats, triggerCLUpdate,
} from "../api/endpoints";
import type {
  CLDetailedStatus, CLForgettingHistory,
  CLReplayStats, CLEWCStats, CLTriggerResponse,
} from "../types/api";
import { Spinner } from "../components/UI";

// ─── Palette ─────────────────────────────────────────────────────
const TASK_COLORS = [
  "#3b82f6", "#8b5cf6", "#06b6d4", "#10b981",
  "#f59e0b", "#ef4444", "#f97316", "#a78bfa",
];

const FAULT_TYPES = [
  "latency_spike", "crash", "cpu_hog", "memory_leak",
  "network_timeout", "db_connection_pool", "auth_failure",
];

const SERVICES = [
  "database", "api-gateway", "auth-service", "payment-service",
  "order-service", "cache-service", "user-service",
];

// ─── Sub-components ──────────────────────────────────────────────

function StatCard({
  icon: Icon, label, value, sub, color, fill = false,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  color: string;
  fill?: boolean;
}) {
  return (
    <div
      className="card card-glow"
      style={{ position: "relative", overflow: "hidden" }}
    >
      {fill && (
        <div style={{
          position: "absolute", inset: 0,
          background: `radial-gradient(ellipse at 0% 0%, ${color}18 0%, transparent 70%)`,
          pointerEvents: "none",
        }} />
      )}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div style={{
          width: 38, height: 38, borderRadius: 10,
          background: `${color}22`,
          display: "flex", alignItems: "center", justifyContent: "center",
          color, flexShrink: 0,
        }}>
          <Icon size={18} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em" }}>
            {label}
          </div>
          <div style={{ fontSize: "1.7rem", fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.2, fontFamily: "JetBrains Mono" }}>
            {value}
          </div>
          {sub && (
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 2 }}>
              {sub}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ProtectionBadge({ strength }: { strength: string }) {
  const map: Record<string, { bg: string; color: string }> = {
    high:   { bg: "rgba(16,185,129,0.15)",  color: "var(--status-healthy)" },
    medium: { bg: "rgba(245,158,11,0.15)",  color: "var(--status-degraded)" },
    low:    { bg: "rgba(239,68,68,0.15)",   color: "var(--status-critical)" },
  };
  const s = map[strength] ?? map["medium"];
  return (
    <span style={{
      padding: "3px 10px", borderRadius: 99,
      fontSize: "0.72rem", fontWeight: 700,
      textTransform: "uppercase", letterSpacing: "0.06em",
      background: s.bg, color: s.color,
    }}>
      {strength}
    </span>
  );
}

function TaskTypeBadge({ type }: { type: string }) {
  const isNormal = type === "normal_baseline";
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 99,
      fontSize: "0.68rem", fontWeight: 700,
      textTransform: "uppercase", letterSpacing: "0.06em",
      background: isNormal ? "rgba(6,182,212,0.15)" : "rgba(139,92,246,0.15)",
      color: isNormal ? "var(--accent-cyan)" : "var(--accent-purple)",
    }}>
      {type.replace("_", " ")}
    </span>
  );
}

function SectionHeader({ icon: Icon, title, color }: { icon: React.ElementType; title: string; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 18 }}>
      <div style={{
        width: 28, height: 28, borderRadius: 8,
        background: `${color}22`,
        display: "flex", alignItems: "center", justifyContent: "center",
        color,
      }}>
        <Icon size={14} />
      </div>
      <span style={{ fontWeight: 700, fontSize: "0.88rem", color: "var(--text-primary)" }}>{title}</span>
    </div>
  );
}

// ─── Custom Tooltip ───────────────────────────────────────────────
const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--bg-elevated)", border: "1px solid var(--border)",
      borderRadius: 8, padding: "8px 12px", fontSize: "0.78rem",
    }}>
      <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color, fontFamily: "JetBrains Mono" }}>
          {p.name}: {typeof p.value === "number" ? p.value.toFixed(4) : p.value}
        </div>
      ))}
    </div>
  );
};

// ─── Forgetting Rate Chart ────────────────────────────────────────
function ForgettingChart({ data }: { data: CLForgettingHistory | null }) {
  if (!data) return <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}><Spinner /></div>;

  const chartData = data.history.map(h => ({
    ep: `E${h.episode}`,
    forgetting: +(h.forgetting_rate * 100).toFixed(2),
    ewc_penalty: +h.ewc_penalty.toFixed(4),
    task: h.task_id.replace("(demo) ", ""),
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" />
        <XAxis dataKey="ep" stroke="var(--text-muted)" tick={{ fontSize: 10 }} />
        <YAxis stroke="var(--text-muted)" tick={{ fontSize: 10 }} unit="%" />
        <Tooltip content={<ChartTooltip />} />
        <Line
          type="monotone" dataKey="forgetting" name="Forgetting Rate"
          stroke="var(--accent-blue)" strokeWidth={2.5}
          dot={{ r: 3, fill: "var(--accent-blue)" }}
          activeDot={{ r: 5 }}
        />
        <Line
          type="monotone" dataKey="ewc_penalty" name="EWC Penalty"
          stroke="var(--accent-purple)" strokeWidth={1.5} strokeDasharray="5 3"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ─── Replay Buffer Pie ────────────────────────────────────────────
function ReplayPie({ data }: { data: CLReplayStats | null }) {
  if (!data) return <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}><Spinner /></div>;

  const dist = data.task_distribution;
  const entries = Object.entries(dist);
  if (entries.length === 0) {
    return (
      <div style={{ height: 200, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
        <Database size={28} color="var(--text-muted)" />
        <span style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>Buffer empty — trigger a CL update</span>
      </div>
    );
  }

  const pieData = entries.map(([name, value]) => ({ name, value }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={pieData} dataKey="value" nameKey="name"
          cx="50%" cy="50%" innerRadius={55} outerRadius={80}
          paddingAngle={3}
        >
          {pieData.map((_, i) => (
            <Cell key={i} fill={TASK_COLORS[i % TASK_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: "0.72rem" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

// ─── EWC Fisher Bar ───────────────────────────────────────────────
function EWCBar({ data }: { data: CLEWCStats | null }) {
  if (!data) return <div style={{ height: 180, display: "flex", alignItems: "center", justifyContent: "center" }}><Spinner /></div>;

  if (data.tasks.length === 0) {
    return (
      <div style={{ height: 180, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
        <Shield size={28} color="var(--text-muted)" />
        <span style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>No EWC tasks registered yet</span>
      </div>
    );
  }

  const chartData = data.tasks.map(t => ({
    name: t.task_id.length > 14 ? t.task_id.slice(0, 13) + "…" : t.task_id,
    penalty: +t.ewc_penalty_contribution.toFixed(2),
    fisher: +(t.fisher_mean * 1000).toFixed(3),
  }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" />
        <XAxis dataKey="name" stroke="var(--text-muted)" tick={{ fontSize: 9 }} />
        <YAxis stroke="var(--text-muted)" tick={{ fontSize: 10 }} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="penalty" name="EWC Penalty" radius={[4, 4, 0, 0]}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={TASK_COLORS[i % TASK_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── Main Page ────────────────────────────────────────────────────
export default function ContinualLearningPage() {
  const [status,     setStatus]     = useState<CLDetailedStatus | null>(null);
  const [forgetting, setForgetting] = useState<CLForgettingHistory | null>(null);
  const [replay,     setReplay]     = useState<CLReplayStats | null>(null);
  const [ewc,        setEWC]        = useState<CLEWCStats | null>(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState<string | null>(null);

  // Trigger form state
  const [taskId,         setTaskId]         = useState("new_fault_pattern");
  const [faultType,      setFaultType]      = useState("latency_spike");
  const [rootCause,      setRootCause]      = useState("database");
  const [numScenarios,   setNumScenarios]   = useState(5);
  const [lambdaOverride, setLambdaOverride] = useState<string>("");
  const [triggering,     setTriggering]     = useState(false);
  const [triggerResult,  setTriggerResult]  = useState<CLTriggerResponse | null>(null);
  const [triggerError,   setTriggerError]   = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, f, r, e] = await Promise.all([
        fetchCLStatus(),
        fetchCLForgettingHistory(),
        fetchCLReplayStats(),
        fetchCLEWCStats(),
      ]);
      setStatus(s);
      setForgetting(f);
      setReplay(r);
      setEWC(e);
    } catch {
      setError("Could not reach the backend. Is it running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleTrigger = async () => {
    setTriggering(true);
    setTriggerResult(null);
    setTriggerError(null);
    try {
      const res = await triggerCLUpdate({
        task_id: taskId,
        fault_type: faultType,
        root_cause_service: rootCause,
        num_scenarios: numScenarios,
        ewc_lambda_override: lambdaOverride ? parseFloat(lambdaOverride) : undefined,
      });
      setTriggerResult(res);
      // Refresh all data after update
      await load();
    } catch (e: any) {
      setTriggerError(e?.response?.data?.detail ?? "Trigger failed. Check backend logs.");
    } finally {
      setTriggering(false);
    }
  };

  // Buffer fill bar color
  const fillPct = status?.replay_buffer_fill_pct ?? 0;
  const fillColor = fillPct > 80 ? "var(--accent-blue)" : fillPct > 40 ? "var(--accent-cyan)" : "var(--text-muted)";

  return (
    <div style={{ padding: "84px 2rem 3rem", maxWidth: 1200, margin: "0 auto" }}>

      {/* ── Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 12,
              background: "linear-gradient(135deg,#3b82f6,#8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Brain size={20} color="#fff" />
            </div>
            <h1 style={{ fontSize: "1.55rem", fontWeight: 800, letterSpacing: "-0.03em" }}>
              Continual Learning
            </h1>
            {status && (
              <span style={{
                padding: "3px 10px", borderRadius: 99, fontSize: "0.7rem", fontWeight: 700,
                background: status.initialized ? "rgba(16,185,129,0.15)" : "rgba(245,158,11,0.15)",
                color: status.initialized ? "var(--status-healthy)" : "var(--status-degraded)",
              }}>
                {status.initialized ? "● ACTIVE" : "○ WAITING"}
              </span>
            )}
          </div>
          <p style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
            EWC · Experience Replay · Forgetting Prevention · Incremental Task Adaptation
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={loading} style={{ gap: 6 }}>
          <RefreshCw size={13} className={loading ? "spin" : ""} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "6rem" }}>
          <Spinner />
        </div>
      ) : error ? (
        <div className="card" style={{ color: "var(--status-critical)", textAlign: "center", padding: "3rem", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <AlertCircle size={32} />
          <div style={{ fontWeight: 700 }}>Backend Unreachable</div>
          <div style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>{error}</div>
          <button className="btn btn-ghost" onClick={load} style={{ marginTop: 8 }}>Retry</button>
        </div>
      ) : (
        <>
          {/* ── Stats Row ── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 20 }}>
            <StatCard
              icon={Brain}
              label="Tasks Learned"
              value={status?.tasks_learned ?? 0}
              sub={`${status?.ewc_tasks_seen ?? 0} EWC-registered`}
              color="var(--accent-blue)"
              fill
            />
            <StatCard
              icon={Shield}
              label="Forgetting Rate"
              value={`${((status?.forgetting_rate ?? 0) * 100).toFixed(1)}%`}
              sub="lower = better retention"
              color={
                (status?.forgetting_rate ?? 0) < 0.05
                  ? "var(--status-healthy)"
                  : (status?.forgetting_rate ?? 0) < 0.15
                  ? "var(--status-degraded)"
                  : "var(--status-critical)"
              }
              fill
            />
            <StatCard
              icon={Database}
              label="Replay Buffer"
              value={status?.replay_buffer_size ?? 0}
              sub={`of ${status?.replay_buffer_max ?? 500} max (${fillPct}% full)`}
              color="var(--accent-cyan)"
              fill
            />
            <StatCard
              icon={Zap}
              label="EWC Lambda"
              value={status?.ewc_lambda.toLocaleString() ?? "5000"}
              sub="weight protection strength"
              color="var(--accent-purple)"
              fill
            />
          </div>

          {/* ── Buffer Fill Progress ── */}
          <div className="card" style={{ marginBottom: 20, padding: "1rem 1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Replay Buffer Fullness
              </span>
              <span style={{ fontFamily: "JetBrains Mono", fontSize: "0.78rem", color: fillColor }}>
                {fillPct}%
              </span>
            </div>
            <div className="score-bar" style={{ height: 8 }}>
              <div
                className="score-bar-fill"
                style={{
                  width: `${fillPct}%`,
                  background: `linear-gradient(90deg, ${fillColor}, var(--accent-blue))`,
                  boxShadow: fillPct > 10 ? `0 0 8px ${fillColor}55` : "none",
                }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: "0.7rem", color: "var(--text-muted)" }}>
              <span>0 samples</span>
              <span>Total seen: <span style={{ fontFamily: "JetBrains Mono" }}>{status?.total_samples_seen ?? 0}</span></span>
              <span>{status?.replay_buffer_max ?? 500} samples</span>
            </div>
          </div>

          {/* ── Charts Row 1 ── */}
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginBottom: 16 }}>
            {/* Forgetting Rate Chart */}
            <div className="card">
              <SectionHeader icon={Shield} title="Forgetting Rate History (EWC Effectiveness)" color="var(--accent-blue)" />
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 12 }}>
                Blue = forgetting rate (%) across training episodes. Purple dashed = EWC penalty magnitude.
                EWC prevents the model forgetting previously learned fault patterns.
              </div>
              <ForgettingChart data={forgetting} />
            </div>

            {/* Replay Buffer Distribution */}
            <div className="card">
              <SectionHeader icon={Database} title="Buffer Distribution" color="var(--accent-cyan)" />
              <ReplayPie data={replay} />
            </div>
          </div>

          {/* ── Charts Row 2 ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 16, marginBottom: 16 }}>
            {/* EWC Bar */}
            <div className="card">
              <SectionHeader icon={Zap} title="EWC Penalty per Task" color="var(--accent-purple)" />
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 12 }}>
                Higher bar = stronger regularization protecting that task's learned weights.
              </div>
              {ewc && (
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Protection:</span>
                  <ProtectionBadge strength={ewc.protection_strength} />
                  <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginLeft: "auto" }}>
                    λ = <span style={{ fontFamily: "JetBrains Mono", color: "var(--text-primary)" }}>{ewc.ewc_lambda.toLocaleString()}</span>
                  </span>
                </div>
              )}
              <EWCBar data={ewc} />
            </div>

            {/* Task Registry Table */}
            <div className="card">
              <SectionHeader icon={Brain} title="Task Registry" color="var(--accent-blue)" />
              {status && status.tasks.length === 0 ? (
                <div style={{
                  display: "flex", flexDirection: "column", alignItems: "center",
                  justifyContent: "center", gap: 10, padding: "2.5rem 0",
                }}>
                  <Info size={28} color="var(--text-muted)" />
                  <span style={{ color: "var(--text-muted)", fontSize: "0.82rem", textAlign: "center" }}>
                    No tasks registered yet.<br />
                    Simulate a fault or run the RCA pipeline to register the first task.
                  </span>
                </div>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Task ID</th>
                        <th>Type</th>
                        <th>In Buffer</th>
                        <th>EWC</th>
                        <th>Loss</th>
                      </tr>
                    </thead>
                    <tbody>
                      {status?.tasks.map((t, i) => (
                        <tr key={t.task_id}>
                          <td>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <div style={{
                                width: 8, height: 8, borderRadius: "50%",
                                background: TASK_COLORS[i % TASK_COLORS.length], flexShrink: 0,
                              }} />
                              <span style={{ fontFamily: "JetBrains Mono", fontSize: "0.78rem", color: "var(--text-primary)" }}>
                                {t.task_id}
                              </span>
                            </div>
                          </td>
                          <td><TaskTypeBadge type={t.task_type} /></td>
                          <td style={{ fontFamily: "JetBrains Mono" }}>{t.samples_in_buffer}</td>
                          <td>
                            <span style={{
                              fontSize: "0.7rem", fontWeight: 700,
                              color: t.ewc_registered ? "var(--status-healthy)" : "var(--text-muted)",
                            }}>
                              {t.ewc_registered ? "✓ Yes" : "—"}
                            </span>
                          </td>
                          <td style={{ fontFamily: "JetBrains Mono", fontSize: "0.78rem" }}>
                            {t.performance_metric.toFixed(4)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* ── How It Works ── */}
          <div className="card" style={{ marginBottom: 16, padding: "1.25rem 1.5rem" }}>
            <SectionHeader icon={Info} title="How SYNAPSE Continual Learning Works" color="var(--accent-cyan)" />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
              {[
                {
                  step: "1", title: "Learn New Fault Pattern",
                  body: "When a new fault type is simulated, SYNAPSE runs the GNN on the incident data and updates the model with reconstruction loss.",
                  color: "var(--accent-blue)",
                },
                {
                  step: "2", title: "EWC Protects Past Knowledge",
                  body: "Elastic Weight Consolidation computes a Fisher Information Matrix for critical weights. These weights are regularized to prevent overwriting learned fault signatures.",
                  color: "var(--accent-purple)",
                },
                {
                  step: "3", title: "Replay Buffer Reinforces Memory",
                  body: "A reservoir-sampled buffer stores past training examples. During each new training pass, past samples are replayed alongside new data to prevent catastrophic forgetting.",
                  color: "var(--accent-cyan)",
                },
              ].map(c => (
                <div key={c.step} style={{
                  background: "var(--bg-elevated)", borderRadius: "var(--radius-md)",
                  padding: "1rem", border: `1px solid var(--border)`,
                }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: `${c.color}22`, color: c.color,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontWeight: 800, fontSize: "0.82rem", marginBottom: 8,
                  }}>
                    {c.step}
                  </div>
                  <div style={{ fontWeight: 700, fontSize: "0.85rem", marginBottom: 6, color: "var(--text-primary)" }}>{c.title}</div>
                  <div style={{ fontSize: "0.77rem", color: "var(--text-muted)", lineHeight: 1.6 }}>{c.body}</div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Trigger Panel ── */}
          <div className="card" style={{
            border: "1px solid var(--border-bright)",
            background: "var(--bg-card)",
          }}>
            <SectionHeader icon={Play} title="Trigger Incremental CL Update" color="var(--status-healthy)" />
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 20, lineHeight: 1.6 }}>
              Register a new fault pattern with the continual learning system. This adds synthetic training
              examples to the replay buffer and marks the task for EWC registration on next full training cycle.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr auto", gap: 12, alignItems: "flex-end" }}>
              {/* Task ID */}
              <div>
                <label style={{ display: "block", fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Task ID
                </label>
                <input
                  id="cl-task-id"
                  className="input"
                  value={taskId}
                  onChange={e => setTaskId(e.target.value)}
                  placeholder="e.g. fault_db_v2"
                />
              </div>

              {/* Fault Type */}
              <div>
                <label style={{ display: "block", fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Fault Type
                </label>
                <select id="cl-fault-type" className="input" value={faultType} onChange={e => setFaultType(e.target.value)}>
                  {FAULT_TYPES.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>

              {/* Root Cause Service */}
              <div>
                <label style={{ display: "block", fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Root Cause Service
                </label>
                <select id="cl-root-cause" className="input" value={rootCause} onChange={e => setRootCause(e.target.value)}>
                  {SERVICES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              {/* Num Scenarios */}
              <div>
                <label style={{ display: "block", fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Scenarios (1–20)
                </label>
                <input
                  id="cl-num-scenarios"
                  className="input"
                  type="number" min={1} max={20}
                  value={numScenarios}
                  onChange={e => setNumScenarios(parseInt(e.target.value) || 5)}
                />
              </div>

              {/* Trigger Button */}
              <button
                id="cl-trigger-btn"
                className="btn btn-primary"
                onClick={handleTrigger}
                disabled={triggering || !taskId.trim()}
                style={{ height: 38, whiteSpace: "nowrap", gap: 6 }}
              >
                {triggering ? <Spinner /> : <><Play size={13} /> Run Update</>}
              </button>
            </div>

            {/* Lambda override */}
            <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", whiteSpace: "nowrap" }}>
                EWC λ Override (optional)
              </span>
              <input
                id="cl-lambda"
                className="input"
                style={{ maxWidth: 140 }}
                placeholder="default: 5000"
                value={lambdaOverride}
                onChange={e => setLambdaOverride(e.target.value)}
              />
              <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                Higher = stronger weight protection against forgetting.
              </span>
            </div>

            {/* Trigger Result */}
            {triggerResult && (
              <div style={{
                marginTop: 16, padding: "12px 16px", borderRadius: "var(--radius-md)",
                background: triggerResult.success ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
                border: `1px solid ${triggerResult.success ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
                display: "flex", alignItems: "flex-start", gap: 10,
              }}>
                {triggerResult.success
                  ? <CheckCircle size={16} color="var(--status-healthy)" style={{ marginTop: 2, flexShrink: 0 }} />
                  : <AlertCircle size={16} color="var(--status-critical)" style={{ marginTop: 2, flexShrink: 0 }} />
                }
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.82rem", color: triggerResult.success ? "var(--status-healthy)" : "var(--status-critical)", marginBottom: 3 }}>
                    {triggerResult.success ? "Update Successful" : "Update Failed"}
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>{triggerResult.message}</div>
                  <div style={{
                    display: "flex", gap: 16, marginTop: 8, fontSize: "0.72rem",
                    color: "var(--text-muted)", fontFamily: "JetBrains Mono",
                  }}>
                    <span>Samples Added: <b style={{ color: "var(--text-primary)" }}>{triggerResult.samples_added}</b></span>
                    <span>New Forgetting Rate: <b style={{ color: "var(--text-primary)" }}>{(triggerResult.new_forgetting_rate * 100).toFixed(2)}%</b></span>
                    <span>Time: <b style={{ color: "var(--text-primary)" }}>{triggerResult.execution_time_ms}ms</b></span>
                  </div>
                </div>
              </div>
            )}

            {triggerError && (
              <div style={{
                marginTop: 16, padding: "12px 16px", borderRadius: "var(--radius-md)",
                background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)",
                display: "flex", alignItems: "center", gap: 10,
              }}>
                <AlertCircle size={16} color="var(--status-critical)" />
                <span style={{ fontSize: "0.82rem", color: "var(--status-critical)" }}>{triggerError}</span>
              </div>
            )}

            {/* Task ID list */}
            {status && status.task_ids.length > 0 && (
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
                <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Registered Tasks
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
                  {status.task_ids.map((t, i) => (
                    <span key={t} style={{
                      padding: "3px 10px", borderRadius: 99, fontSize: "0.72rem",
                      fontFamily: "JetBrains Mono", fontWeight: 600,
                      background: `${TASK_COLORS[i % TASK_COLORS.length]}22`,
                      color: TASK_COLORS[i % TASK_COLORS.length],
                      display: "flex", alignItems: "center", gap: 4,
                    }}>
                      <ChevronRight size={10} />
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
