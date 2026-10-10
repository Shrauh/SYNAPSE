import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Bell, Copy, CheckCircle, AlertTriangle, Send } from "lucide-react";
import { getAlertStatus, testAlert, fetchIncidents } from "../api/endpoints";
import { Spinner, StatusBadge } from "../components/UI";
import type { IncidentSummary } from "../types/api";

export default function AlertsPage() {
  const [copied, setCopied] = useState(false);
  const [activeAlerts, setActiveAlerts] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [service, setService] = useState("payment-service");
  const [faultType, setFaultType] = useState("latency_spike");
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    Promise.all([
      getAlertStatus().catch(() => []),
      fetchIncidents(1).catch(() => ({ incidents: [] }))
    ]).then(([alerts, incData]) => {
      if (Array.isArray(alerts)) {
        setActiveAlerts(alerts);
      } else if (alerts && Array.isArray(alerts.alerts)) {
        setActiveAlerts(alerts.alerts);
      }
      if (incData && Array.isArray(incData.incidents)) {
        setIncidents(incData.incidents.filter((i: IncidentSummary) => i.title.startsWith("[AUTO]")));
      }
      setLoading(false);
    });
  }, []);

  const handleCopy = () => {
    navigator.clipboard.writeText(window.location.origin + "/api/v1/alerts/webhook");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTestAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    setTesting(true);
    try {
      await testAlert({ service, fault_type: faultType });
      // Refresh
      const alerts = await getAlertStatus().catch(() => []);
      if (Array.isArray(alerts)) setActiveAlerts(alerts);
      else if (alerts && Array.isArray(alerts.alerts)) setActiveAlerts(alerts.alerts);
    } catch (err) {
      console.error(err);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div style={{ padding: "84px 2rem 2rem" }}>
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 800 }}>Alert Management</h1>
        <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Configure and test alert webhooks</p>
      </motion.div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        {/* Webhook Status Card */}
        <div className="card glass">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <Bell size={18} color="var(--accent-blue)" />
            <h2 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Webhook Endpoint</h2>
          </div>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 12 }}>
            Configure Prometheus or Alertmanager to send POST requests to this URL:
          </p>
          <div style={{ display: "flex", gap: 8 }}>
            <input 
              readOnly 
              value={`${window.location.origin}/api/v1/alerts/webhook`}
              style={{ flex: 1, padding: "8px 12px", background: "rgba(0,0,0,0.2)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)" }}
            />
            <button onClick={handleCopy} className="btn btn-ghost" style={{ padding: "8px 12px" }}>
              {copied ? <CheckCircle size={16} color="var(--status-healthy)" /> : <Copy size={16} />}
            </button>
          </div>
        </div>

        {/* Test Alert Panel */}
        <div className="card glass">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <Send size={18} color="var(--accent-purple)" />
            <h2 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Test Alert</h2>
          </div>
          <form onSubmit={handleTestAlert} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4, display: "block" }}>Service</label>
                <select value={service} onChange={e => setService(e.target.value)} style={{ width: "100%", padding: "8px", background: "rgba(0,0,0,0.2)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)" }}>
                  <option value="payment-service">payment-service</option>
                  <option value="order-service">order-service</option>
                  <option value="auth-service">auth-service</option>
                  <option value="inventory-service">inventory-service</option>
                  <option value="database">database</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4, display: "block" }}>Fault Type</label>
                <select value={faultType} onChange={e => setFaultType(e.target.value)} style={{ width: "100%", padding: "8px", background: "rgba(0,0,0,0.2)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)" }}>
                  <option value="latency_spike">latency_spike</option>
                  <option value="error_spike">error_spike</option>
                  <option value="cpu_overload">cpu_overload</option>
                  <option value="memory_leak">memory_leak</option>
                </select>
              </div>
            </div>
            <button type="submit" disabled={testing} className="btn" style={{ background: "var(--accent-blue)", color: "#fff", padding: "8px", borderRadius: 6, fontWeight: 600 }}>
              {testing ? "Sending..." : "Send Test Alert"}
            </button>
          </form>
        </div>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}><Spinner /></div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* Active Alerts Table */}
          <div className="card glass">
            <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 16 }}>Active Alerts</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Alert Name</th>
                    <th>Service</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {activeAlerts.length === 0 ? (
                    <tr><td colSpan={3} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>No active alerts</td></tr>
                  ) : activeAlerts.map((alt, i) => (
                    <tr key={i}>
                      <td>{alt.alert_name || alt.name || "Unknown"}</td>
                      <td>{alt.service || "N/A"}</td>
                      <td><StatusBadge status={alt.status || "firing"} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Auto-Triggered Incidents */}
          <div className="card glass">
            <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 16 }}>Recent Auto-Triggered Incidents</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.length === 0 ? (
                    <tr><td colSpan={3} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>No auto-triggered incidents</td></tr>
                  ) : incidents.map(inc => (
                    <tr key={inc.id}>
                      <td style={{ color: "var(--text-primary)", fontWeight: 500 }}>{inc.title}</td>
                      <td><StatusBadge status={inc.status} /></td>
                      <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {inc.detected_at ? new Date(inc.detected_at).toLocaleTimeString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
