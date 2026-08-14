import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Zap, CheckCircle, Loader } from "lucide-react";
import { simulateFault } from "../api/endpoints";
import { useNavigate } from "react-router-dom";

const SERVICES = [
  "api-gateway","auth-service","user-service","payment-service",
  "order-service","inventory-service","notification-service",
  "search-service","cache-service","database",
];
const FAULT_TYPES = ["latency_spike","error_burst","resource_exhaustion"];
const SEVERITIES = ["low","medium","high","critical"];

const STEPS = [
  "Injecting fault...",
  "Running GNN anomaly detection...",
  "Running causal inference...",
  "Generating LLM explanation...",
  "RCA complete!",
];

interface Props { onClose: () => void; }

export function SimulateModal({ onClose }: Props) {
  const nav = useNavigate();
  const [form, setForm] = useState({
    root_cause_service: "database",
    fault_type: "latency_spike",
    severity: "critical",
    duration_minutes: 5,
  });
  const [running, setRunning] = useState(false);
  const [step, setStep] = useState(-1);
  const [incidentId, setIncidentId] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setStep(0);
    try {
      const res = await simulateFault(form);
      setIncidentId(res.incident_id);
      // Animate through steps
      for (let i = 1; i < STEPS.length; i++) {
        await new Promise(r => setTimeout(r, 1200));
        setStep(i);
      }
      await new Promise(r => setTimeout(r, 800));
      nav(`/incidents/${res.incident_id}`);
    } catch (e) {
      console.error(e);
      setRunning(false);
      setStep(-1);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        style={{
          position: "fixed", inset: 0, zIndex: 200,
          background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
        onClick={!running ? onClose : undefined}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          onClick={e => e.stopPropagation()}
          className="card"
          style={{ width: 480, position: "relative" }}
        >
          {!running && (
            <button onClick={onClose} className="btn btn-ghost"
              style={{ position: "absolute", top: 12, right: 12, padding: "4px 8px" }}>
              <X size={14} />
            </button>
          )}

          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(239,68,68,0.15)",
              display: "flex", alignItems: "center", justifyContent: "center", color: "var(--status-critical)" }}>
              <Zap size={18} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: "1rem" }}>Simulate Fault</div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Inject a synthetic fault and run full RCA</div>
            </div>
          </div>

          {!running ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {[
                { label: "Root Cause Service", key: "root_cause_service", opts: SERVICES },
                { label: "Fault Type", key: "fault_type", opts: FAULT_TYPES },
                { label: "Severity", key: "severity", opts: SEVERITIES },
              ].map(({ label, key, opts }) => (
                <div key={key}>
                  <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</div>
                  <select
                    className="input"
                    value={form[key as keyof typeof form]}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  >
                    {opts.map(o => <option key={o}>{o}</option>)}
                  </select>
                </div>
              ))}
              <div>
                <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>Duration (minutes)</div>
                <input className="input" type="number" min={1} max={30}
                  value={form.duration_minutes}
                  onChange={e => setForm(f => ({ ...f, duration_minutes: Number(e.target.value) }))} />
              </div>
              <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
                <button className="btn btn-ghost" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
                <button className="btn btn-danger" style={{ flex: 2 }} onClick={run}>
                  <Zap size={14} /> Run Simulation
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {STEPS.map((s, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -12 }} animate={{ opacity: i <= step ? 1 : 0.3, x: 0 }}
                  style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  {i < step ? <CheckCircle size={16} color="var(--status-healthy)" /> :
                   i === step ? <Loader size={16} color="var(--accent-blue)" style={{ animation: "spin 1s linear infinite" }} /> :
                   <div style={{ width: 16, height: 16, borderRadius: "50%", background: "var(--border)" }} />}
                  <span style={{ fontSize: "0.85rem", color: i <= step ? "var(--text-primary)" : "var(--text-muted)" }}>{s}</span>
                </motion.div>
              ))}
              {incidentId && step === STEPS.length - 1 && (
                <div style={{ marginTop: 8, padding: "8px 12px", background: "rgba(16,185,129,0.1)", borderRadius: 8, fontSize: "0.8rem", color: "var(--status-healthy)" }}>
                  Incident ID: <span className="mono">{incidentId}</span> — Redirecting...
                </div>
              )}
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
