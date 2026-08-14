import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Shield, AlertTriangle, CheckCircle, Clock, Zap, User } from "lucide-react";

interface ActionScore {
  action_id: string;
  name: string;
  confidence: number;
  requires_approval: boolean;
  risk_level: string;
}

interface RemediationState {
  action_id: string;
  action_name: string;
  service: string;
  confidence: number;
  status: string;
  auto_executed: boolean;
  requires_approval: boolean;
  message: string;
  all_action_scores: ActionScore[];
}

const RISK_COLORS: Record<string, string> = {
  low:    "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  medium: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  high:   "text-rose-400 bg-rose-500/10 border-rose-500/30",
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  executing:         <Clock size={13} className="text-amber-400 animate-spin" />,
  success:           <CheckCircle size={13} className="text-emerald-400" />,
  simulated:         <CheckCircle size={13} className="text-cyan-400" />,
  recommended:       <Zap size={13} className="text-violet-400" />,
  pending_approval:  <User size={13} className="text-amber-400" />,
  requires_approval: <User size={13} className="text-amber-400" />,
  error:             <AlertTriangle size={13} className="text-rose-400" />,
};

export default function RemediationPanel() {
  const [remediation, setRemediation] = useState<RemediationState | null>(null);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);

  useEffect(() => {
    const handler = (e: CustomEvent) => {
      const { type, data } = e.detail;
      if (type === "remediation_executed" && data) {
        setRemediation({
          action_id:         data.action_id || "",
          action_name:       data.action_name || data.action_id || "",
          service:           data.service || "",
          confidence:        data.confidence || 0,
          status:            data.status || "unknown",
          auto_executed:     data.auto_executed || false,
          requires_approval: data.requires_approval || false,
          message:           data.message || "",
          all_action_scores: data.all_action_scores || [],
        });
        setApproved(false);
      }
    };
    window.addEventListener("synapse_ws_event" as any, handler);
    return () => window.removeEventListener("synapse_ws_event" as any, handler);
  }, []);

  const handleApprove = async () => {
    if (!remediation) return;
    setApproving(true);
    try {
      await fetch(
        `/api/v1/remediation/approve/manual?action_id=${remediation.action_id}&service=${remediation.service}`,
        { method: "POST" }
      );
      setApproved(true);
      setRemediation(prev => prev ? { ...prev, status: "executing", auto_executed: true } : null);
    } catch {
      // silently fail
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="synapse-card h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield size={16} className="text-emerald-400" />
          <h3 className="text-sm font-semibold text-white">Auto-Remediation</h3>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded border ${
          remediation?.auto_executed
            ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10"
            : "border-slate-600 text-slate-400 bg-transparent"
        }`}>
          {remediation?.auto_executed ? "Auto-Executed" : "Standby"}
        </span>
      </div>

      {!remediation && (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 py-6">
          <Shield size={28} className="text-slate-600" />
          <p className="text-sm text-slate-500">CQL Agent Ready</p>
          <p className="text-xs text-slate-600 text-center max-w-[200px]">
            Actions will be selected automatically when an incident is detected
          </p>
        </div>
      )}

      {remediation && (
        <div className="flex-1 space-y-3">
          {/* Primary action */}
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-xl p-4 bg-emerald-500/5 border border-emerald-500/20"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {STATUS_ICONS[remediation.status] ?? <Shield size={13} />}
                <span className="text-sm font-semibold text-white">{remediation.action_name}</span>
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded border ${RISK_COLORS.low}`}>
                CQL
              </span>
            </div>

            <div className="text-xs text-slate-400 mb-3">
              Target: <span className="text-white font-mono">{remediation.service}</span>
            </div>

            {/* Confidence bar */}
            <div className="space-y-1 mb-3">
              <div className="flex justify-between text-[11px]">
                <span className="text-slate-400">CQL Confidence</span>
                <span className={`font-bold ${
                  remediation.confidence >= 0.85 ? "text-emerald-400" : "text-amber-400"
                }`}>
                  {(remediation.confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${remediation.confidence * 100}%` }}
                  transition={{ duration: 0.7, ease: "easeOut" }}
                  className={`h-full rounded-full ${
                    remediation.confidence >= 0.85 ? "bg-emerald-500" : "bg-amber-500"
                  }`}
                />
              </div>
              <p className="text-[10px] text-slate-500">
                Threshold: {remediation.confidence >= 0.85 ? "85% ✓ auto" : "< 85% — manual"}
              </p>
            </div>

            {/* Status message */}
            <p className="text-xs text-slate-400 border-t border-slate-700/50 pt-2">
              {remediation.message}
            </p>

            {/* Approval button for low-confidence / high-risk actions */}
            {remediation.requires_approval && !approved && (
              <button
                onClick={handleApprove}
                disabled={approving}
                className="mt-3 w-full py-2 rounded-lg text-xs font-semibold bg-amber-500/20 border border-amber-500/40 text-amber-300 hover:bg-amber-500/30 transition-colors disabled:opacity-50"
              >
                {approving ? "Executing..." : "✓ Approve & Execute"}
              </button>
            )}
            {approved && (
              <div className="mt-3 flex items-center gap-2 text-xs text-emerald-400">
                <CheckCircle size={13} />
                Approved — executing now
              </div>
            )}
          </motion.div>

          {/* All action scores */}
          {remediation.all_action_scores && remediation.all_action_scores.length > 0 && (
            <div className="space-y-1">
              <p className="text-[11px] text-slate-500 font-medium">All Actions</p>
              {remediation.all_action_scores.slice(0, 4).map((a, i) => (
                <div key={a.action_id} className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500 w-4">{i + 1}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        i === 0 ? "bg-emerald-500" : "bg-slate-600"
                      }`}
                      style={{ width: `${a.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-slate-400 w-24 truncate">{a.name}</span>
                  <span className="text-[10px] text-slate-500 w-8 text-right">
                    {(a.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
