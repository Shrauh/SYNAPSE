import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { MessageSquare, CheckCircle, XCircle, Send } from "lucide-react";
import { getNotifyStatus, testNotification } from "../api/endpoints";
import { Spinner } from "../components/UI";

export default function NotificationsPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    getNotifyStatus()
      .then(res => setStatus(res))
      .catch(() => setStatus({ slack: { configured: false }, teams: { configured: false } }))
      .finally(() => setLoading(false));
  }, []);

  const handleTest = async (channel: string) => {
    setTesting(channel);
    try {
      await testNotification(channel);
      setToast(`Test notification sent to ${channel}!`);
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      console.error(err);
      setToast(`Failed to send test to ${channel}`);
      setTimeout(() => setToast(null), 3000);
    } finally {
      setTesting(null);
    }
  };

  return (
    <div style={{ padding: "84px 2rem 2rem", position: "relative" }}>
      {toast && (
        <div style={{ position: "fixed", top: 80, right: 24, zIndex: 1000, background: "var(--status-healthy)", color: "#fff", padding: "8px 16px", borderRadius: 8, fontSize: "0.85rem", fontWeight: 600, boxShadow: "0 4px 12px rgba(0,0,0,0.15)" }}>
          {toast}
        </div>
      )}
      
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 800 }}>Notifications</h1>
        <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Configure external alerting channels</p>
      </motion.div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}><Spinner /></div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* Slack Integration */}
          <div className="card glass">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <MessageSquare size={20} color="#E01E5A" />
                <h2 style={{ fontSize: "1.2rem", fontWeight: 600 }}>Slack</h2>
              </div>
              {status?.slack?.configured ? (
                <div style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--status-healthy)", fontSize: "0.85rem", fontWeight: 600 }}>
                  <CheckCircle size={16} /> Configured
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--status-critical)", fontSize: "0.85rem", fontWeight: 600 }}>
                  <XCircle size={16} /> Not Configured
                </div>
              )}
            </div>
            
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 16, lineHeight: 1.5 }}>
              Receive AI incident summaries and root cause reports directly in your Slack channel.
            </p>
            
            {!status?.slack?.configured && (
              <div style={{ background: "rgba(0,0,0,0.2)", padding: 12, borderRadius: 6, border: "1px dashed var(--border)", marginBottom: 16, fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                <strong>Setup Instructions:</strong><br/>
                1. Create an Incoming Webhook in your Slack workspace.<br/>
                2. Set the <code>SLACK_WEBHOOK_URL</code> environment variable in your backend environment.<br/>
                3. Restart the SYNAPSE backend service.
              </div>
            )}

            <button 
              onClick={() => handleTest('slack')}
              disabled={!status?.slack?.configured || testing === 'slack'}
              className="btn" 
              style={{ width: "100%", background: status?.slack?.configured ? "var(--accent-blue)" : "rgba(255,255,255,0.1)", color: status?.slack?.configured ? "#fff" : "var(--text-muted)", padding: "8px", borderRadius: 6, fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
            >
              {testing === 'slack' ? <Spinner /> : <><Send size={16} /> Send Test Message</>}
            </button>
          </div>

          {/* Teams Integration */}
          <div className="card glass">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <MessageSquare size={20} color="#6264A7" />
                <h2 style={{ fontSize: "1.2rem", fontWeight: 600 }}>Microsoft Teams</h2>
              </div>
              {status?.teams?.configured ? (
                <div style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--status-healthy)", fontSize: "0.85rem", fontWeight: 600 }}>
                  <CheckCircle size={16} /> Configured
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--status-critical)", fontSize: "0.85rem", fontWeight: 600 }}>
                  <XCircle size={16} /> Not Configured
                </div>
              )}
            </div>
            
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 16, lineHeight: 1.5 }}>
              Receive AI incident summaries and root cause reports in Microsoft Teams via webhooks.
            </p>
            
            {!status?.teams?.configured && (
              <div style={{ background: "rgba(0,0,0,0.2)", padding: 12, borderRadius: 6, border: "1px dashed var(--border)", marginBottom: 16, fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                <strong>Setup Instructions:</strong><br/>
                1. Configure an Incoming Webhook connector in your Teams channel.<br/>
                2. Set the <code>TEAMS_WEBHOOK_URL</code> environment variable in your backend environment.<br/>
                3. Restart the SYNAPSE backend service.
              </div>
            )}

            <button 
              onClick={() => handleTest('teams')}
              disabled={!status?.teams?.configured || testing === 'teams'}
              className="btn" 
              style={{ width: "100%", background: status?.teams?.configured ? "var(--accent-blue)" : "rgba(255,255,255,0.1)", color: status?.teams?.configured ? "#fff" : "var(--text-muted)", padding: "8px", borderRadius: 6, fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
            >
              {testing === 'teams' ? <Spinner /> : <><Send size={16} /> Send Test Message</>}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
