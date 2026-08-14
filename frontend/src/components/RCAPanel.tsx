import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Target, ChevronRight, AlertTriangle } from "lucide-react";
import { api } from "../api/endpoints";

interface RootCandidate {
  service: string;
  confidence: number;
  fault_type?: string;
  anomaly_score?: number;
}

interface RCAPanelProps {
  incidentId?: string;
}

const FAULT_COLORS: Record<string, string> = {
  cpu_stress:       "text-amber-400 bg-amber-500/10 border-amber-500/30",
  db_exhaustion:    "text-rose-400 bg-rose-500/10 border-rose-500/30",
  oom_kill:         "text-rose-400 bg-rose-500/10 border-rose-500/30",
  memory_leak:      "text-orange-400 bg-orange-500/10 border-orange-500/30",
  network_latency:  "text-violet-400 bg-violet-500/10 border-violet-500/30",
  pod_crash:        "text-red-400 bg-red-500/10 border-red-500/30",
  cascade_failure:  "text-rose-400 bg-rose-500/10 border-rose-500/30",
  retry_storm:      "text-amber-400 bg-amber-500/10 border-amber-500/30",
  config_error:     "text-blue-400 bg-blue-500/10 border-blue-500/30",
  dns_failure:      "text-cyan-400 bg-cyan-500/10 border-cyan-500/30",
  latency_spike:    "text-violet-400 bg-violet-500/10 border-violet-500/30",
  error_burst:      "text-rose-400 bg-rose-500/10 border-rose-500/30",
  resource_exhaustion: "text-orange-400 bg-orange-500/10 border-orange-500/30",
  unknown:          "text-slate-400 bg-slate-500/10 border-slate-500/30",
};

export default function RCAPanel({ incidentId }: RCAPanelProps) {
  const [candidates, setCandidates] = useState<RootCandidate[]>([]);
  const [propagationChain, setPropagationChain] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  // Listen for RCA complete events from WebSocket
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      const { type, data } = e.detail;
      if (type === "rca_complete" && data) {
        setCandidates([{
          service: data.root_cause || "unknown",
          confidence: data.confidence || 0,
          fault_type: data.fault_type || "unknown",
        }]);
        setPropagationChain(data.propagation_chain || "");
        setLastUpdated(new Date().toISOString());
      }
    };
    window.addEventListener("synapse_ws_event" as any, handler);
    return () => window.removeEventListener("synapse_ws_event" as any, handler);
  }, []);

  // Fetch from API if incidentId provided
  useEffect(() => {
    if (!incidentId) return;

    const fetchReport = async () => {
      setLoading(true);
      try {
        const report = await api.getIncidentReport(incidentId);
        if (report?.root_cause) {
          setCandidates([{
            service: report.root_cause.service,
            confidence: report.root_cause.confidence,
            fault_type: report.root_cause.fault_type,
          }]);
          setPropagationChain(report.propagation_chain || "");
          setLastUpdated(new Date().toISOString());
        }
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [incidentId]);

  const hasData = candidates.length > 0;

  return (
    <div className="synapse-card h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target size={16} className="text-violet-400" />
          <h3 className="text-sm font-semibold text-white">Root Cause Analysis</h3>
        </div>
        {loading && (
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <div className="w-3 h-3 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
            Analyzing...
          </div>
        )}
      </div>

      {!hasData && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center text-center gap-3 py-8">
          <AlertTriangle size={28} className="text-slate-600" />
          <p className="text-sm text-slate-500">No RCA results yet</p>
          <p className="text-xs text-slate-600">Run a simulation or trigger RCA analysis</p>
        </div>
      )}

      {hasData && (
        <div className="flex-1 space-y-3">
          {candidates.map((cand, idx) => {
            const faultClass = FAULT_COLORS[cand.fault_type || "unknown"] ?? FAULT_COLORS.unknown;
            const barWidth = `${Math.round(cand.confidence * 100)}%`;
            const isTop = idx === 0;

            return (
              <motion.div
                key={`${cand.service}-${idx}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.08 }}
                className={`rounded-xl p-4 border ${
                  isTop
                    ? "border-violet-500/40 bg-violet-500/5"
                    : "border-white/5 bg-white/2"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {isTop && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30">
                        #1
                      </span>
                    )}
                    <span className="text-sm font-semibold text-white">{cand.service}</span>
                  </div>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded border ${faultClass}`}>
                    {cand.fault_type || "unknown"}
                  </span>
                </div>

                {/* Confidence bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-400">Confidence</span>
                    <span className={`font-bold ${
                      cand.confidence > 0.85 ? "text-emerald-400" :
                      cand.confidence > 0.65 ? "text-amber-400" : "text-rose-400"
                    }`}>
                      {(cand.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: barWidth }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      className={`h-full rounded-full ${
                        cand.confidence > 0.85 ? "bg-emerald-500" :
                        cand.confidence > 0.65 ? "bg-amber-500" : "bg-rose-500"
                      }`}
                    />
                  </div>
                </div>

                {cand.anomaly_score !== undefined && (
                  <p className="text-[11px] text-slate-500 mt-1">
                    Anomaly score: {cand.anomaly_score.toFixed(3)}
                  </p>
                )}
              </motion.div>
            );
          })}

          {/* Propagation chain */}
          {propagationChain && (
            <div className="mt-3 rounded-xl p-3 bg-slate-900/60 border border-slate-700/50">
              <p className="text-[11px] text-slate-400 mb-1.5 font-medium">Propagation Chain</p>
              <div className="flex items-center flex-wrap gap-1">
                {propagationChain.split("→").map((svc, i, arr) => (
                  <span key={i} className="flex items-center gap-1">
                    <span className="text-xs text-slate-300 font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                      {svc.trim()}
                    </span>
                    {i < arr.length - 1 && (
                      <ChevronRight size={12} className="text-slate-600" />
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}

          {lastUpdated && (
            <p className="text-[10px] text-slate-600 text-right">
              Updated {new Date(lastUpdated).toLocaleTimeString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
