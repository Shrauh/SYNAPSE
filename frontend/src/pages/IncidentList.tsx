import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { fetchIncidents } from "../api/endpoints";
import type { IncidentSummary } from "../types/api";
import { Spinner } from "../components/UI";
import { SimulateModal } from "../components/SimulateModal";
import { Zap, ChevronLeft, ChevronRight } from "lucide-react";
import { format } from "date-fns";

function getSeverityRowClass(sev: string) {
  const s = (sev || "").toLowerCase();
  if (s === "critical" || s === "l4" || s === "l3") return "incident-row-critical";
  if (s === "high" || s === "l2") return "incident-row-high";
  if (s === "medium" || s === "l1") return "incident-row-medium";
  return "incident-row-low";
}

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
                    <th>Title</th>
                    <th>Root Cause</th>
                    <th>Severity</th>
                    <th>Confidence</th>
                    <th>Time</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.length === 0 ? (
                    <tr><td colSpan={6} style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
                      No incidents found. Simulate a fault to create one!
                    </td></tr>
                  ) : incidents.map((inc, i) => (
                    <motion.tr
                      key={inc.id}
                      className={`incident-row ${getSeverityRowClass(inc.severity)}`}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      whileHover={{ scale: 1.008 }}
                      transition={{ delay: i * 0.04, duration: 0.2 }}
                      onClick={() => nav(`/incidents/${inc.id}`)}
                      style={{
                        background: i % 2 === 1 ? "rgba(255, 255, 255, 0.02)" : "transparent",
                        cursor: "pointer",
                      }}>
                      <td style={{ color: "var(--text-primary)", fontWeight: 600, maxWidth: 260 }}>
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{inc.title}</div>
                        <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>{inc.id}</div>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem", color: inc.root_cause_service ? "var(--accent-blue)" : "var(--text-muted)" }}>
                        {inc.root_cause_service ?? "analyzing..."}
                      </td>
                      <td>
                        <span className={`badge ${
                          inc.severity === "critical" || inc.severity === "L4" || inc.severity === "L3"
                            ? "badge-critical"
                            : inc.severity === "high" || inc.severity === "L2"
                            ? "badge-warning"
                            : inc.severity === "medium" || inc.severity === "L1"
                            ? "badge-degraded"
                            : "badge-healthy"
                        }`}>
                          {inc.severity}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600, color: inc.confidence != null ? "var(--status-healthy)" : "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {inc.confidence != null ? `${(inc.confidence * 100).toFixed(0)}%` : "—"}
                      </td>
                      <td style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {format(new Date(inc.detected_at), "dd MMM HH:mm")}
                      </td>
                      <td>
                        <span className={`badge ${
                          inc.status === "analyzing"
                            ? "badge-analyzing"
                            : inc.status === "detected" || inc.status === "resolved"
                            ? "badge-detected"
                            : inc.status === "error"
                            ? "badge-error"
                            : `badge-${inc.status}`
                        }`}>
                          {inc.status}
                        </span>
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
