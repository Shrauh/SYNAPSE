import { useEffect, useRef, useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import { CheckCircle, AlertCircle, Clock, Activity, TrendingUp, Minus } from "lucide-react";
import { useStore } from "../store";

/* ─── Spinner ─── */
export function Spinner({ size = "default" }: { size?: "sm" | "default" | "lg" }) {
  const cls = size === "sm" ? "spinner spinner-sm" : "spinner";
  return <div className={cls} />;
}

/* ─── Status Badge ─── */
const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  healthy:   { label: "Healthy",   cls: "badge-healthy"   },
  degraded:  { label: "Degraded",  cls: "badge-degraded"  },
  warning:   { label: "Warning",   cls: "badge-warning"   },
  critical:  { label: "Critical",  cls: "badge-critical"  },
  analyzing: { label: "Analyzing", cls: "badge-analyzing" },
  detected:  { label: "Detected",  cls: "badge-detected"  },
  resolved:  { label: "Resolved",  cls: "badge-resolved"  },
  error:     { label: "Error",     cls: "badge-error"     },
  high:      { label: "High",      cls: "badge-high"      },
  medium:    { label: "Medium",    cls: "badge-medium"    },
  low:       { label: "Low",       cls: "badge-low"       },
};

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_MAP[status?.toLowerCase()] ?? { label: status, cls: "badge-info" };
  return <span className={`badge ${cfg.cls}`}>{cfg.label}</span>;
}

/* ─── Animated Counter ─── */
export function AnimatedCounter({ value, suffix = "", prefix = "" }: {
  value: number; suffix?: string; prefix?: string;
}) {
  const [display, setDisplay] = useState(0);
  const ref = useRef<number>(0);

  useEffect(() => {
    const start = ref.current;
    const end = value;
    const duration = 800;
    const startTime = performance.now();

    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(start + (end - start) * eased);
      setDisplay(current);
      if (progress < 1) requestAnimationFrame(animate);
      else { ref.current = end; }
    };
    requestAnimationFrame(animate);
  }, [value]);

  return <span>{prefix}{display.toLocaleString()}{suffix}</span>;
}

/* ─── Stat Card ─── */
interface StatCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  color?: "blue" | "purple" | "cyan" | "emerald";
  sub?: string;
  trend?: { value: string; up: boolean };
  animate?: boolean;
}
export function StatCard({
  title, value, icon, color = "blue", sub, trend, animate: doAnimate = false,
}: StatCardProps) {
  const colorMap: Record<string, { icon: string; text: string }> = {
    blue:    { icon: "rgba(59,130,246,0.12)",  text: "#3b82f6"  },
    purple:  { icon: "rgba(139,92,246,0.12)",  text: "#8b5cf6"  },
    cyan:    { icon: "rgba(6,182,212,0.12)",   text: "#06b6d4"  },
    emerald: { icon: "rgba(16,185,129,0.12)",  text: "#10b981"  },
  };
  const c = colorMap[color] ?? colorMap.blue;

  return (
    <motion.div
      className={`stat-card ${color}`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      whileHover={{ scale: 1.015 }}
    >
      {icon && (
        <div className="stat-icon" style={{ background: c.icon }}>
          <span style={{ color: c.text }}>{icon}</span>
        </div>
      )}
      <div className="stat-label">{title}</div>
      <div className="stat-value">
        {doAnimate && typeof value === "number"
          ? <AnimatedCounter value={value} />
          : value}
      </div>
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

/* ─── Score Bar ─── */
export function ScoreBar({ score, size = "default" }: { score: number; size?: "sm" | "default" }) {
  const color = score > 0.8 ? "var(--status-critical)"
    : score > 0.6 ? "var(--status-warning)"
    : score > 0.4 ? "var(--status-degraded)"
    : "var(--status-healthy)";
  const h = size === "sm" ? 3 : 4;
  return (
    <div className="score-bar" style={{ height: h }}>
      <motion.div
        className="score-bar-fill"
        initial={{ width: 0 }}
        animate={{ width: `${score * 100}%` }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        style={{ height: h, background: color, borderRadius: 2 }}
      />
    </div>
  );
}

/* ─── Skeleton Loader ─── */
export function Skeleton({ h = 20, w = "100%", radius = 8 }: { h?: number; w?: string | number; radius?: number }) {
  return (
    <div className="skeleton" style={{ height: h, width: w, borderRadius: radius }} />
  );
}
export function SkeletonCard() {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Skeleton h={14} w="40%" />
      <Skeleton h={36} w="60%" />
      <Skeleton h={12} w="80%" />
    </div>
  );
}

/* ─── Empty State ─── */
export function EmptyState({
  icon, title, desc, action,
}: { icon: string; title: string; desc: string; action?: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        justifyContent: "center", gap: 12, padding: "3rem 2rem", textAlign: "center",
      }}
    >
      <div style={{ fontSize: "2.5rem" }}>{icon}</div>
      <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--text-secondary)" }}>{title}</div>
      <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", maxWidth: 320, lineHeight: 1.55 }}>{desc}</div>
      {action}
    </motion.div>
  );
}

