import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, GitBranch, AlertTriangle, Cpu, Zap, Activity, Trophy,
  Bell, FileText, MessageSquare
} from "lucide-react";
import { useStore } from "../store";
import { useEffect, useState } from "react";
import { getActiveSystem } from "../api/endpoints";

const NAV = [
  { to: "/",         icon: LayoutDashboard, label: "Dashboard" },
  { to: "/graph",    icon: GitBranch,       label: "Service Graph" },
  { to: "/incidents",icon: AlertTriangle,   label: "Incidents" },
  { to: "/simulate", icon: Zap,             label: "Simulate" },
  { to: "/model",    icon: Cpu,             label: "Model Status" },
  { to: "/evaluation", icon: Trophy,        label: "Benchmark" },
  { to: "/alerts",   icon: Bell,            label: "Alerts" },
  { to: "/logs",     icon: FileText,        label: "Logs" },
  { to: "/notifications", icon: MessageSquare, label: "Notify" },
];

export function Navbar() {
  const loc = useLocation();
  const wsConnected = useStore((s) => s.wsConnected);
  const [activeSystem, setActiveSystem] = useState("Loading...");
  const [sysStatus, setSysStatus] = useState<"running" | "switching">("running");

  useEffect(() => {
    const fetchSys = () => {
      getActiveSystem().then(r => {
        setActiveSystem(r.active_system);
        setSysStatus("running");
      }).catch(() => {
        setSysStatus("switching");
      });
    };
    fetchSys();
    const iv = setInterval(fetchSys, 30000);
    return () => clearInterval(iv);
  }, []);

  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "0 1.5rem", height: "56px",
      background: "#050510", backdropFilter: "blur(16px)",
      borderBottom: "1px solid var(--border)",
    }}>
      {/* Logo */}
      <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 10 }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
        </svg>
        <span style={{ fontWeight: 800, fontSize: "1.2rem", letterSpacing: "1px", color: "var(--primary)", textShadow: "0 0 10px var(--primary-glow)" }}>
          SYNAPSE
        </span>
      </Link>

      {/* Nav links */}
      <div style={{ display: "flex", gap: 4 }}>
        {NAV.map(({ to, icon: Icon, label }) => {
          const active = loc.pathname === to;
          return (
            <Link key={to} to={to} style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "6px 14px", borderRadius: "8px",
              textDecoration: "none", fontSize: "0.82rem", fontWeight: 500,
              transition: "all 0.2s",
              background: active ? "var(--primary-glow)" : "transparent",
              color: active ? "var(--primary)" : "var(--text-muted)",
              border: active ? "1px solid var(--primary)" : "1px solid transparent",
              boxShadow: active ? "0 0 10px var(--primary-glow)" : "none",
            }}>
              <Icon size={14} />
              {label}
            </Link>
          );
        })}
      </div>

      {/* Status Indicators */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {/* System status */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.75rem", color: "var(--text-primary)", background: "var(--surface)", padding: "4px 12px", borderRadius: "20px", border: "1px solid var(--border)" }}>
          <div className={`status-dot ${sysStatus === "running" ? "green" : "yellow"}`} />
          {activeSystem}
        </div>

        {/* WS status */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.75rem", color: "var(--text-primary)", background: "var(--surface)", padding: "4px 12px", borderRadius: "20px", border: "1px solid var(--border)" }}>
          <div className={`status-dot ${wsConnected ? "blue" : "red"}`} />
          {wsConnected ? "Live" : "Offline"}
        </div>
      </div>
    </nav>
  );
}
