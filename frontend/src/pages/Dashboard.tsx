import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { AlertTriangle, Activity, Clock, Cpu, ArrowRight, Server } from "lucide-react";
import { fetchHealth, fetchMetrics, fetchIncidents, getActiveSystem, switchSystem } from "../api/endpoints";
import type { HealthResponse, MetricsResponse, IncidentSummary } from "../types/api";
import { StatCard, StatusBadge, Spinner } from "../components/UI";
import { useStore } from "../store";
import { format } from "date-fns";

const SYSTEMS = ["Online Boutique", "FinTech", "HealthCare", "Default"];

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [activeSystem, setActiveSystem] = useState<string>("Default");
  const [switching, setSwitching] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const anomalyScores = useStore(s => s.anomalyScores || {});

  useEffect(() => {
    Promise.all([
      fetchHealth().catch(() => null),
      fetchMetrics().catch(() => null),
      fetchIncidents(1).catch(() => ({ incidents: [], total: 0, page: 1, per_page: 20 })),
      getActiveSystem().catch(() => ({ active_system: "Default" })),
    ])
      .then(([h, m, i, sys]) => {
        if (h) setHealth(h);
        if (m) setMetrics(m);
        if (i && Array.isArray(i.incidents)) {
          setIncidents(i.incidents.slice(0, 6));
        }
        if (sys && sys.active_system) {
          setActiveSystem(sys.active_system);
        }
      })
      .catch((err) => console.error("Dashboard load error:", err))
      .finally(() => setLoading(false));

    const iv = setInterval(() => {
      fetchMetrics().then(m => m && setMetrics(m)).catch(() => {});
      fetchIncidents(1).then(i => {
        if (i && Array.isArray(i.incidents)) {
          setIncidents(i.incidents.slice(0, 6));
        }
      }).catch(() => {});
    }, 10000);
    return () => clearInterval(iv);
  }, []);

  const handleSystemSwitch = async (sys: string) => {
    if (sys === activeSystem) return;
    setSwitching(true);
    try {
      await switchSystem(sys);
      setActiveSystem(sys);
      setToast(`Now monitoring: ${sys}`);
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      console.error(err);
      setToast(`Failed to switch to ${sys}`);
      setTimeout(() => setToast(null), 3000);
    } finally {
      setSwitching(false);
    }
  };

  // Top anomalous services from WebSocket
  const topServices = Object.entries(anomalyScores || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div style={{ padding: "84px 2rem 2rem", position: "relative" }}>
      {toast && (
        <div style={{ position: "fixed", top: 80, right: 24, zIndex: 1000, background: "var(--status-healthy)", color: "#fff", padding: "8px 16px", borderRadius: 8, fontSize: "0.85rem", fontWeight: 600, boxShadow: "0 4px 12px rgba(0,0,0,0.15)" }}>
          {toast}
        </div>
      )}
      {/* Header and System Switcher */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
        style={{ marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
            Operations Dashboard
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 4 }}>
            Real-time AIOps monitoring · {health?.version ?? "v1.0.0"}
          </p>
        </div>
        
        <div className="card glass" style={{ padding: "0.75rem 1rem", display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Server size={14} color="var(--accent-blue)" />
            <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-secondary)" }}>System:</span>
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            {SYSTEMS.map(sys => (
              <button
                key={sys}
                onClick={() => handleSystemSwitch(sys)}
                disabled={switching}
                className="btn btn-ghost"
                style={{
                  padding: "4px 10px",
                  fontSize: "0.75rem",
                  background: activeSystem === sys ? "var(--accent-glow)" : "transparent",
                  borderColor: activeSystem === sys ? "rgba(59,130,246,0.3)" : "transparent",
                  color: activeSystem === sys ? "var(--accent-blue)" : "var(--text-muted)",
                }}
              >
                {sys}
              </button>
            ))}
          </div>
        </div>
      </motion.div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}><Spinner /></div>
      ) : (
        <>
          {/* Stat Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 24 }}>
            <StatCard title="Total Incidents" value={metrics?.total_incidents ?? 0}
              icon={<AlertTriangle size={16} />} sub="All time" />
            <StatCard title="Active Analysis" value={metrics?.active_incidents ?? 0}
              icon={<Activity size={16} />} color="var(--accent-purple)" sub="Currently analyzing" />
            <StatCard title="Avg RCA Time" value={`${Number(metrics?.avg_resolution_time_sec ?? 0).toFixed(1)}s`}
              icon={<Clock size={16} />} color="var(--accent-cyan)" sub="Pipeline execution" />
            <StatCard title="Services Monitored" value={10}
              icon={<Cpu size={16} />} color="var(--status-healthy)" sub="10-service topology" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 20, marginBottom: 24 }}>
            {/* Recent Incidents */}
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <span className="section-title" style={{ marginBottom: 0 }}>Recent Incidents</span>
                <Link to="/incidents" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.78rem", color: "var(--accent-blue)", textDecoration: "none" }}>
                  View All <ArrowRight size={13} />
                </Link>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Title</th><th>Status</th><th>Root Cause</th><th>Confidence</th><th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {!incidents || incidents.length === 0 ? (
                      <tr><td colSpan={5} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                        No incidents yet — try simulating a fault!
                      </td></tr>
                    ) : incidents.map(inc => (
                      <tr key={inc.id} onClick={() => window.location.href = `/incidents/${inc.id}`} style={{ cursor: "pointer" }}>
                        <td style={{ color: "var(--text-primary)", fontWeight: 500 }}>{inc.title}</td>
                        <td><StatusBadge status={inc.status} /></td>
                        <td style={{ fontFamily: "JetBrains Mono", fontSize: "0.78rem" }}>
                          {inc.root_cause_service ?? <span style={{ color: "var(--text-muted)" }}>analyzing...</span>}
                        </td>
                        <td style={{ color: "var(--accent-blue)", fontWeight: 600 }}>
                          {inc.confidence != null ? `${(inc.confidence * 100).toFixed(0)}%` : "—"}
                        </td>
                        <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          {inc.detected_at ? format(new Date(inc.detected_at), "HH:mm:ss") : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Live Anomalies Side Card */}
            <div className="card">
              <div className="section-title" style={{ marginBottom: 14 }}>Live Telemetry</div>
              {topServices.length === 0 ? (
                <div style={{ color: "var(--text-muted)", fontSize: "0.8rem", textAlign: "center", padding: "1.5rem" }}>
                  All services nominal
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {topServices.map(([svc, score]) => (
                    <div key={svc} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem" }}>
                      <span style={{ color: "var(--text-secondary)" }}>{svc}</span>
                      <span style={{ fontWeight: 700, color: score > 0.6 ? "var(--status-critical)" : "var(--status-healthy)" }}>
                        {(score * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
