import type { ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, CheckCircle, Clock, Activity } from "lucide-react";
import { useStore } from "../store";

/* ── Spinner ── */
export function Spinner({ size = "default" }: { size?: "sm" | "default" | "lg" }) {
  const cls = size === "sm" ? "spinner spinner-sm" : size === "lg" ? "spinner spinner-lg" : "spinner";
  return <div className={cls} />;
}

/* ── Status Badge ── */
const STATUS_CONFIG: Record<string, { label: string; cls: string; dot?: string }> = {
  healthy:   { label: "Healthy",   cls: "badge-healthy",   dot: "healthy" },
  degraded:  { label: "Degraded",  cls: "badge-degraded",  dot: "degraded" },
  warning:   { label: "Warning",   cls: "badge-warning",   dot: "warning" },
  critical:  { label: "Critical",  cls: "badge-critical",  dot: "critical" },
  analyzing: { label: "Analyzing", cls: "badge-analyzing" },
  detected:  { label: "Detected",  cls: "badge-detected",  dot: "healthy" },
  resolved:  { label: "Resolved",  cls: "badge-resolved",  dot: "healthy" },
  error:     { label: "Error",     cls: "badge-error",     dot: "critical" },
  high:      { label: "High",      cls: "badge-high",      dot: "warning" },
  medium:    { label: "Medium",    cls: "badge-medium",    dot: "degraded" },
  low:       { label: "Low",       cls: "badge-low",       dot: "healthy" },
};
export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status?.toLowerCase()] ?? { label: status, cls: "badge-info" };
  return (
    <span className={`badge badge-dot ${cfg.cls}`} style={{ gap: cfg.dot ? 5 : undefined }}>
      {cfg.dot && <span className={`status-dot ${cfg.dot}`} style={{ width: 5, height: 5 }} />}
      {cfg.label}
    </span>
  );
}