/* ─── Alert Banner ─── */
export function AlertBanner({ type, message }: { type: "error" | "success" | "warning" | "info"; message: string }) {
  const cfg = {
    error:   { bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.3)",   color: "#ef4444",  Icon: AlertCircle  },
    success: { bg: "rgba(16,185,129,0.08)",  border: "rgba(16,185,129,0.3)",  color: "#10b981",  Icon: CheckCircle  },
    warning: { bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.3)",  color: "#f59e0b",  Icon: AlertCircle  },
    info:    { bg: "rgba(59,130,246,0.08)",  border: "rgba(59,130,246,0.3)",  color: "#3b82f6",  Icon: Activity     },
  }[type];
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "0.875rem 1.1rem", borderRadius: 10, marginBottom: 16,
        background: cfg.bg, border: `1px solid ${cfg.border}`,
      }}
    >
      <cfg.Icon size={16} color={cfg.color} />
      <span style={{ fontSize: "0.82rem", color: cfg.color }}>{message}</span>
    </motion.div>
  );
}

/* ─── Section Header ─── */
export function SectionHeader({ title, subtitle, action }: {
  title: string; subtitle?: string; action?: ReactNode;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.25rem" }}>
      <div>
        <h2 className="section-heading">{title}</h2>
        {subtitle && <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 3 }}>{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

/* ─── Connection Status (for sidebar footer) ─── */
export function ConnectionStatus() {
  const wsConnected = useStore(s => s.wsConnected);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.72rem", color: "var(--text-muted)" }}>
      <div style={{
        width: 7, height: 7, borderRadius: "50%",
        background: wsConnected ? "var(--status-healthy)" : "var(--text-muted)",
        boxShadow: wsConnected ? "0 0 6px var(--status-healthy)" : "none",
        animation: wsConnected ? "blink 1.4s infinite" : "none",
      }} />
      {wsConnected ? "Live" : "Offline"}
    </div>
  );
}

/* ─── Infrastructure Card ─── */
const INFRA_GRADIENTS: Record<string, string> = {
  aws:        "linear-gradient(135deg, #1a1200 0%, #2d1f00 100%)",
  ecommerce:  "linear-gradient(135deg, #04120a 0%, #082010 100%)",
  retail:     "linear-gradient(135deg, #08040e 0%, #180a28 100%)",
  streaming:  "linear-gradient(135deg, #0a0408 0%, #200816 100%)",
  rideshare:  "linear-gradient(135deg, #04080e 0%, #081828 100%)",
  k8s:        "linear-gradient(135deg, #040812 0%, #0a1528 100%)",
  docker:     "linear-gradient(135deg, #040a12 0%, #081424 100%)",
};

interface InfraCardProps {
  name: string;
  type: string;
  icon: string;
  image?: string;
  status: "healthy" | "degraded" | "critical";
  services: number;
  incidents: number;
  confidence: number;
  uptime: string;
  accentColor: string;
  gradient?: string;
}

export function InfraCard({ name, type, icon, image, status, services, incidents, confidence, uptime, accentColor }: InfraCardProps) {
  const statusColor = status === "healthy" ? "var(--status-healthy)"
    : status === "degraded" ? "var(--status-degraded)"
    : "var(--status-critical)";

  return (
    <motion.div
      className="infra-card card-glow"
      whileHover={{ scale: 1.02, y: -4 }}
      transition={{ duration: 0.25 }}
    >
      {/* Real photo header */}
      <div className="infra-card-bg" style={{ background: INFRA_GRADIENTS[type] ?? INFRA_GRADIENTS.k8s, overflow: "hidden" }}>
        {/* Real photo */}
        {image && (
          <img
            src={image}
            alt={name}
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: 0.55 }}
            onError={(e) => { (e.target as HTMLImageElement).style.opacity = "0"; }}
          />
        )}
        {/* Dark overlay gradient */}
        <div style={{
          position: "absolute", inset: 0,
          background: `linear-gradient(180deg, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.65) 100%),
            linear-gradient(135deg, ${accentColor}22 0%, transparent 60%)`,
        }} />
        {/* Icon badge top-left */}
        <div style={{
          position: "absolute", top: 12, left: 12,
          width: 38, height: 38, borderRadius: 10,
          background: "rgba(0,0,0,0.55)", backdropFilter: "blur(10px)",
          border: `1px solid ${accentColor}40`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "1.4rem",
        }}>
          {icon}
        </div>
        {/* Status pill */}
        <div style={{
          position: "absolute", top: 12, right: 12,
          display: "flex", alignItems: "center", gap: 5,
          padding: "4px 10px", borderRadius: 99,
          background: "rgba(0,0,0,0.55)", backdropFilter: "blur(8px)",
          border: `1px solid ${statusColor}40`,
        }}>
          <div className={`status-dot ${status}`} />
          <span style={{ fontSize: "0.65rem", fontWeight: 700, color: statusColor, textTransform: "uppercase" }}>
            {status}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="infra-card-body">
        <div className="infra-card-name">{name}</div>
        <div className="infra-card-stats">
          {[
            { label: "Services", value: services },
            { label: "Incidents", value: incidents },
            { label: "AI Confidence", value: `${confidence}%` },
            { label: "Uptime", value: uptime },
          ].map(({ label, value }) => (
            <div key={label} className="infra-stat">
              <div className="infra-stat-label">{label}</div>
              <div className="infra-stat-value">{value}</div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

/* ─── Feature Card ─── */
interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  desc: string;
  benefit: string;
  color: string;
  image?: string;
  delay?: number;
}
export function FeatureCard({ icon, title, desc, benefit, color, image, delay = 0 }: FeatureCardProps) {
  return (
    <motion.div
      className="feature-card card-glow"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      whileHover={{ scale: 1.02, y: -3 }}
      style={{ padding: 0, overflow: "hidden" }}
    >
      {/* Real photo header */}
      {image && (
        <div style={{ position: "relative", height: 90, overflow: "hidden" }}>
          <img
            src={image}
            alt={title}
            style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.7 }}
            onError={(e) => { (e.target as HTMLImageElement).parentElement!.style.display = "none"; }}
          />
          <div style={{
            position: "absolute", inset: 0,
            background: `linear-gradient(180deg, ${color}30 0%, rgba(13,20,36,0.85) 100%)`,
          }} />
          <div style={{
            position: "absolute", bottom: 10, left: 12,
            width: 32, height: 32, borderRadius: 8,
            background: `${color}30`, border: `1px solid ${color}50`,
            backdropFilter: "blur(8px)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ color }}>{icon}</span>
          </div>
        </div>
      )}
      {/* Card body */}
      <div style={{ padding: image ? "0.85rem 1rem 1rem" : "1.5rem" }}>
        {!image && (
          <div className="feature-icon" style={{ background: `${color}18`, border: `1px solid ${color}30`, marginBottom: 14 }}>
            <span style={{ color }}>{icon}</span>
          </div>
        )}
        <div className="feature-title">{title}</div>
        <div className="feature-desc">{desc}</div>
        <div className="feature-benefit">→ {benefit}</div>
      </div>
    </motion.div>
  );
}
