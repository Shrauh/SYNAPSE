import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Search, Upload, Server } from "lucide-react";
import { analyzeLog, pushLogs, getPushStatus } from "../api/endpoints";
import { Spinner, StatusBadge } from "../components/UI";

export default function LogsPage() {
  const [analyzingService, setAnalyzingService] = useState("");
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const [pushService, setPushService] = useState("payment-service");
  const [logLines, setLogLines] = useState("");
  const [pushing, setPushing] = useState(false);
  
  const [pushStatus, setPushStatus] = useState<any>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);

  const fetchStatus = () => {
    getPushStatus()
      .then(res => setPushStatus(res))
      .catch(err => console.error(err))
      .finally(() => setLoadingStatus(false));
  };

  useEffect(() => {
    fetchStatus();
    const iv = setInterval(fetchStatus, 10000);
    return () => clearInterval(iv);
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!analyzingService) return;
    setAnalyzing(true);
    try {
      const res = await analyzeLog(analyzingService);
      setAnalysisResult(res);
    } catch (err) {
      console.error(err);
      setAnalysisResult({ error: "Failed to analyze logs" });
    } finally {
      setAnalyzing(false);
    }
  };

  const handlePush = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!logLines.trim()) return;
    setPushing(true);
    try {
      await pushLogs({ service: pushService, logs: logLines.split("\n").filter(l => l.trim()) });
      setLogLines("");
      fetchStatus();
    } catch (err) {
      console.error(err);
    } finally {
      setPushing(false);
    }
  };

  return (
    <div style={{ padding: "84px 2rem 2rem" }}>
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 800 }}>Log Management</h1>
        <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Ingest and analyze service logs</p>
      </motion.div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        {/* Analyze Logs */}
        <div className="card glass">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <Search size={18} color="var(--accent-cyan)" />
            <h2 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Log Analyzer</h2>
          </div>
          <form onSubmit={handleAnalyze} style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <input 
              placeholder="Service name (e.g., payment-service)" 
              value={analyzingService}
              onChange={e => setAnalyzingService(e.target.value)}
              style={{ flex: 1, padding: "8px 12px", background: "rgba(255,255,255,0.45)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)" }}
            />
            <button type="submit" disabled={analyzing} className="btn" style={{ background: "var(--accent-blue)", color: "#fff", padding: "8px 16px", borderRadius: 6, fontWeight: 600 }}>
              {analyzing ? <Spinner /> : "Analyze"}
            </button>
          </form>

          {analysisResult && (
            <div style={{ background: "rgba(255,255,255,0.5)", padding: 16, borderRadius: 8, border: "1px solid var(--border)", fontSize: "0.85rem" }}>
              {analysisResult.error ? (
                <div style={{ color: "var(--status-critical)" }}>{analysisResult.error}</div>
              ) : (
                <>
                  <div style={{ display: "flex", gap: 16, marginBottom: 12 }}>
                    <div><strong>Error Count:</strong> <span style={{ color: "var(--status-critical)" }}>{analysisResult.error_count ?? 0}</span></div>
                    <div><strong>Types:</strong> {(analysisResult.error_types ?? []).join(", ") || "None"}</div>
                  </div>
                  <strong>Last Errors:</strong>
                  <pre style={{ marginTop: 8, padding: 8, background: "rgba(255, 255, 255, 0.6)", borderRadius: 4, overflowX: "auto", color: "var(--status-warning)", fontSize: "0.75rem" }}>
                    {(analysisResult.last_errors ?? []).join("\n") || "No errors found."}
                  </pre>
                </>
              )}
            </div>
          )}
        </div>

        {/* Push Logs */}
        <div className="card glass">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <Upload size={18} color="var(--accent-purple)" />
            <h2 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Push Logs Manually</h2>
          </div>
          <form onSubmit={handlePush} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4, display: "block" }}>Service</label>
              <input 
                value={pushService}
                onChange={e => setPushService(e.target.value)}
                style={{ width: "100%", padding: "8px", background: "rgba(255,255,255,0.45)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)" }}
              />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4, display: "block" }}>Log Lines (one per line)</label>
              <textarea 
                rows={4}
                value={logLines}
                onChange={e => setLogLines(e.target.value)}
                style={{ width: "100%", padding: "8px", background: "rgba(255,255,255,0.45)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)", resize: "vertical" }}
                placeholder="[ERROR] Database connection failed..."
              />
            </div>
            <button type="submit" disabled={pushing} className="btn" style={{ background: "var(--accent-purple)", color: "#fff", padding: "8px", borderRadius: 6, fontWeight: 600 }}>
              {pushing ? "Pushing..." : "Push Logs"}
            </button>
          </form>
        </div>
      </div>

      {/* Push Status Card */}
      <div className="card glass">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
          <Server size={18} color="var(--accent-blue)" />
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Log Stream Status</h2>
        </div>
        {loadingStatus ? (
          <Spinner />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Status</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {!pushStatus || !pushStatus.services || Object.keys(pushStatus.services).length === 0 ? (
                  <tr><td colSpan={3} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>No active log streams</td></tr>
                ) : Object.entries(pushStatus.services).map(([svc, stat]: [string, any]) => (
                  <tr key={svc}>
                    <td style={{ fontWeight: 500 }}>{svc}</td>
                    <td><StatusBadge status={stat.status || "active"} /></td>
                    <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{stat.last_seen || "Just now"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
