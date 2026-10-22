import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import ProfileMenu from "./ProfileMenu";
import { CyberControls } from "./Cyber3DBackground";


interface NavItem {
  path: string;
  label: string;
  icon: string;
  badge?: string;
}

interface NavGroup {
  group: string;
  icon: string;
  items: NavItem[];
}

const NAV: NavGroup[] = [
  {
    group: "Overview",
    icon: "⬡",
    items: [
      { path: "/", label: "Operations Dashboard", icon: "◈" },
      { path: "/graph", label: "Service Map", icon: "⬡" },
    ],
  },
  {
    group: "Observability",
    icon: "◉",
    items: [
      { path: "/incidents", label: "Incident Explorer", icon: "⚠" },
      { path: "/alerts", label: "Alerts", icon: "🔔" },
      { path: "/logs", label: "Logs", icon: "≡" },
    ],
  },
  {
    group: "Intelligence",
    icon: "⬣",
    items: [
      { path: "/simulate", label: "Fault Simulation", icon: "⚙" },
      { path: "/model", label: "Model Health", icon: "◎" },
      { path: "/evaluation", label: "Research Eval", icon: "∑" },
    ],
  },
  {
    group: "Recovery",
    icon: "↺",
    items: [
      { path: "/actions", label: "Suggested Actions", icon: "▷" },
      { path: "/approval-queue", label: "Approval Queue", icon: "✓" },
    ],
  },
  {
    group: "Platform",
    icon: "⚙",
    items: [
      { path: "/platform", label: "Platform Health", icon: "◉" },
      { path: "/audit", label: "Audit History", icon: "☰" },
      { path: "/notifications", label: "Notifications", icon: "◫" },
    ],
  },
];

const SEVERITY_COLORS: Record<string, string> = {
  healthy: "var(--success)",
  degraded: "var(--warning)",
  unhealthy: "var(--danger)",
  unavailable: "var(--text-muted)",
};

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const location = useLocation();

  const isActive = (path: string) =>
    path === "/" ? location.pathname === "/" : location.pathname.startsWith(path);

  return (
    <aside
      style={{
        width: collapsed ? "56px" : "220px",
        minHeight: "100vh",
        background: "var(--bg-card)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        transition: "width 0.2s ease",
        flexShrink: 0,
        position: "sticky",
        top: 0,
        height: "100vh",
        overflowY: "auto",
        overflowX: "hidden",
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: collapsed ? "16px 12px" : "20px 16px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          minHeight: "64px",
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: "linear-gradient(135deg, var(--primary), var(--secondary))",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 800,
            fontSize: "14px",
            color: "#fff",
            flexShrink: 0,
          }}
        >
          SY
        </div>
        {!collapsed && (
          <div>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--text-primary)", lineHeight: 1.2 }}>
              SYNAPSE
            </div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              AIOps Platform
            </div>
          </div>
        )}
      </div>

      {/* Nav groups */}
      <nav style={{ flex: 1, padding: "8px 0" }}>
        {NAV.map((group) => (
          <div key={group.group} style={{ marginBottom: "4px" }}>
            {!collapsed && (
              <div
                style={{
                  padding: "8px 16px 4px",
                  fontSize: "10px",
                  fontWeight: 600,
                  color: "var(--text-muted)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                {group.group}
              </div>
            )}
            {group.items.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                title={collapsed ? item.label : undefined}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: collapsed ? "10px 16px" : "8px 16px",
                  margin: "1px 8px",
                  borderRadius: "var(--radius-sm)",
                  textDecoration: "none",
                  fontSize: "13px",
                  fontWeight: isActive(item.path) ? 600 : 400,
                  color: isActive(item.path) ? "var(--text-primary)" : "var(--text-secondary)",
                  background: isActive(item.path) ? "var(--bg-elevated)" : "transparent",
                  borderLeft: isActive(item.path)
                    ? "2px solid var(--primary)"
                    : "2px solid transparent",
                  transition: "all 0.15s ease",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                }}
              >
                <span style={{ fontSize: "14px", flexShrink: 0 }}>{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            ))}
          </div>
        ))}
      </nav>

      {/* Toggle button */}
      <button
        onClick={onToggle}
        style={{
          background: "none",
          border: "none",
          borderTop: "1px solid var(--border)",
          padding: "12px",
          cursor: "pointer",
          color: "var(--text-muted)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "16px",
          transition: "color 0.15s",
          width: "100%",
        }}
      >
        {collapsed ? "→" : "←"}
      </button>
    </aside>
  );
}

export function TopBar() {
  const location = useLocation();
  const pageTitle = getPageTitle(location.pathname);

  return (
    <header
      style={{
        height: "56px",
        background: "var(--bg-card)",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        padding: "0 24px",
        gap: "16px",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      <h1 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", flex: 1 }}>
        {pageTitle}
      </h1>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <CyberControls />
        <StatusPill />
        <ProfileMenu />
      </div>
    </header>
  );
}

function StatusPill() {
  const [healthy, setHealthy] = React.useState<boolean | null>(null);
  React.useEffect(() => {
    fetch("/api/v1/health")
      .then(r => r.json())
      .then(d => setHealthy(d.status === "healthy"))
      .catch(() => setHealthy(true));
  }, []);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        padding: "4px 12px",
        borderRadius: 20,
        background: "rgba(16, 185, 129, 0.08)",
        border: "1px solid rgba(16, 185, 129, 0.25)",
        fontSize: "12px",
        fontWeight: 500,
        color: "var(--success)",
      }}
    >
      <div
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: "var(--success)",
          boxShadow: "0 0 8px rgba(16, 185, 129, 0.6)",
          animation: "pulse 2s infinite",
        }}
      />
      {healthy === null ? "Connecting…" : "System Online"}
    </div>
  );
}

function getPageTitle(path: string): string {
  if (path === "/") return "Operations Dashboard";
  if (path.startsWith("/incidents/") && path.includes("/actions")) return "Recovery Actions";
  if (path.startsWith("/incidents/")) return "Incident Investigation";
  if (path === "/incidents") return "Incident Explorer";
  if (path === "/graph") return "Service Map";
  if (path === "/simulate") return "Fault Simulation";
  if (path === "/model") return "Model Health";
  if (path === "/evaluation") return "Research Evaluation";
  if (path === "/alerts") return "Alerts";
  if (path === "/logs") return "Logs";
  if (path === "/actions") return "Suggested Actions";
  if (path === "/approval-queue") return "Approval Queue";
  if (path === "/platform") return "Platform Health";
  if (path === "/audit") return "Audit History";
  if (path === "/notifications") return "Notifications";
  return "SYNAPSE";
}
