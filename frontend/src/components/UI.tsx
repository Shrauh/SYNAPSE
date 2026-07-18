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
      className="card card-glow"
      style={{ position: "relative", overflow: "hidden" }}
    >
      {/* Glow accent */}
      <div style={{
        position: "absolute", top: 0, right: 0,
        width: 80, height: 80, borderRadius: "50%",
        background: color, opacity: 0.07, filter: "blur(30px)",
      }} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <span style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>
          {title}
        </span>
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: `${color}18`, display: "flex", alignItems: "center", justifyContent: "center",
          color,
        }}>
          {icon}
        </div>
      </div>
      <div style={{ fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{sub}</div>}
    </motion.div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export function ScoreBar({ score }: { score: number }) {
  const color = score > 0.8 ? "var(--status-critical)"
    : score > 0.6 ? "var(--status-warning)"
    : score > 0.4 ? "var(--status-degraded)"
    : "var(--status-healthy)";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div className="score-bar" style={{ flex: 1 }}>
        <div className="score-bar-fill" style={{ width: `${score * 100}%`, background: color }} />
      </div>
      <span style={{ fontSize: "0.75rem", fontFamily: "JetBrains Mono", color, minWidth: 36 }}>
        {score.toFixed(2)}
      </span>
    </div>
  );
}

export function Spinner() {
  return <div className="spinner" />;
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <div className="section-title">{children}</div>;
}
