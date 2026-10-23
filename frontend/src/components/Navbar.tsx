import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, GitBranch, AlertTriangle, Cpu, Zap,
  Bell, FileText, MessageSquare
} from "lucide-react";
import { useStore } from "../store";
import { useEffect, useState } from "react";
import { getActiveSystem, type ActiveSystemResponse } from "../api/endpoints";

const NAV = [
  { to: "/",         icon: LayoutDashboard, label: "Dashboard" },
  { to: "/graph",    icon: GitBranch,       label: "Service Graph" },
  { to: "/incidents",icon: AlertTriangle,   label: "Incidents" },
  { to: "/simulate", icon: Zap,             label: "Simulate" },
  { to: "/model",    icon: Cpu,             label: "Model Status" },
  // { to: "/evaluation", icon: Trophy,        label: "Benchmark" },
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
      getActiveSystem().then((r: ActiveSystemResponse) => {
        setActiveSystem(r.system);
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
      background: "rgba(255, 255, 255, 0.75)", backdropFilter: "blur(16px)",
      WebkitBackdropFilter: "blur(16px)",
      borderBottom: "1px solid rgba(148, 163, 184, 0.2)", boxShadow: "0 2px 16px rgba(0,0,0,0.04)",
    }}>
      {/* Logo */}
      <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 10 }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
        </svg>
        <span style={{ fontWeight: 800, fontSize: "1.2rem", letterSpacing: "1px", color: "var(--primary)" }}>
          SYNAPSE
        </span>
      </Link>

      {/* Nav links */}
      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
        {NAV.map(({ to, icon: Icon, label }) => {
          const active = loc.pathname === to;
          return (
            <Link key={to} to={to} style={{
              position: "relative",
              display: "flex", alignItems: "center", gap: 6,
              padding: "7px 13px", borderRadius: "8px",
              textDecoration: "none", fontSize: "0.82rem",
              fontWeight: active ? 600 : 500,
              transition: "all 0.2s ease",
              background: active ? "rgba(99, 102, 241, 0.12)" : "transparent",
              color: active ? "#1e293b" : "var(--text-secondary)",
              border: active ? "1px solid var(--border-bright)" : "1px solid transparent",
              boxShadow: active ? "0 0 8px rgba(99, 102, 241, 0.15)" : "none",
            }}>
              <Icon size={14} color={active ? "var(--primary)" : "currentColor"} />
              <span>{label}</span>
              {active && (
                <span style={{
                  position: "absolute", bottom: "-1px", left: "15%", right: "15%",
                  height: "2px", background: "var(--primary)", borderRadius: "2px",
                  boxShadow: "0 0 8px var(--primary)"
                }} />
              )}
            </Link>
          );
        })}
      </div>

      {/* Status Indicators */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* System status */}
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          fontSize: "0.75rem", color: "var(--text-primary)",
          background: "rgba(255, 255, 255, 0.7)", padding: "5px 12px",
          borderRadius: "20px", border: "1px solid var(--border-bright)",
          boxShadow: "0 2px 8px rgba(0,0,0,0.06)"
        }}>
          <div className={`status-dot ${sysStatus === "running" ? "green" : "yellow"}`} />
          <span style={{ color: "var(--text-muted)", fontSize: "0.7rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>System</span>
          <span style={{ fontWeight: 600 }}>{activeSystem}</span>
        </div>

        {/* WS status */}
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          fontSize: "0.75rem", color: "var(--text-primary)",
          background: "rgba(255, 255, 255, 0.7)", padding: "5px 12px",
          borderRadius: "20px", border: "1px solid var(--border-bright)",
          boxShadow: "0 2px 8px rgba(0,0,0,0.06)"
        }}>
          <div className={`status-dot ${wsConnected ? "blue" : "red"}`} />
          <span style={{ fontWeight: 600 }}>{wsConnected ? "Live" : "Offline"}</span>
        </div>
      </div>
    </nav>
  );
}
