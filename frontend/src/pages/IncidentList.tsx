import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { fetchIncidents } from "../api/endpoints";
import type { IncidentSummary } from "../types/api";
import { StatusBadge, Spinner } from "../components/UI";
import { SimulateModal } from "../components/SimulateModal";
import { Zap, ChevronLeft, ChevronRight } from "lucide-react";
import { format } from "date-fns";

export default function IncidentList() {
  const nav = useNavigate();
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showSim, setShowSim] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchIncidents(page).then(r => { setIncidents(r.incidents); setTotal(r.total); }).finally(() => setLoading(false));
  }, [page]);

  const totalPages = Math.ceil(total / 20) || 1;

  return (
    <div style={{ padding: "84px 2rem 2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em" }}>Incidents</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.82rem", marginTop: 3 }}>{total} total incidents</p>
        </div>
        <button className="btn btn-danger" onClick={() => setShowSim(true)}><Zap size={14} /> Simulate Fault</button>
      </div>

      <div className="card">
        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}><Spinner /></div>
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title</th><th>Status</th><th>Severity</th>
                    <th>Root Cause</th><th>Confidence</th>
                    <th>Affected Services</th><th>Detected At</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.length === 0 ? (
                    <tr><td colSpan={7} style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
                      No incidents found. Simulate a fault to create one!
                    </td></tr>
                  ) : incidents.map((inc, i) => (
                    <motion.tr key={inc.id}
                      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.04 }}
                      onClick={() => nav(`/incidents/${inc.id}`)}>
                      <td style={{ color: "var(--text-primary)", fontWeight: 600, maxWidth: 240 }}>
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{inc.title}</div>
                        <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontFamily: "JetBrains Mono" }}>{inc.id}</div>
                      </td>
                      <td><StatusBadge status={inc.status} /></td>
                      <td><span className={`badge badge-${inc.severity === "critical" ? "critical" : inc.severity === "high" ? "warning" : "degraded"}`}>{inc.severity}</span></td>
                      <td style={{ fontFamily: "JetBrains Mono", fontSize: "0.78rem", color: inc.root_cause_service ? "var(--accent-blue)" : "var(--text-muted)" }}>
                        {inc.root_cause_service ?? "analyzing..."}
                      </td>
                      <td style={{ fontWeight: 600, color: "var(--status-healthy)" }}>
                        {inc.confidence != null ? `${(inc.confidence * 100).toFixed(0)}%` : "—"}
                      </td>
                      <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {inc.affected_services?.slice(0, 2).join(", ") ?? "—"}
                        {(inc.affected_services?.length ?? 0) > 2 && ` +${inc.affected_services.length - 2}`}
                      </td>
                      <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {format(new Date(inc.detected_at), "dd MMM HH:mm")}
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 8, marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
                <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Page {page} / {totalPages}</span>
                <button className="btn btn-ghost" style={{ padding: "4px 10px" }} onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}><ChevronLeft size={14} /></button>
                <button className="btn btn-ghost" style={{ padding: "4px 10px" }} onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}><ChevronRight size={14} /></button>
              </div>
            )}
          </>
        )}
      </div>

      {showSim && <SimulateModal onClose={() => setShowSim(false)} />}
    </div>
  );
}
