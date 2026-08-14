import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FileText, ChevronRight, Lightbulb, Loader2 } from "lucide-react";

interface ReportPanelProps {
  incidentId?: string;
}

interface ReportData {
  explanation: string;
  propagation_chain: string;
  recommended_actions: string[];
  model_info?: {
    gnn_type?: string;
    causal_method?: string;
    execution_time_ms?: number;
  };
  root_cause?: {
    service: string;
    confidence: number;
    fault_type?: string;
  };
}

export default function ReportPanel({ incidentId }: ReportPanelProps) {
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState<string>("mock");

  // Listen for RCA complete events
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      const { type, data } = e.detail;
      if (type === "rca_complete" && data?.explanation) {
        setReport({
          explanation: data.explanation,
          propagation_chain: data.propagation_chain || "",
          recommended_actions: data.recommended_actions || [],
          root_cause: {
            service: data.root_cause,
            confidence: data.confidence,
            fault_type: data.fault_type,
          },
        });
        setProvider(data._provider || "mock");
      }
    };
    window.addEventListener("synapse_ws_event" as any, handler);
    return () => window.removeEventListener("synapse_ws_event" as any, handler);
  }, []);

  // Fetch report if incidentId provided
  useEffect(() => {
    if (!incidentId) return;
    setLoading(true);

    const fetchReport = async () => {
      try {
        const res = await fetch(`/api/v1/incidents/${incidentId}/report`);
        if (res.ok) {
          const data = await res.json();
          setReport({
            explanation: data.explanation || "",
            propagation_chain: data.propagation_chain || "",
            recommended_actions: data.recommended_actions || [],
            model_info: data.model_info,
            root_cause: data.root_cause,
          });
        }
      } catch {
        // silently fail
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [incidentId]);

  return (
    <div className="synapse-card h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-emerald-400" />
          <h3 className="text-sm font-semibold text-white">AI Report</h3>
        </div>
        <div className="flex items-center gap-2">
          {provider !== "mock" && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              {provider === "groq" ? "Groq Llama 3" : "GPT-4o"}
            </span>
          )}
          {provider === "mock" && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-700/50 border border-slate-600 text-slate-400">
              Template
            </span>
          )}
          {loading && <Loader2 size={13} className="animate-spin text-slate-400" />}
        </div>
      </div>

      {!report && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 py-8">
          <FileText size={28} className="text-slate-600" />
          <p className="text-sm text-slate-500">No report yet</p>
          <p className="text-xs text-slate-600">Trigger an RCA to generate an AI explanation</p>
        </div>
      )}

      {loading && (
        <div className="flex-1 flex items-center justify-center gap-2">
          <Loader2 size={20} className="animate-spin text-emerald-400" />
          <span className="text-sm text-slate-400">Generating explanation...</span>
        </div>
      )}

      {report && !loading && (
        <div className="flex-1 overflow-y-auto space-y-4 min-h-0">
          {/* Explanation */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-xl p-4 bg-emerald-500/5 border border-emerald-500/20"
          >
            <p className="text-xs font-medium text-emerald-400 mb-2">Explanation</p>
            <p className="text-sm text-slate-300 leading-relaxed">
              {report.explanation || "Analysis complete. Review recommended actions below."}
            </p>
          </motion.div>

          {/* Recommended Actions */}
          {report.recommended_actions && report.recommended_actions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="space-y-2"
            >
              <div className="flex items-center gap-2">
                <Lightbulb size={13} className="text-amber-400" />
                <p className="text-xs font-medium text-amber-400">Recommended Actions</p>
              </div>
              {report.recommended_actions.map((action, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 rounded-lg px-3 py-2 bg-slate-900/60 border border-slate-700/50"
                >
                  <span className="text-[10px] font-bold text-slate-500 mt-0.5 flex-shrink-0">{i + 1}.</span>
                  <p className="text-xs text-slate-300">{action}</p>
                </div>
              ))}
            </motion.div>
          )}

          {/* Model Info */}
          {report.model_info && (
            <div className="flex flex-wrap gap-2 text-[10px] text-slate-500">
              {report.model_info.gnn_type && (
                <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                  {report.model_info.gnn_type}
                </span>
              )}
              {report.model_info.causal_method && (
                <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                  {report.model_info.causal_method}
                </span>
              )}
              {report.model_info.execution_time_ms && (
                <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                  {report.model_info.execution_time_ms.toFixed(0)}ms
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
