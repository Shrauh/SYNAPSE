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

function getScoreColor(score: number): string {
  const clamped = Math.max(0, Math.min(1, score));
  // Smooth continuous transition: green (142) -> yellow (45) -> red (0)
  const hue = clamped < 0.5
    ? 142 - (clamped / 0.5) * (142 - 45)
    : 45 - ((clamped - 0.5) / 0.5) * 45;
  return `hsl(${Math.round(hue)}, 90%, 50%)`;
}

export function ScoreBar({ score }: { score: number }) {
  const color = getScoreColor(score);
  const pct = Math.min(100, Math.max(0, Math.round(score * 100)));

  // Dynamic gradient spanning from green through yellow to current score color
  const gradientFill = score > 0.4
    ? `linear-gradient(90deg, #10b981 0%, #f59e0b 60%, ${color} 100%)`
    : `linear-gradient(90deg, #10b981 0%, ${color} 100%)`;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, width: "100%" }}>
      <div
        className="score-bar"
        style={{
          flex: 1,
          height: 16,
          borderRadius: 99,
          background: "rgba(255,255,255,0.06)",
          position: "relative",
          overflow: "hidden",
          border: "1px solid rgba(255,255,255,0.06)",
          boxShadow: "inset 0 1px 3px rgba(0,0,0,0.4)"
        }}
      >
        <div
          className="score-bar-fill"
          style={{
            width: `${pct}%`,
            background: gradientFill,
            borderRadius: 99,
            height: "100%",
            boxShadow: score > 0.4 ? `0 0 10px ${color}` : "none",
            transition: "width 0.7s cubic-bezier(0.4, 0, 0.2, 1), background 0.4s ease",
            position: "relative",
            overflow: "hidden"
          }}
        >
          {/* Shimmer / shine reflection animation */}
          <div className="score-bar-shimmer" />
        </div>

        {/* Overlaid percentage text */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "0.68rem",
            fontFamily: "var(--font-mono)",
            fontWeight: 700,
            letterSpacing: "0.03em",
            color: "#ffffff",
            textShadow: "0 1px 3px rgba(0,0,0,0.9), 0 0 4px rgba(0,0,0,0.85)",
            pointerEvents: "none",
            zIndex: 2,
          }}
        >
          {pct}%
        </div>
      </div>
      <span
        style={{
          fontSize: "0.75rem",
          fontFamily: "var(--font-mono)",
          fontWeight: 700,
          color,
          minWidth: 36,
          textAlign: "right",
          textShadow: score > 0.6 ? `0 0 8px ${color}` : "none"
        }}
      >
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
