import { useState } from "react";
import { SimulateModal } from "../components/SimulateModal";
import { Zap, Info } from "lucide-react";

export default function SimulatePage() {
  const [showModal, setShowModal] = useState(false);

  const scenarios = [
    { title: "Database Latency Spike", service: "database", type: "latency_spike", severity: "critical",
      desc: "Simulates a database slowdown. Cascades through auth, user, order services." },
    { title: "Payment Service Error Burst", service: "payment-service", type: "error_burst", severity: "high",
      desc: "High error rate in payment service — mimics API gateway or network failure." },
    { title: "Cache Resource Exhaustion", service: "cache-service", type: "resource_exhaustion", severity: "medium",
      desc: "Memory/CPU exhaustion in cache — causes degradation in auth and inventory." },
    { title: "API Gateway Latency", service: "api-gateway", type: "latency_spike", severity: "high",
      desc: "All upstream services are affected since gateway is the entry point." },
  ];

  return (
    <div style={{ padding: "84px 2rem 3rem", maxWidth: 860, margin: "0 auto" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em" }}>Fault Simulation</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 4 }}>
          Inject a synthetic fault into the microservice topology and run the full RCA pipeline
        </p>
      </div>

      {/* Quick Scenarios */}
      <div className="section-title">Quick Scenarios</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 28 }}>
        {scenarios.map((s) => (
          <button key={s.title} className="card card-glow"
            style={{ textAlign: "left", cursor: "pointer", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: "1.2rem" }}
            onClick={() => setShowModal(true)}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <Zap size={14} color="var(--status-critical)" />
              <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>{s.title}</span>
            </div>
            <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
              <span className={`badge badge-${s.severity === "critical" ? "critical" : s.severity === "high" ? "warning" : "degraded"}`}>{s.severity}</span>
              <span style={{ padding: "2px 8px", borderRadius: 99, fontSize: "0.68rem", fontWeight: 600,
                background: "var(--bg-elevated)", color: "var(--text-muted)" }}>{s.type.replace(/_/g," ")}</span>
            </div>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.5 }}>{s.desc}</p>
          </button>
        ))}
      </div>

      {/* Custom */}
      <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Info size={16} color="var(--accent-blue)" />
          <span style={{ fontSize: "0.88rem", color: "var(--text-secondary)" }}>
            Configure a custom fault with any service, type, and severity
          </span>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Zap size={14} /> Custom Simulation
        </button>
      </div>

      {showModal && <SimulateModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
