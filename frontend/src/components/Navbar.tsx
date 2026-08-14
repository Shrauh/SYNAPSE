import { NavLink, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, GitBranch, AlertTriangle,
  Zap, Cpu, ChevronRight, Menu, X, Moon, Sun
} from "lucide-react";
import { useState } from "react";
import { useStore } from "../store";
import { ConnectionStatus } from "./UI";

const NAV_ITEMS = [
  { to: "/",          label: "Dashboard",   Icon: LayoutDashboard },
  { to: "/graph",     label: "Graph",       Icon: GitBranch },
  { to: "/incidents", label: "Incidents",   Icon: AlertTriangle },
  { to: "/simulate",  label: "Simulate",    Icon: Zap },
  { to: "/model",     label: "Model",       Icon: Cpu },
];

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const anomalyScores = useStore(s => s.anomalyScores);
  const theme = useStore(s => s.theme);
  const toggleTheme = useStore(s => s.toggleTheme);
  const navigate = useNavigate();

  const maxScore = Math.max(0, ...Object.values(anomalyScores));
  const hasAlert = maxScore > 0.6;

  return (
    <>
      <nav className="synapse-nav glass">
        {/* Brand */}
        <button
          onClick={() => navigate("/")}
          style={{
            display: "flex", alignItems: "center", gap: 10,
            background: "none", border: "none", cursor: "pointer", padding: 0,
          }}
        >
          {/* Logo Mark */}
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 0 16px rgba(99,102,241,0.4)",
            flexShrink: 0,
          }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="4" r="2" fill="white" opacity="0.9"/>
              <circle cx="3" cy="12" r="2" fill="white" opacity="0.7"/>
              <circle cx="13" cy="12" r="2" fill="white" opacity="0.7"/>
              <line x1="8" y1="6" x2="3" y2="10" stroke="white" strokeWidth="1.2" opacity="0.5"/>
              <line x1="8" y1="6" x2="13" y2="10" stroke="white" strokeWidth="1.2" opacity="0.5"/>
              <line x1="3" y1="12" x2="13" y2="12" stroke="white" strokeWidth="1.2" opacity="0.3"/>
            </svg>
          </div>
          <span style={{
            fontSize: "1rem", fontWeight: 800, letterSpacing: "0.08em",
            background: "linear-gradient(135deg, #a5b4fc, #e0e7ff)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
          }}>
            SYNAPSE
          </span>
        </button>

        {/* Desktop Nav */}
        <div style={{ display: "flex", alignItems: "center", gap: 2, flex: 1, justifyContent: "center" }}
          className="desktop-nav">
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} end={to === "/"} style={{ textDecoration: "none" }}>
              {({ isActive }) => (
                <motion.div
                  style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "6px 14px", borderRadius: 8,
                    fontSize: "0.82rem", fontWeight: isActive ? 600 : 500,
                    color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                    background: isActive ? "rgba(99,102,241,0.12)" : "transparent",
                    border: isActive ? "1px solid rgba(99,102,241,0.25)" : "1px solid transparent",
                    cursor: "pointer",
                    transition: "all 0.18s ease",
                    position: "relative",
                  }}
                  whileHover={{ color: "var(--text-primary)", background: "rgba(255,255,255,0.04)" }}
                >
                  <Icon size={14} />
                  {label}
                  {label === "Incidents" && hasAlert && (
                    <span style={{
                      position: "absolute", top: 4, right: 4,
                      width: 6, height: 6, borderRadius: "50%",
                      background: "var(--status-critical)",
                      boxShadow: "0 0 6px rgba(239,68,68,0.8)",
                    }} className="blink" />
                  )}
                </motion.div>
              )}
            </NavLink>
          ))}
        </div>

        {/* Right: Status + Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <ConnectionStatus />

          {/* Alert indicator */}
          {hasAlert && (
            <motion.div
              initial={{ scale: 0 }} animate={{ scale: 1 }}
              style={{
                display: "flex", alignItems: "center", gap: 5,
                padding: "4px 10px", borderRadius: 99,
                background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                fontSize: "0.7rem", fontWeight: 700, color: "#f87171",
                cursor: "pointer",
              }}
              onClick={() => navigate("/incidents")}
            >
              <AlertTriangle size={11} />
              ALERT
            </motion.div>
          )}

          {/* Quick Simulate */}
          <button
            className="btn btn-sm"
            onClick={() => navigate("/simulate")}
            style={{
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#fff", border: "none", fontSize: "0.75rem",
            }}
          >
            <Zap size={12} /> Simulate
          </button>

          {/* Theme Toggle */}
          <motion.button
            whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.94 }}
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            style={{
              width: 32, height: 32, borderRadius: 8,
              background: theme === "light" ? "rgba(79,70,229,0.1)" : "rgba(255,255,255,0.06)",
              border: `1px solid ${theme === "light" ? "rgba(79,70,229,0.25)" : "rgba(255,255,255,0.1)"}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: "pointer", color: "var(--text-muted)", flexShrink: 0,
            }}
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.div key={theme}
                initial={{ rotate: -30, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 30, opacity: 0 }} transition={{ duration: 0.18 }}>
                {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
              </motion.div>
            </AnimatePresence>
          </motion.button>

          {/* Mobile Toggle */}
          <button
            onClick={() => setMobileOpen(v => !v)}
            style={{ background: "none", border: "none", cursor: "pointer",
              color: "var(--text-muted)", display: "none" }}
            className="mobile-menu-btn"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            style={{
              position: "fixed", top: 58, left: 0, right: 0, z: 999,
              background: "rgba(4,4,15,0.95)", backdropFilter: "blur(20px)",
              borderBottom: "1px solid var(--border)",
              padding: "1rem 1.75rem", zIndex: 999,
            }}
          >
            {NAV_ITEMS.map(({ to, label, Icon }) => (
              <NavLink key={to} to={to} onClick={() => setMobileOpen(false)}
                style={{ textDecoration: "none", display: "block" }}>
                {({ isActive }) => (
                  <div style={{
                    display: "flex", alignItems: "center", gap: 10, justifyContent: "space-between",
                    padding: "0.75rem 0", borderBottom: "1px solid var(--border)",
                    color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                    fontWeight: isActive ? 600 : 400, fontSize: "0.9rem",
                  }}>
                    <div style={{ display: "flex", gap: 10 }}><Icon size={16} />{label}</div>
                    <ChevronRight size={14} />
                  </div>
                )}
              </NavLink>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        @media (max-width: 768px) {
          .desktop-nav { display: none !important; }
          .mobile-menu-btn { display: flex !important; }
        }
      `}</style>
    </>
  );
}
