import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Brain, BarChart2, RefreshCw, Database } from "lucide-react";

interface LearningData {
  ewc_tasks_learned: number;
  ewc_lambda: number;
  ewc_fisher_computed: boolean;
  maml_initialized: boolean;
  maml_tasks_trained: number;
  maml_inner_lr: number;
  cql_states: number;
  cql_replay_size: number;
  replay_buffer_size: number;
  replay_buffer_capacity: number;
  ac_at_1: number;
  ac_at_3: number;
  forgetting_rate: number;
  total_incidents_learned: number;
}

const DEFAULT_DATA: LearningData = {
  ewc_tasks_learned: 0,
  ewc_lambda: 5000,
  ewc_fisher_computed: false,
  maml_initialized: false,
  maml_tasks_trained: 0,
  maml_inner_lr: 0.01,
  cql_states: 0,
  cql_replay_size: 0,
  replay_buffer_size: 0,
  replay_buffer_capacity: 500,
  ac_at_1: 0,
  ac_at_3: 0,
  forgetting_rate: 0,
  total_incidents_learned: 0,
};

function Gauge({ value, max, label, color }: { value: number; max: number; label: string; color: string }) {
  const pct = Math.min(1, value / max);
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - pct);

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={radius} fill="none" stroke="#1e293b" strokeWidth="6" />
        <motion.circle
          cx="36" cy="36" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1, ease: "easeOut" }}
          transform="rotate(-90 36 36)"
        />
        <text x="36" y="40" textAnchor="middle" fill="white" fontSize="13" fontWeight="700">
          {(pct * 100).toFixed(0)}%
        </text>
      </svg>
      <span className="text-[10px] text-slate-400 text-center">{label}</span>
    </div>
  );
}

function Stat({ label, value, unit = "", highlight = false }: {
  label: string; value: string | number; unit?: string; highlight?: boolean;
}) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
      <span className="text-xs text-slate-400">{label}</span>
      <span className={`text-xs font-bold ${highlight ? "text-emerald-400" : "text-white"}`}>
        {value}{unit}
      </span>
    </div>
  );
}

export default function LearningStats() {
  const [data, setData] = useState<LearningData>(DEFAULT_DATA);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/learning/stats");
      if (res.ok) {
        const json = await res.json();
        setData({ ...DEFAULT_DATA, ...json });
        setLastUpdated(new Date().toLocaleTimeString());
      }
    } catch {
      // silently use defaults
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const id = setInterval(fetchStats, 30_000);
    return () => clearInterval(id);
  }, []);

  const bufferPct = data.replay_buffer_capacity > 0
    ? data.replay_buffer_size / data.replay_buffer_capacity
    : 0;

  return (
    <div className="synapse-card h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-violet-400" />
          <h3 className="text-sm font-semibold text-white">Continual Learning</h3>
        </div>
        <button
          onClick={fetchStats}
          disabled={loading}
          className="p-1.5 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-colors"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Performance gauges */}
      <div className="flex justify-around mb-4">
        <Gauge value={data.ac_at_1}   max={1} label="AC@1" color="#a78bfa" />
        <Gauge value={data.ac_at_3}   max={1} label="AC@3" color="#06b6d4" />
        <Gauge value={1 - data.forgetting_rate} max={1} label="Retention" color="#34d399" />
      </div>

      {/* Target indicators */}
      <div className="flex gap-1.5 mb-4">
        {[
          { label: "AC@1", val: data.ac_at_1, target: 0.80 },
          { label: "AC@3", val: data.ac_at_3, target: 0.90 },
          { label: "Forgetting", val: data.forgetting_rate, target: 0.05, lower: true },
        ].map(({ label, val, target, lower }) => {
          const ok = lower ? val <= target : val >= target;
          return (
            <div
              key={label}
              className={`flex-1 rounded-lg px-2 py-1.5 text-center text-[10px] border ${
                ok ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-400"
                   : "border-amber-500/30 bg-amber-500/5 text-amber-400"
              }`}
            >
              <div className="font-bold">{label}</div>
              <div>{ok ? "✓" : "↑"} {(val * 100).toFixed(1)}% / {(target * 100).toFixed(0)}%</div>
            </div>
          );
        })}
      </div>

      {/* Detailed stats */}
      <div className="flex-1 overflow-y-auto space-y-0 min-h-0">
        <p className="text-[10px] text-slate-500 font-medium mb-1">EWC</p>
        <Stat label="Tasks Consolidated" value={data.ewc_tasks_learned} />
        <Stat label="Lambda (λ)" value={data.ewc_lambda.toLocaleString()} />
        <Stat label="Fisher Computed" value={data.ewc_fisher_computed ? "Yes" : "No"} />

        <p className="text-[10px] text-slate-500 font-medium mt-3 mb-1">MAML</p>
        <Stat label="Initialized" value={data.maml_initialized ? "Yes" : "No"} />
        <Stat label="Tasks Trained" value={data.maml_tasks_trained} />
        <Stat label="Inner LR" value={data.maml_inner_lr} />

        <p className="text-[10px] text-slate-500 font-medium mt-3 mb-1">CQL Agent</p>
        <Stat label="Q-Table States" value={data.cql_states} />
        <Stat label="Replay Buffer" value={`${data.cql_replay_size} / 500`} />

        <p className="text-[10px] text-slate-500 font-medium mt-3 mb-1">Memory</p>
        <div className="space-y-1 pb-2">
          <div className="flex justify-between text-[11px]">
            <span className="text-slate-400">Replay Buffer</span>
            <span className="text-white">{data.replay_buffer_size} / {data.replay_buffer_capacity}</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <motion.div
              animate={{ width: `${bufferPct * 100}%` }}
              className="h-full rounded-full bg-violet-500"
            />
          </div>
        </div>

        <Stat label="Total Incidents Learned" value={data.total_incidents_learned} highlight />
      </div>

      {lastUpdated && (
        <p className="text-[10px] text-slate-600 text-right pt-2">
          Updated {lastUpdated}
        </p>
      )}
    </div>
  );
}
