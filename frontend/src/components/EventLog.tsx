import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, AlertTriangle, CheckCircle, Shield, Zap } from "lucide-react";
import { format } from "date-fns";

interface LogEntry {
  id: string;
  type: "anomaly_update" | "incident_detected" | "rca_complete" | "remediation_executed" | "log_event" | "alert" | "info";
  timestamp: string;
  title: string;
  detail: string;
  severity?: "info" | "warning" | "critical";
}

interface EventLogProps {
  maxEntries?: number;
}

const TYPE_CONFIG: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
  anomaly_update:      { icon: <Activity size={14}/>,     color: "text-cyan-400",   bg: "bg-cyan-500/10" },
  incident_detected:   { icon: <AlertTriangle size={14}/>, color: "text-amber-400", bg: "bg-amber-500/10" },
  rca_complete:        { icon: <Zap size={14}/>,           color: "text-violet-400", bg: "bg-violet-500/10" },
  remediation_executed:{ icon: <Shield size={14}/>,        color: "text-emerald-400",bg: "bg-emerald-500/10" },
  log_event:           { icon: <AlertTriangle size={14}/>, color: "text-rose-400",  bg: "bg-rose-500/10" },
  alert:               { icon: <AlertTriangle size={14}/>, color: "text-amber-400", bg: "bg-amber-500/10" },
  info:                { icon: <CheckCircle size={14}/>,   color: "text-slate-400",  bg: "bg-slate-500/10" },
};

function useGlobalEvents() {
  const [events, setEvents] = useState<LogEntry[]>([]);

  useEffect(() => {
    // Listen to custom DOM events dispatched by useLiveAnomalies
    const handler = (e: CustomEvent) => {
      const { type, data, timestamp } = e.detail;
      let entry: LogEntry | null = null;

      if (type === "incident_detected") {
        entry = {
          id: `${Date.now()}-${Math.random()}`,
          type: "incident_detected",
          timestamp: timestamp || new Date().toISOString(),
          title: `Incident Detected`,
          detail: `${data?.critical_services?.join(", ") || "Unknown"} service(s) anomalous`,
          severity: "critical",
        };
      } else if (type === "rca_complete") {
        entry = {
          id: `${Date.now()}-${Math.random()}`,
          type: "rca_complete",
          timestamp: timestamp || new Date().toISOString(),
          title: `RCA Complete`,
          detail: `Root cause: ${data?.root_cause || "unknown"} (${((data?.confidence || 0) * 100).toFixed(0)}%)`,
          severity: "warning",
        };
      } else if (type === "remediation_executed") {
        entry = {
          id: `${Date.now()}-${Math.random()}`,
          type: "remediation_executed",
          timestamp: timestamp || new Date().toISOString(),
          title: `Remediation: ${data?.action_name || data?.action_id}`,
          detail: `${data?.service || "?"} — ${data?.status || "unknown"}`,
          severity: "info",
        };
      } else if (type === "anomaly_update" && data?.critical_services?.length > 0) {
        entry = {
          id: `${Date.now()}-${Math.random()}`,
          type: "anomaly_update",
          timestamp: timestamp || new Date().toISOString(),
          title: `High Anomaly Detected`,
          detail: `Critical: ${data.critical_services.join(", ")}`,
          severity: "warning",
        };
      }

      if (entry) {
        setEvents(prev => [entry!, ...prev].slice(0, 100));
      }
    };

    window.addEventListener("synapse_ws_event" as any, handler);
    return () => window.removeEventListener("synapse_ws_event" as any, handler);
  }, []);

  // Seed with initial info entry
  useEffect(() => {
    setEvents([{
      id: "init",
      type: "info",
      timestamp: new Date().toISOString(),
      title: "SYNAPSE Online",
      detail: "WebSocket connected — monitoring active",
      severity: "info",
    }]);
  }, []);

  return events;
}

export default function EventLog({ maxEntries = 50 }: EventLogProps) {
  const events = useGlobalEvents();
  const bottomRef = useRef<HTMLDivElement>(null);

  return (
    <div className="synapse-card h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Event Stream</h3>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-xs text-slate-400">live</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 scroll-smooth min-h-0"
           style={{ maxHeight: 320 }}>
        <AnimatePresence initial={false} mode="popLayout">
          {events.slice(0, maxEntries).map((entry) => {
            const cfg = TYPE_CONFIG[entry.type] ?? TYPE_CONFIG.info;
            return (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: -12, height: 0 }}
                animate={{ opacity: 1, x: 0, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className={`flex items-start gap-2.5 rounded-lg px-3 py-2 ${cfg.bg} border border-white/5`}
              >
                <span className={`${cfg.color} mt-0.5 flex-shrink-0`}>{cfg.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-xs font-medium ${cfg.color} truncate`}>{entry.title}</span>
                    <span className="text-[10px] text-slate-500 flex-shrink-0">
                      {format(new Date(entry.timestamp), "HH:mm:ss")}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 truncate mt-0.5">{entry.detail}</p>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
