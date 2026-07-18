import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, GitFork, AlertTriangle, Cpu, Zap, Activity
} from "lucide-react";
import { useStore } from "../store";

const NAV = [
  { to: "/",         icon: LayoutDashboard, label: "Dashboard" },
  { to: "/graph",    icon: GitFork,         label: "Service Graph" },
  { to: "/incidents",icon: AlertTriangle,   label: "Incidents" },
  { to: "/simulate", icon: Zap,             label: "Simulate" },
  { to: "/model",    icon: Cpu,             label: "Model Status" },
];

export function Navbar() {
  const loc = useLocation();
  const wsConnected = useStore((s) => s.wsConnected);

  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "0 1.5rem", height: "56px",
      background: "rgba(7,11,20,0.85)", backdropFilter: "blur(16px)",
      borderBottom: "1px solid var(--border)",
    }}>
      {/* Logo */}
      <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: "linear-gradient(135deg,#3b82f6,#8b5cf6)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Activity size={18} color="#fff" />
        </div>
        <span style={{ fontWeight: 800, fontSize: "1.05rem", letterSpacing: "-0.01em" }}>
          <span className="gradient-text">SYNAPSE</span>
        </span>
        <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginLeft: 2, fontWeight: 600 }}>
          AIOps
        </span>
      </Link>

      {/* Nav links */}
      <div style={{ display: "flex", gap: 4 }}>
        {NAV.map(({ to, icon: Icon, label }) => {
          const active = loc.pathname === to;
          return (
            <Link key={to} to={to} style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "6px 14px", borderRadius: "var(--radius-md)",
              textDecoration: "none", fontSize: "0.82rem", fontWeight: 500,
              transition: "all 0.15s",
              background: active ? "var(--accent-glow)" : "transparent",
              color: active ? "var(--accent-blue)" : "var(--text-secondary)",
              border: active ? "1px solid rgba(59,130,246,0.3)" : "1px solid transparent",
            }}>
              <Icon size={14} />
              {label}
            </Link>
          );
        })}
      </div>

      {/* WS status */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.75rem", color: "var(--text-muted)" }}>
        <div style={{
          width: 7, height: 7, borderRadius: "50%",
          background: wsConnected ? "var(--status-healthy)" : "var(--text-muted)",
          boxShadow: wsConnected ? "0 0 6px var(--status-healthy)" : "none",
        }} />
        {wsConnected ? "Live" : "Offline"}
      </div>
    </nav>
  );
}
