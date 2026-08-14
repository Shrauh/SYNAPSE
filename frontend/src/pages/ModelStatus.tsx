import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { fetchModelStatus, fetchHealth } from "../api/endpoints";
import type { ModelStatus, HealthResponse } from "../types/api";
import { Spinner, SectionHeader, MetricRow, EmptyState, Tag } from "../components/UI";
import { Brain, Zap, BookOpen, Shield, RefreshCw, CheckCircle } from "lucide-react";

const FADE_UP = (delay: number) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.35, delay },
});

export default function ModelStatusPage() {
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [m, h] = await Promise.all([fetchModelStatus(), fetchHealth()]);
      setModel(m);
      setHealth(h);
    } catch { /* backend offline */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page-content">
      <div className="page-bg" />

      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
        style={{ marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">AI Model Status</h1>
          <p className="page-subtitle">GNN · Causal Inference · Continual Learning · Meta-Learning</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={13} /> Refresh
        </button>
      </motion.div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}><Spinner /></div>
      ) : !model ? (
        <EmptyState
          icon={<Brain size={40} />}
          title="Backend Offline"
          desc="Start the FastAPI server to see AI model status."
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* System Health Row */}
          <motion.div {...FADE_UP(0)}
            style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            {[
              { label: "API Server", value: health?.components?.api ?? "—", ok: health?.components?.api === "up" },
              { label: "Database", value: health?.components?.database ?? "—", ok: health?.components?.database === "up" },
              { label: "GNN Model", value: health?.components?.gnn_model_loaded ? "loaded" : "fallback", ok: !!health?.components?.gnn_model_loaded },
              { label: "MAML Ready", value: health?.components?.maml_ready ? "ready" : "init", ok: !!health?.components?.maml_ready },
            ].map(({ label, value, ok }) => (
              <div key={label} style={{
                padding: "1rem 1.25rem", borderRadius: "var(--radius-lg)",
                background: ok ? "rgba(16,185,129,0.04)" : "rgba(255,255,255,0.02)",
                border: `1px solid ${ok ? "rgba(16,185,129,0.2)" : "var(--border)"}`,
                display: "flex", alignItems: "center", gap: 10,
              }}>
                <CheckCircle size={16} color={ok ? "var(--accent-emerald)" : "var(--text-muted)"} />
                <div>
                  <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
                  <div style={{ fontSize: "0.82rem", fontWeight: 600, color: ok ? "#34d399" : "var(--text-secondary)" }}>{String(value)}</div>
                </div>
              </div>
            ))}
          </motion.div>

          {/* 2x2 grid of module cards */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

            {/* GNN / DECI Module */}
            <motion.div {...FADE_UP(0.06)} className="card">
              <SectionHeader label="Graph Neural Network" title="DEIC-GNN Anomaly Detector"
                action={<Brain size={16} color="var(--accent-indigo)" />} />
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                <Tag color="indigo">GAT Autoencoder</Tag>
                <Tag color="cyan">Self-Supervised</Tag>
                <Tag>No Labels Needed</Tag>
              </div>
              <MetricRow label="Model Version" value={model.deic_gnn?.version ?? "1.0.0"} />
              <MetricRow label="Tasks Trained On" value={model.deic_gnn?.trained_on_tasks ?? 0} unit=" tasks" />
              <MetricRow label="Node Features" value="5" unit=" (latency, error, cpu, mem, req)" />
              <MetricRow label="GAT Layers" value="2" unit=" layers, 4 heads" />
              <MetricRow label="Latent Dim" value="16" />
              <div style={{ marginTop: 14, padding: "0.75rem", borderRadius: "var(--radius-md)",
                background: "rgba(99,102,241,0.05)", border: "1px solid rgba(99,102,241,0.12)", fontSize: "0.78rem", color: "var(--text-muted)" }}>
                🧠 Trained on normal behavior only. Reconstruction error &gt; threshold = anomaly.
              </div>
            </motion.div>

            {/* MAML */}
            <motion.div {...FADE_UP(0.09)} className="card">
              <SectionHeader label="Meta-Learning" title="MAML Zero-Shot Adapter"
                action={<Zap size={16} color="var(--accent-amber)" />} />
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                <Tag color="indigo">Few-Shot</Tag>
                <Tag>Finn et al. 2017</Tag>
              </div>
              <MetricRow label="Meta LR" value={model.maml?.meta_lr?.toFixed(4) ?? "0.0010"} />
              <MetricRow label="Inner LR" value={model.maml?.inner_lr?.toFixed(4) ?? "0.0100"} />
              <MetricRow label="Tasks Meta-Trained" value={model.maml?.tasks_meta_trained ?? 0} unit=" services" />
              <MetricRow label="Adaptation Steps" value="5–10" unit=" gradient steps" />
              <MetricRow label="Cold Start" value="Eliminated" />
              <div style={{ marginTop: 14, padding: "0.75rem", borderRadius: "var(--radius-md)",
                background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.12)", fontSize: "0.78rem", color: "var(--text-muted)" }}>
                ⚡ New service? Adapts in 5 steps. No 2-week baseline wait.
              </div>
            </motion.div>

            {/* EWC Continual Learning */}
            <motion.div {...FADE_UP(0.12)} className="card">
              <SectionHeader label="Continual Learning" title="EWC — No Catastrophic Forgetting"
                action={<BookOpen size={16} color="var(--accent-emerald)" />} />
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                <Tag color="emerald">EWC</Tag>
                <Tag>DeepMind 2017</Tag>
                <Tag>Replay Buffer</Tag>
              </div>
              <MetricRow label="EWC λ" value={model.continual_learning?.ewc_lambda?.toFixed(0) ?? "5000"} />
              <MetricRow label="Tasks Learned" value={model.continual_learning?.tasks_learned ?? 0} unit=" incidents" />
              <MetricRow label="Replay Buffer Size" value={model.continual_learning?.replay_buffer_size ?? 0} unit=" samples" />
              <MetricRow label="Forgetting Rate" value={((model.continual_learning?.forgetting_rate ?? 0) * 100).toFixed(2)} unit="%" />
              <MetricRow label="Target Forgetting" value="&lt; 5%" />

              {/* Forgetting rate bar */}
              <div style={{ marginTop: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 5 }}>
                  <span>Forgetting Rate</span>
                  <span>{((model.continual_learning?.forgetting_rate ?? 0) * 100).toFixed(2)}%</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{
                    width: `${(model.continual_learning?.forgetting_rate ?? 0) * 100}%`,
                    background: (model.continual_learning?.forgetting_rate ?? 0) < 0.05
                      ? "var(--grad-healthy)" : "var(--grad-danger)",
                  }} />
                </div>
              </div>
            </motion.div>

            {/* Innovation Summary */}
            <motion.div {...FADE_UP(0.15)} className="card">
              <SectionHeader label="Research" title="Key Innovations"
                action={<Shield size={16} color="var(--accent-violet)" />} />
              <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                {[
                  { num: "01", label: "LLM as Causal Prior Injector", badge: "Novel — First in Literature", color: "var(--accent-indigo)" },
                  { num: "02", label: "DECI + Do-Calculus for RCA", badge: "Microsoft Research CAUSICA", color: "var(--accent-violet)" },
                  { num: "03", label: "EWC Continual Learning", badge: "Zero Catastrophic Forgetting", color: "var(--accent-emerald)" },
                  { num: "04", label: "MAML Zero-Shot Adaptation", badge: "5-step new service onboarding", color: "var(--accent-amber)" },
                  { num: "05", label: "CQL Safe Remediation RL", badge: "Offline RL — No Prod Risk", color: "var(--accent-cyan)" },
                ].map(({ num, label, badge, color }) => (
                  <div key={num} style={{ display: "flex", gap: 12, padding: "0.7rem 0", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                    <span style={{ fontSize: "0.72rem", fontWeight: 800, color, fontFamily: "JetBrains Mono", flexShrink: 0 }}>{num}</span>
                    <div>
                      <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>{label}</div>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>{badge}</div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* Uptime */}
          {health && (
            <motion.div {...FADE_UP(0.18)} className="card" style={{ padding: "1rem 1.5rem" }}>
              <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
                <div>
                  <div className="section-label">Server Uptime</div>
                  <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--accent-emerald)" }}>
                    {Math.floor((health.uptime_seconds ?? 0) / 60)}m {Math.round((health.uptime_seconds ?? 0) % 60)}s
                  </div>
                </div>
                <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: 24 }}>
                  <div className="section-label">API Version</div>
                  <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)" }}>v{health.version}</div>
                </div>
                <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: 24 }}>
                  <div className="section-label">Overall Status</div>
                  <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--accent-emerald)" }}>
                    {health.status?.toUpperCase()}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}
