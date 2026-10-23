import React, { useState, useEffect } from "react";
import { fetchPlatformHealth, type PlatformHealth } from "../api/endpoints";

const STATUS_CONFIG: Record<string, { color: string; icon: string; label: string }> = {
  healthy: { color: "var(--success)", icon: "✓", label: "Healthy" },
  degraded: { color: "var(--warning)", icon: "⚠", label: "Degraded" },
  unhealthy: { color: "var(--danger)", icon: "✗", label: "Unhealthy" },
  unavailable: { color: "var(--text-muted)", icon: "○", label: "Unavailable" },
  unknown: { color: "var(--text-muted)", icon: "?", label: "Unknown" },
  initializing: { color: "var(--accent-cyan)", icon: "◎", label: "Initializing" },
};

const COMPONENT_INFO: Record<string, { label: string; description: string; icon: string }> = {
  database: { label: "Database", description: "SQLite async storage for incidents, actions, and audit events", icon: "🗄" },
  prometheus: { label: "Prometheus", description: "Metrics collection and alerting", icon: "📊" },
  ai_pipeline: { label: "AI Pipeline", description: "VAE-GNN anomaly detection + causal inference", icon: "🧠" },
  llm: { label: "LLM Reasoner", description: "Language model for root-cause explanation", icon: "💬" },
  telemetry_ingestion: { label: "Telemetry Ingestion", description: "Metric ingestion pipeline", icon: "📡" },
};

export default function PlatformHealthPage() {
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const h = await fetchPlatformHealth();
      setHealth(h);
      setLastChecked(new Date());
    } catch (e: any) {
      setError(e?.message || "Failed to fetch platform health");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000); // Auto-refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const overallConfig = health ? STATUS_CONFIG[health.overall] || STATUS_CONFIG.unknown : STATUS_CONFIG.unknown;

  return (
    <div style={{ padding: "24px", maxWidth: 960, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
            Platform Health
          </h1>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Real-time SYNAPSE component status — actual checks, not config presence
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-bright)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-secondary)",
            padding: "8px 14px",
            fontSize: "13px",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Checking…" : "↺ Refresh"}
        </button>
      </div>

      {error && (
        <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "var(--radius-md)", padding: "12px 16px", color: "var(--danger)", fontSize: "13px", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {health && (
        <>
          {/* Overall status banner */}
          <div
            style={{
              background: `${overallConfig.color}11`,
              border: `1px solid ${overallConfig.color}44`,
              borderRadius: "var(--radius-md)",
              padding: "20px 24px",
              display: "flex",
              alignItems: "center",
              gap: "16px",
              marginBottom: "24px",
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                background: `${overallConfig.color}22`,
                border: `2px solid ${overallConfig.color}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "20px",
                color: overallConfig.color,
                flexShrink: 0,
              }}
            >
              {overallConfig.icon}
            </div>
            <div>
              <div style={{ fontSize: "18px", fontWeight: 700, color: overallConfig.color }}>
                System {overallConfig.label}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                Last checked: {lastChecked ? lastChecked.toLocaleTimeString() : "N/A"}
                {" · "}Checked at: {new Date(health.checked_at).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Component grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "12px" }}>
            {Object.entries(health.components).map(([key, comp]) => {
              const cfg = STATUS_CONFIG[comp.status] || STATUS_CONFIG.unknown;
              const info = COMPONENT_INFO[key] || { label: key, description: "", icon: "⚙" };
              return (
                <ComponentCard
                  key={key}
                  info={info}
                  comp={comp}
                  cfg={cfg}
                />
              );
            })}
          </div>

          {/* Info note */}
          <div style={{ marginTop: "24px", padding: "12px 16px", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", fontSize: "12px", color: "var(--text-muted)" }}>
            <strong style={{ color: "var(--text-secondary)" }}>Note:</strong>{" "}
            These checks are performed live at request time. A component labeled healthy has passed its actual health check, not merely its configuration check.
            Diagnostics are read-only and do not modify any system state.
          </div>
        </>
      )}

      {loading && !health && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "12px" }}>
          {[1, 2, 3, 4, 5].map(i => (
            <div
              key={i}
              style={{
                height: 120,
                background: "var(--bg-card)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                animation: "pulse 1.5s ease-in-out infinite",
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ComponentCard({ info, comp, cfg }: {
  info: { label: string; description: string; icon: string };
  comp: { status: string; detail?: string; [key: string]: any };
  cfg: { color: string; icon: string; label: string };
}) {
  const extras = Object.entries(comp).filter(([k]) => !["status", "detail"].includes(k));

  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: `1px solid ${cfg.color}33`,
        borderRadius: "var(--radius-md)",
        padding: "16px",
        transition: "border-color 0.2s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", marginBottom: "10px" }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "var(--radius-sm)",
            background: "var(--bg-elevated)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "18px",
            flexShrink: 0,
          }}
        >
          {info.icon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "2px" }}>
            {info.label}
          </div>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "11px",
              color: cfg.color,
              fontWeight: 600,
            }}
          >
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: cfg.color }} />
            {cfg.label}
          </div>
        </div>
      </div>

      {info.description && (
        <p style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "8px", lineHeight: 1.5 }}>
          {info.description}
        </p>
      )}

      {comp.detail && (
        <p style={{ fontSize: "11px", color: comp.status === "healthy" ? "var(--text-muted)" : "var(--warning)", fontFamily: "var(--font-mono)" }}>
          {comp.detail}
        </p>
      )}

      {extras.length > 0 && (
        <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "3px" }}>
          {extras.map(([k, v]) => (
            <div key={k} style={{ display: "flex", gap: "8px", fontSize: "11px" }}>
              <span style={{ color: "var(--text-muted)", minWidth: 80 }}>{k.replace(/_/g, " ")}</span>
              <span style={{ color: "var(--text-secondary)", fontFamily: typeof v === "string" && v.length > 20 ? "var(--font-mono)" : undefined }}>
                {String(v)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
