import { useState } from "react";
import { SimulateModal } from "../components/SimulateModal";
import { Zap, Info, Cpu, GitBranch, Sparkles, FileText, ArrowRight, Activity } from "lucide-react";
import { Card3D } from "../components/Card3D";
import { cyberAudio } from "../components/Cyber3DBackground";

export default function SimulatePage() {
  const [showModal, setShowModal] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState<{
    service?: string;
    fault_type?: string;
    severity?: string;
    duration_minutes?: number;
  } | undefined>(undefined);

  const scenarios = [
    {
      title: "Database Latency Spike",
      service: "database",
      type: "latency_spike",
      severity: "critical",
      desc: "Simulates a database slowdown. Cascades through auth, user, order services.",
      color: "#ef4444",
    },
    {
      title: "Payment Service Error Burst",
      service: "payment-service",
      type: "error_burst",
      severity: "high",
      desc: "High error rate in payment service — mimics API gateway or network failure.",
      color: "#f59e0b",
    },
    {
      title: "Cache Resource Exhaustion",
      service: "cache-service",
      type: "resource_exhaustion",
      severity: "medium",
      desc: "Memory/CPU exhaustion in cache — causes slowdown in auth and inventory.",
      color: "#06b6d4",
    },
    {
      title: "API Gateway Latency",
      service: "api-gateway",
      type: "latency_spike",
      severity: "high",
      desc: "All upstream services are affected since gateway is the entry point.",
      color: "#8b5cf6",
    },
  ];

  const handleLaunchScenario = (s: typeof scenarios[0]) => {
    cyberAudio.playClick();
    setSelectedScenario({
      service: s.service,
      fault_type: s.type,
      severity: s.severity,
      duration_minutes: 5,
    });
    setShowModal(true);
  };

  const handleCustomLaunch = () => {
    cyberAudio.playClick();
    setSelectedScenario(undefined);
    setShowModal(true);
  };

  return (
    <div style={{ padding: "84px 2rem 3rem", maxWidth: 960, margin: "0 auto", position: "relative", zIndex: 1 }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg, rgba(239,68,68,0.2), rgba(99,102,241,0.2))",
              border: "1px solid rgba(239,68,68,0.4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--danger)",
            }}
          >
            <Zap size={18} />
          </div>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
            Fault Simulation & AI Pipeline
          </h1>
        </div>
        <p style={{ color: "var(--text-muted)", fontSize: "0.88rem" }}>
          Inject synthetic microservice faults, trigger real-time spatio-temporal GNN anomaly detection,
          infer causal DAGs, and automatically generate verified executive incident reports.
        </p>
      </div>

      {/* 3D Interactive Pipeline Infographic Banner */}
      <Card3D
        style={{
          marginBottom: 32,
          padding: "20px 24px",
          background: "rgba(26, 31, 46, 0.8)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(99, 102, 241, 0.3)",
        }}
      >
        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 14 }}>
          Autonomous AIOps Pipeline Flow
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: 12,
            alignItems: "center",
          }}
        >
          {[
            { icon: Zap, label: "Fault Injection", sub: "Chaos Telemetry", color: "#ef4444" },
            { icon: Cpu, label: "VAE-GNN Anomaly", sub: "Graph Neural Net", color: "#6366f1" },
            { icon: GitBranch, label: "Causal Inference", sub: "DECI Discovery", color: "#06b6d4" },
            { icon: Sparkles, label: "LLM Reasoning", sub: "Multi-Agent RCA", color: "#a855f7" },
            { icon: FileText, label: "Report Production", sub: "PDF / MD / HTML", color: "#10b981" },
          ].map((stage, idx, arr) => {
            const Icon = stage.icon;
            return (
              <div
                key={stage.label}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  textAlign: "center",
                  padding: "12px 8px",
                  background: "rgba(15, 20, 25, 0.5)",
                  border: `1px solid ${stage.color}33`,
                  borderRadius: "10px",
                  position: "relative",
                }}
              >
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: `${stage.color}18`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: stage.color,
                    marginBottom: 8,
                  }}
                >
                  <Icon size={16} />
                </div>
                <div style={{ fontWeight: 700, fontSize: "0.78rem", color: "var(--text-primary)" }}>{stage.label}</div>
                <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginTop: 2 }}>{stage.sub}</div>
              </div>
            );
          })}
        </div>
      </Card3D>

      {/* Quick Scenarios with 3D perspective tilt */}
      <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: 14, letterSpacing: "0.04em", textTransform: "uppercase" }}>
        Instant Chaos Scenarios
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 28 }}>
        {scenarios.map((s) => (
          <Card3D
            key={s.title}
            onClick={() => handleLaunchScenario(s)}
            interactiveAudio
            style={{
              padding: "1.3rem",
              cursor: "pointer",
              textAlign: "left",
              border: `1px solid ${s.color}33`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Zap size={16} color={s.color} />
                <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--text-primary)" }}>{s.title}</span>
              </div>
              <ArrowRight size={14} color="var(--text-muted)" />
            </div>

            <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
              <span className={`badge badge-${s.severity === "critical" ? "critical" : s.severity === "high" ? "warning" : "healthy"}`}>
                {s.severity.toUpperCase()}
              </span>
              <span
                style={{
                  padding: "2px 8px",
                  borderRadius: 99,
                  fontSize: "0.68rem",
                  fontWeight: 600,
                  background: "var(--bg-elevated)",
                  color: "var(--text-muted)",
                }}
              >
                {s.type.replace(/_/g, " ")}
              </span>
              <span
                style={{
                  padding: "2px 8px",
                  borderRadius: 99,
                  fontSize: "0.68rem",
                  fontWeight: 600,
                  background: "rgba(99, 102, 241, 0.12)",
                  color: "var(--primary)",
                }}
              >
                {s.service}
              </span>
            </div>

            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: 1.5 }}>{s.desc}</p>
          </Card3D>
        ))}
      </div>

      {/* Custom Simulation */}
      <Card3D
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "18px 24px",
          background: "rgba(26, 31, 46, 0.85)",
          border: "1px solid rgba(6, 182, 212, 0.3)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: "rgba(6, 182, 212, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent-cyan)",
            }}
          >
            <Info size={18} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: "0.92rem", color: "var(--text-primary)" }}>
              Custom Synthetic Fault Architecture
            </div>
            <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              Select target microservices, customize duration, injection vectors, and severity thresholds
            </div>
          </div>
        </div>

        <button className="btn btn-primary" onClick={handleCustomLaunch} style={{ gap: 8, padding: "8px 18px" }}>
          <Zap size={15} /> Custom Simulation
        </button>
      </Card3D>

      {showModal && (
        <SimulateModal
          onClose={() => setShowModal(false)}
          initialConfig={selectedScenario}
        />
      )}
    </div>
  );
}
