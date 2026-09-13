import { useState } from "react";
import { motion } from "framer-motion";
import { SimulateModal } from "../components/SimulateModal";
import { Zap, Info, Database, CreditCard, HardDrive, Globe } from "lucide-react";

const SCENARIOS = [
  {
    title: "Database Latency Spike", service: "database", type: "latency_spike", severity: "critical",
    desc: "Simulates a database slowdown. Cascades through auth, user, order services.",
    icon: Database, color: "#ef4444",
  },
  {
    title: "Payment Service Error Burst", service: "payment-service", type: "error_burst", severity: "high",
    desc: "High error rate in payment service — mimics API gateway or network failure.",
    icon: CreditCard, color: "#f97316",
  },
  {
    title: "Cache Resource Exhaustion", service: "cache-service", type: "resource_exhaustion", severity: "medium",
    desc: "Memory/CPU exhaustion in cache — causes degradation in auth and inventory.",
    icon: HardDrive, color: "#f59e0b",
  },
  {
    title: "API Gateway Latency", service: "api-gateway", type: "latency_spike", severity: "high",
    desc: "All upstream services are affected since gateway is the entry point.",
    icon: Globe, color: "#f97316",
  },
];

export default function SimulatePage() {
  const [showModal, setShowModal] = useState(false);

  return (
    <div className="page-content" style={{ maxWidth: 900 }}>
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(139,92,246,0.15)",
            border: "1px solid rgba(139,92,246,0.3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Zap size={18} color="#8b5cf6" />
          </div>
          <h1 className="page-title">Fault Simulation</h1>
        </div>
        <p className="page-subtitle">Inject synthetic faults and watch the 8-stage SYNAPSE RCA pipeline execute in real time.</p>
      </motion.div>

      {/* Quick Scenarios */}
      <div className="section-title" style={{ marginBottom: 14 }}>Quick Scenarios</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 28 }}>
        {SCENARIOS.map((s, i) => (
          <motion.button
            key={s.title}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
            className="card card-glow"
            style={{
              textAlign: "left", cursor: "pointer",
              background: `linear-gradient(135deg, ${s.color}08 0%, ${s.color}04 100%)`,
              border: `1px solid ${s.color}25`,
              borderRadius: "var(--radius-lg)", padding: "1.3rem",
            }}
            onClick={() => setShowModal(true)}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ width: 34, height: 34, borderRadius: 9, background: `${s.color}18`,
                border: `1px solid ${s.color}30`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <s.icon size={16} color={s.color} />
              </div>
              <span style={{ fontWeight: 700, fontSize: "0.88rem", color: "var(--text-primary)" }}>{s.title}</span>
            </div>
            <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
              <span className={`badge badge-${s.severity === "critical" ? "critical" : s.severity === "high" ? "warning" : "degraded"}`}>
                {s.severity}
              </span>
              <span style={{ padding: "2px 8px", borderRadius: 99, fontSize: "0.67rem", fontWeight: 600,
                background: "var(--bg-elevated)", color: "var(--text-muted)" }}>
                {s.type.replace(/_/g, " ")}
              </span>
            </div>
            <p style={{ fontSize: "0.77rem", color: "var(--text-muted)", lineHeight: 1.55 }}>{s.desc}</p>
          </motion.button>
        ))}
      </div>

      {/* Custom */}
      <motion.div
        className="card"
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "rgba(59,130,246,0.05)", border: "1px solid rgba(59,130,246,0.2)" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Info size={18} color="var(--accent-blue)" />
          <span style={{ fontSize: "0.88rem", color: "var(--text-secondary)" }}>
            Configure a custom fault with any service, type, and severity
          </span>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Zap size={14} /> Custom Simulation
        </button>
      </motion.div>

      {showModal && <SimulateModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
