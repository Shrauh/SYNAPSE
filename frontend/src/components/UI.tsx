import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  color?: string;
  sub?: string;
}

export function StatCard({ title, value, icon, color = "var(--accent-blue)", sub }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2, transition: { duration: 0.15 } }}
      className="card card-glow"
      style={{
        position: "relative",
        overflow: "hidden",
        border: "1px solid var(--border)",
        background: "var(--bg-card)",
        transition: "border-color 0.2s, box-shadow 0.2s",
      }}
    >
      {/* Glow accent */}
      <div style={{
        position: "absolute", top: -20, right: -20,
        width: 100, height: 100, borderRadius: "50%",
        background: color, opacity: 0.12, filter: "blur(32px)",
        pointerEvents: "none",
      }} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>
          {title}
        </span>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: `${color}18`,
          border: `1px solid ${color}33`,
          display: "flex", alignItems: "center", justifyContent: "center",
          color,
          boxShadow: `0 0 12px ${color}22`,
        }}>
          {icon}
        </div>
      </div>
      <div style={{ fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 6, display: "flex", alignItems: "center", gap: 4 }}>
          {sub}
        </div>
      )}
    </motion.div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const norm = (status || "").toLowerCase();
  
  let badgeClass = "badge";
  let dotColor = "var(--status-healthy)";
  
  if (norm.includes("crit") || norm.includes("error") || norm.includes("fail")) {
    badgeClass += " badge-critical";
    dotColor = "var(--status-critical)";
  } else if (norm.includes("warn") || norm === "high") {
    badgeClass += " badge-warning";
    dotColor = "var(--status-warning)";
  } else if (norm.includes("degrad") || norm === "medium") {
    badgeClass += " badge-degraded";
    dotColor = "var(--status-degraded)";
  } else if (norm.includes("analyz") || norm.includes("run") || norm === "open" || norm === "active") {
    badgeClass += " badge-analyzing";
    dotColor = "var(--accent-blue)";
  } else {
    badgeClass += " badge-healthy";
    dotColor = "var(--status-healthy)";
  }

  return (
    <span className={badgeClass} style={{ gap: 6, textTransform: "uppercase", fontWeight: 600 }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%",
        background: dotColor, boxShadow: `0 0 6px ${dotColor}`,
        display: "inline-block"
      }} />
      {status}
    </span>
  );
}

export function ScoreBar({ score }: { score: number }) {
  const color = score > 0.8 ? "var(--status-critical)"
    : score > 0.6 ? "var(--status-warning)"
    : score > 0.4 ? "var(--status-degraded)"
    : "var(--status-healthy)";

  const pct = Math.min(100, Math.max(0, Math.round(score * 100)));

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, width: "100%" }}>
      <div className="score-bar" style={{ flex: 1, height: 6, borderRadius: 99, background: "rgba(255,255,255,0.06)" }}>
        <div
          className="score-bar-fill"
          style={{
            width: `${pct}%`,
            background: color,
            borderRadius: 99,
            boxShadow: score > 0.6 ? `0 0 8px ${color}` : "none",
            transition: "width 0.6s cubic-bezier(0.4, 0, 0.2, 1)"
          }}
        />
      </div>
      <span style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", fontWeight: 600, color, minWidth: 36, textAlign: "right" }}>
        {score.toFixed(2)}
      </span>
    </div>
  );
}

export function Spinner() {
  return <div className="spinner" />;
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "1rem" }}>
      <div style={{ width: 3, height: 12, background: "var(--primary)", borderRadius: 2 }} />
      <div className="section-title" style={{ marginBottom: 0 }}>{children}</div>
    </div>
  );
}