/* ── Stat Card ── */
const COLOR_MAP: Record<string, string> = {
  indigo: "indigo", violet: "violet", cyan: "cyan", emerald: "emerald"
};
interface StatCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  color?: string;
  sub?: string;
  trend?: { value: string; up: boolean };
}
export function StatCard({ title, value, icon, color = "indigo", sub, trend }: StatCardProps) {
  const colorKey = Object.keys(COLOR_MAP).find(k => color.includes(k)) ?? "indigo";
  return (
    <motion.div
      className={`stat-card ${colorKey}`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      {icon && <div className="stat-icon">{icon}</div>}
      <div className="stat-label">{title}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
      {trend && (
        <div className={`stat-trend ${trend.up ? "up" : "down"}`}>
          <span>{trend.up ? "↑" : "↓"}</span>
          <span>{trend.value}</span>
        </div>
      )}
    </motion.div>
  );
}

/* ── Score Bar ── */
export function ScoreBar({ score, size = "default" }: { score: number; size?: "sm" | "default" }) {
  const color = score > 0.8 ? "var(--status-critical)"
    : score > 0.6 ? "var(--status-warning)"
    : score > 0.4 ? "var(--accent-amber)"
    : "var(--accent-emerald)";
  const h = size === "sm" ? 3 : 4;
  return (
    <div className="score-bar" style={{ height: h }}>
      <motion.div
        className="score-bar-fill"
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${score * 100}%` }}
        transition={{ duration: 0.7, ease: "easeOut" }}
      />
    </div>
  );
}

/* ── Anomaly Score Chip ── */
export function AnomalyChip({ score }: { score: number }) {
  const color = score > 0.8 ? "#f87171"
    : score > 0.6 ? "#fb923c"
    : score > 0.4 ? "#fbbf24"
    : "#34d399";
  return (
    <span style={{ fontFamily: "JetBrains Mono", fontSize: "0.78rem", fontWeight: 600, color, letterSpacing: "0.02em" }}>
      {score.toFixed(3)}
    </span>
  );
}

/* ── Card ── */
export function Card({
  children, className = "", glow = false, style,
}: { children: ReactNode; className?: string; glow?: boolean; style?: React.CSSProperties }) {
  return (
    <div className={`card ${glow ? "card-glow" : ""} ${className}`} style={style}>
      {children}
    </div>
  );
}

/* ── Section Header ── */
export function SectionHeader({ label, title, action }: { label?: string; title: string; action?: ReactNode }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
      <div>
        {label && <div className="section-label">{label}</div>}
        <h2 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 0 }}>{title}</h2>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

/* ── Empty State ── */
export function EmptyState({ icon, title, desc, action }: {
  icon?: ReactNode; title: string; desc?: string; action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      {icon && <div style={{ fontSize: "2.5rem", opacity: 0.3 }}>{icon}</div>}
      <h3>{title}</h3>
      {desc && <p>{desc}</p>}
      {action}
    </div>
  );
}

/* ── Alert Banner ── */
export function AlertBanner({ type, message }: { type: "error" | "success" | "info"; message: string }) {
  const colors = {
    error:   { bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.25)",   text: "#f87171", Icon: AlertTriangle },
    success: { bg: "rgba(16,185,129,0.08)",  border: "rgba(16,185,129,0.25)",  text: "#34d399", Icon: CheckCircle },
    info:    { bg: "rgba(99,102,241,0.08)",  border: "rgba(99,102,241,0.25)",  text: "#a5b4fc", Icon: Activity },
  };
  const c = colors[type];
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        style={{ display: "flex", alignItems: "center", gap: 10, padding: "0.75rem 1rem",
          background: c.bg, border: `1px solid ${c.border}`, borderRadius: "var(--radius-md)",
          fontSize: "0.85rem", color: c.text, marginBottom: 16 }}
      >
        <c.Icon size={15} />
        {message}
      </motion.div>
    </AnimatePresence>
  );
}

/* ── Live Badge ── */
export function LiveBadge({ connected }: { connected: boolean }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em",
      textTransform: "uppercase",
      color: connected ? "var(--accent-emerald)" : "var(--text-muted)",
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%",
        background: connected ? "var(--accent-emerald)" : "var(--text-muted)",
        animation: connected ? "pulse-ring 1.8s infinite" : "none",
      }} />
      {connected ? "Live" : "Offline"}
    </span>
  );
}

/* ── Confidence Gauge ── */
export function ConfidenceGauge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "var(--status-critical)" : pct >= 60 ? "var(--accent-amber)" : "var(--accent-indigo)";
  const r = 36, cx = 44, cy = 44;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <svg width={88} height={88} viewBox="0 0 88 88">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={7} />
        <motion.circle
          cx={cx} cy={cy} r={r}
          fill="none" stroke={color} strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
        <text x={cx} y={cy} textAnchor="middle" dy="0.35em"
          style={{ fill: "var(--text-primary)", fontSize: 16, fontWeight: 800, fontFamily: "Inter" }}>
          {pct}%
        </text>
      </svg>
      <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em" }}>
        Confidence
      </span>
    </div>
  );
}

/* ── Metric Row ── */
export function MetricRow({ label, value, unit = "" }: { label: string; value: string | number; unit?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "0.6rem 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{label}</span>
      <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)",
        fontFamily: unit ? "JetBrains Mono" : "inherit" }}>
        {value}{unit}
      </span>
    </div>
  );
}

/* ── Tag ── */
export function Tag({ children, color = "default" }: { children: ReactNode; color?: "indigo" | "cyan" | "emerald" | "default" }) {
  const colors: Record<string, { bg: string; text: string }> = {
    indigo:  { bg: "rgba(99,102,241,0.12)",  text: "#a5b4fc" },
    cyan:    { bg: "rgba(6,182,212,0.12)",   text: "#67e8f9" },
    emerald: { bg: "rgba(16,185,129,0.12)",  text: "#6ee7b7" },
    default: { bg: "rgba(255,255,255,0.06)", text: "var(--text-secondary)" },
  };
  const c = colors[color] ?? colors.default;
  return (
    <span style={{
      display: "inline-block", padding: "2px 9px",
      borderRadius: 99, fontSize: "0.7rem", fontWeight: 600,
      background: c.bg, color: c.text,
    }}>
      {children}
    </span>
  );
}

/* ── Connection Status Hook Display ── */
export function ConnectionStatus() {
  const connected = useStore(s => s.connected);
  return <LiveBadge connected={connected} />;
}
