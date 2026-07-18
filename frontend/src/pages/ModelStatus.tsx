import { useEffect, useState } from "react";
import { fetchModelStatus } from "../api/endpoints";
import type { ModelStatus } from "../types/api";
import { Spinner } from "../components/UI";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Brain, Zap, RefreshCw, Shield } from "lucide-react";

const Row = ({ label, value }: { label: string; value: string | number }) => (
  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem" }}>
    <span style={{ color: "var(--text-muted)" }}>{label}</span>
    <span style={{ color: "var(--text-primary)", fontFamily: "JetBrains Mono", fontWeight: 600 }}>{value}</span>
  </div>
);

export default function ModelStatusPage() {
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    fetchModelStatus().then(setStatus).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const dummyLoss = Array.from({ length: 12 }, (_, i) => ({
    step: `T${i + 1}`,
    loss: Math.max(0.05, 0.85 * Math.exp(-0.35 * i) + Math.random() * 0.04),
  }));

  return (
    <div style={{ padding: "84px 2rem 3rem", maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em" }}>AI Model Status</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.82rem", marginTop: 3 }}>
            GNN · Continual Learning · MAML · Causal Inference
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load}><RefreshCw size={13} /> Refresh</button>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}><Spinner /></div>
      ) : status ? (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 24 }}>
            {/* GNN */}
            <div className="card card-glow">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: "rgba(59,130,246,0.15)",
                  display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-blue)" }}>
                  <Brain size={16} />
                </div>
                <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>GNN Model</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <Row label="Version" value={status.deic_gnn.version} />
                <Row label="Architecture" value="GAT Autoencoder" />
                <Row label="Tasks Trained" value={status.deic_gnn.trained_on_tasks} />
                <Row label="Status" value={status.deic_gnn.trained_on_tasks > 0 ? "✅ Ready" : "⏳ Untrained"} />
              </div>
            </div>

            {/* MAML */}
            <div className="card card-glow">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: "rgba(139,92,246,0.15)",
                  display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-purple)" }}>
                  <Zap size={16} />
                </div>
                <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>MAML</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <Row label="Meta LR" value={status.maml.meta_lr} />
                <Row label="Inner LR" value={status.maml.inner_lr} />
                <Row label="Inner Steps" value={3} />
                <Row label="Tasks Meta-Trained" value={status.maml.tasks_meta_trained} />
              </div>
            </div>

            {/* Continual Learning */}
            <div className="card card-glow">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: "rgba(6,182,212,0.15)",
                  display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-cyan)" }}>
                  <Shield size={16} />
                </div>
                <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>Continual Learning</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <Row label="EWC λ" value={status.continual_learning.ewc_lambda} />
                <Row label="Tasks Learned" value={status.continual_learning.tasks_learned} />
                <Row label="Replay Buffer" value={`${status.continual_learning.replay_buffer_size} samples`} />
                <Row label="Forgetting Rate" value={`${(status.continual_learning.forgetting_rate * 100).toFixed(1)}%`} />
              </div>
            </div>
          </div>

          {/* Training Loss Chart */}
          <div className="card">
            <div className="section-title">GNN Training Loss Curve</div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={dummyLoss}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" />
                <XAxis dataKey="step" stroke="var(--text-muted)" tick={{ fontSize: 11 }} />
                <YAxis stroke="var(--text-muted)" tick={{ fontSize: 11 }} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "var(--text-secondary)" }}
                />
                <Line type="monotone" dataKey="loss" stroke="var(--accent-blue)"
                  strokeWidth={2} dot={false} activeDot={{ r: 4, fill: "var(--accent-blue)" }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <div className="card" style={{ color: "var(--text-muted)", textAlign: "center", padding: "3rem" }}>
          Failed to load model status. Is the backend running?
        </div>
      )}
    </div>
  );
}
