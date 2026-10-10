import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Trophy, Activity, CheckCircle, Search, Target, Award, List } from "lucide-react";
import { getBenchmark, getEvalHistory, evaluateManual } from "../api/endpoints";
import { StatCard, Spinner, StatusBadge } from "../components/UI";
import { format } from "date-fns";

export default function EvaluationPage() {
  const [benchmark, setBenchmark] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [incId, setIncId] = useState("");
  const [predRanking, setPredRanking] = useState("");
  const [trueRc, setTrueRc] = useState("");
  const [evalResult, setEvalResult] = useState<any>(null);
  const [evaluating, setEvaluating] = useState(false);

  useEffect(() => {
    Promise.all([
      getBenchmark().catch(() => null),
      getEvalHistory().catch(() => []),
    ])
      .then(([bench, hist]) => {
        if (bench) setBenchmark(bench);
        if (hist) setHistory(hist.slice(0, 10)); // last 10
      })
      .finally(() => setLoading(false));
  }, []);

  const handleEvaluate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incId || !predRanking || !trueRc) return;
    setEvaluating(true);
    setEvalResult(null);
    try {
      const result = await evaluateManual({
        incident_id: incId,
        predicted_ranking: predRanking.split(",").map(s => s.trim()),
        true_root_cause: trueRc
      });
      setEvalResult(result);
      
      // refresh history and benchmark
      const [bench, hist] = await Promise.all([getBenchmark(), getEvalHistory()]);
      setBenchmark(bench);
      setHistory(hist.slice(0, 10));
    } catch (err) {
      console.error(err);
    } finally {
      setEvaluating(false);
    }
  };

  const getColor = (val: number) => {
    if (val > 0.5) return "var(--status-healthy)";
    if (val >= 0.3) return "var(--status-warning)";
    return "var(--status-critical)";
  };

  return (
    <div style={{ padding: "84px 2rem 3rem", maxWidth: 1100, margin: "0 auto" }}>
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: 10 }}>
          <Trophy size={24} color="var(--accent-purple)" /> RCAEval Benchmark
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 4 }}>
          Comparing SYNAPSE against published baselines
        </p>
      </motion.div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}><Spinner /></div>
      ) : (
        <>
          {benchmark && (
            <>
              {/* Top Stats */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 24 }}>
                <StatCard title="PR@1" value={benchmark["PR@1"]?.toFixed(3) || "0.000"} icon={<Target size={16} />} color={getColor(benchmark["PR@1"])} />
                <StatCard title="PR@3" value={benchmark["PR@3"]?.toFixed(3) || "0.000"} icon={<Target size={16} />} color={getColor(benchmark["PR@3"])} />
                <StatCard title="PR@5" value={benchmark["PR@5"]?.toFixed(3) || "0.000"} icon={<Target size={16} />} color={getColor(benchmark["PR@5"])} />
                <StatCard title="Avg@5" value={benchmark["Avg@5"]?.toFixed(3) || "0.000"} icon={<Activity size={16} />} color="var(--accent-blue)" />
                <StatCard title="Avg@10" value={benchmark["Avg@10"]?.toFixed(3) || "0.000"} icon={<Activity size={16} />} color="var(--accent-blue)" />
                <StatCard title="MRR" value={benchmark["MRR"]?.toFixed(3) || "0.000"} icon={<Award size={16} />} color="var(--accent-cyan)" />
                <StatCard title="Total Evaluated" value={benchmark.total_incidents || 0} icon={<List size={16} />} color="var(--text-secondary)" />
              </div>

              {/* Comparison Table */}
              <div className="card" style={{ marginBottom: 24 }}>
                <div className="section-title">Baseline Comparison</div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Baseline</th>
                        <th>Their Avg@5</th>
                        <th>SYNAPSE Avg@5</th>
                        <th>Difference</th>
                      </tr>
                    </thead>
                    <tbody>
                      {benchmark.baselines && Object.entries(benchmark.baselines).map(([name, theirs]: [string, any]) => {
                        const ours = benchmark["Avg@5"] || 0;
                        const diff = ours - theirs;
                        return (
                          <tr key={name}>
                            <td style={{ fontWeight: 600 }}>{name}</td>
                            <td>{theirs.toFixed(3)}</td>
                            <td style={{ color: "var(--accent-blue)", fontWeight: 600 }}>{ours.toFixed(3)}</td>
                            <td style={{ color: diff >= 0 ? "var(--status-healthy)" : "var(--status-critical)", fontWeight: 600 }}>
                              {diff >= 0 ? "+" : ""}{diff.toFixed(3)}
                            </td>
                          </tr>
                        );
                      })}
                      {(!benchmark.baselines || Object.keys(benchmark.baselines).length === 0) && (
                        <tr>
                          <td colSpan={4} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                            No baselines to compare against.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            {/* History Table */}
            <div className="card">
              <div className="section-title">Recent Evaluations</div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Incident ID</th>
                      <th>True RC</th>
                      <th>Predicted</th>
                      <th>Rank</th>
                      <th>PR@1</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                          No recent evaluations.
                        </td>
                      </tr>
                    ) : (
                      history.map((h, i) => (
                        <tr key={i}>
                          <td className="mono" style={{ fontSize: "0.75rem" }}>{h.incident_id}</td>
                          <td style={{ color: "var(--status-healthy)" }}>{h.true_root_cause}</td>
                          <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                            {h.predicted_ranking?.[0]}
                          </td>
                          <td>{h.rank}</td>
                          <td>
                            <StatusBadge status={h["PR@1"] === 1 ? "healthy" : "critical"} />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Manual Eval Form */}
            <div className="card glass">
              <div className="section-title">Manual Evaluation</div>
              <form onSubmit={handleEvaluate} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 6 }}>Incident ID</label>
                  <input
                    className="input"
                    value={incId}
                    onChange={e => setIncId(e.target.value)}
                    placeholder="inc_12345"
                    required
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 6 }}>True Root Cause</label>
                  <input
                    className="input"
                    value={trueRc}
                    onChange={e => setTrueRc(e.target.value)}
                    placeholder="cart-service"
                    required
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 6 }}>Predicted Ranking (comma separated)</label>
                  <input
                    className="input"
                    value={predRanking}
                    onChange={e => setPredRanking(e.target.value)}
                    placeholder="cart-service, payment-service, frontend"
                    required
                  />
                </div>
                <button type="submit" className="btn btn-primary" disabled={evaluating}>
                  {evaluating ? <Spinner /> : "Evaluate"}
                </button>
              </form>

              {evalResult && (
                <div style={{ marginTop: 20, padding: 16, background: "var(--bg-elevated)", borderRadius: 8, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: 8, color: "var(--text-primary)" }}>Result</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: "0.8rem" }}>
                    <div>Rank: <span style={{ color: "var(--accent-blue)" }}>{evalResult.rank}</span></div>
                    <div>PR@1: <span style={{ color: "var(--accent-cyan)" }}>{evalResult["PR@1"]}</span></div>
                    <div>PR@3: <span style={{ color: "var(--accent-cyan)" }}>{evalResult["PR@3"]}</span></div>
                    <div>PR@5: <span style={{ color: "var(--accent-cyan)" }}>{evalResult["PR@5"]}</span></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
