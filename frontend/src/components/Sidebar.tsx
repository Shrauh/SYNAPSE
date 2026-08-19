import { NavLink, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, GitBranch, AlertTriangle, Zap, Cpu,
  Activity, Search, Map, BookOpen, BarChart3, ChevronLeft,
  ChevronRight, Brain, TrendingUp, Server, Shield, Sun, Moon,
} from "lucide-react";
import { useStore } from "../store";

const NAV_SECTIONS = [
  {
    label: "Core",
    items: [
      { to: "/",          icon: LayoutDashboard, label: "Dashboard",          badge: null },
      { to: "/incidents", icon: AlertTriangle,   label: "Incident Feed",      badge: "live" },
      { to: "/graph",     icon: GitBranch,       label: "Causal Graph",       badge: null },
      { to: "/simulate",  icon: Zap,             label: "Fault Simulation",   badge: null },
      { to: "/model",     icon: Cpu,             label: "Model Status",       badge: null },
    ],
  },
  {
    label: "Analytics",
    items: [
      { to: "/incidents", icon: Brain,      label: "Root Cause Analysis", badge: null },
      { to: "/graph",     icon: Search,     label: "Anomaly Detection",   badge: null },
      { to: "/graph",     icon: TrendingUp, label: "Predictive Insights", badge: null },
      { to: "/model",     icon: BarChart3,  label: "Reports & Analytics", badge: null },
    ],
  },
  {
    label: "Infrastructure",
    items: [
      { to: "/graph",     icon: Map,      label: "Service Dependency",  badge: null },
      { to: "/model",     icon: Server,   label: "Cloud Infrastructure",badge: null },
      { to: "/incidents", icon: Shield,   label: "Runbook Repository",  badge: null },
      { to: "/model",     icon: Activity, label: "Metrics Dashboard",   badge: null },
    ],
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const wsConnected = useStore(s => s.wsConnected);
  const anomalyScores = useStore(s => s.anomalyScores);
  const navigate = useNavigate();

  const maxScore = Math.max(0, ...Object.values(anomalyScores));
  const criticalCount = Object.values(anomalyScores).filter(s => s > 0.8).length;
  const theme = useStore(s => s.theme);
  const toggleTheme = useStore(s => s.toggleTheme);

  return (
    <motion.div
      className={`sidebar${collapsed ? " collapsed" : ""}`}
      animate={{ width: collapsed ? 68 : 240 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
    >
      {/* Logo */}
      <div className="sidebar-logo" style={{ cursor: "pointer" }} onClick={() => navigate("/")}>
        <div className="sidebar-logo-icon">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="5"  r="2.5" fill="white" opacity="0.95"/>
            <circle cx="4"  cy="15" r="2"   fill="white" opacity="0.75"/>
            <circle cx="16" cy="15" r="2"   fill="white" opacity="0.75"/>
            <line x1="10" y1="7.5" x2="4"  y2="13" stroke="white" strokeWidth="1.2" opacity="0.5"/>
            <line x1="10" y1="7.5" x2="16" y2="13" stroke="white" strokeWidth="1.2" opacity="0.5"/>
            <line x1="4"  y1="15" x2="16"  y2="15" stroke="white" strokeWidth="1.2" opacity="0.3"/>
          </svg>
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
            >
              <div className="sidebar-logo-text">SYNAPSE</div>
              <span className="sidebar-logo-sub">AIOps Platform</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <AnimatePresence>
              {!collapsed && (
                <motion.div
                  className="sidebar-section-label"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                >
                  {section.label}
                </motion.div>
              )}
            </AnimatePresence>

            {section.items.map((item) => (
              <NavLink
                key={`${item.to}-${item.label}`}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => `sidebar-item${isActive ? " active" : ""}`}
                title={collapsed ? item.label : undefined}
              >
                <div className="sidebar-icon">
                  <item.icon size={16} />
                </div>
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      className="sidebar-label"
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -8 }}
                      transition={{ duration: 0.18 }}
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>

                {!collapsed && item.badge === "live" && criticalCount > 0 && (
                  <span className="sidebar-badge blink">{criticalCount}</span>
                )}
              </NavLink>
            ))}

            {!collapsed && <div style={{ height: 4 }} />}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        {/* WS Status */}
        <div className="sidebar-ws" title={wsConnected ? "WebSocket Connected" : "WebSocket Offline"}>
          <div
            className="sidebar-ws-dot blink"
            style={{
              background: wsConnected ? "var(--status-healthy)" : "var(--text-muted)",
              boxShadow: wsConnected ? "0 0 6px var(--status-healthy)" : "none",
              animation: wsConnected ? undefined : "none",
            }}
          />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                style={{ fontSize: "0.72rem", color: wsConnected ? "var(--status-healthy)" : "var(--text-muted)" }}
              >
                {wsConnected ? "Live Connected" : "Offline"}
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Theme Toggle */}
        <button className="theme-toggle" onClick={toggleTheme} title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"} style={{ width: "100%", justifyContent: collapsed ? "center" : "flex-start", marginBottom: 6 }}>
          {theme === "dark"
            ? <Sun size={14} color="#f59e0b" />
            : <Moon size={14} color="#4F46E5" />}
          <AnimatePresence>
            {!collapsed && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ fontSize: "0.72rem" }}>
                {theme === "dark" ? "Light Mode" : "Dark Mode"}
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Collapse toggle */}
        <button className="sidebar-collapse-btn" onClick={onToggle}>
          {collapsed ? <ChevronRight size={14} /> : (
            <>
              <ChevronLeft size={14} />
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ fontSize: "0.7rem" }}>
                Collapse
              </motion.span>
            </>
          )}
        </button>
      </div>
    </motion.div>
  );
}
