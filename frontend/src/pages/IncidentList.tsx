import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle, Search, Filter, RefreshCw,
  ChevronRight, Zap, Clock, Target
} from "lucide-react";
import { fetchIncidents } from "../api/endpoints";
import type { IncidentSummary } from "../types/api";
import { StatusBadge, Spinner, EmptyState, SectionHeader } from "../components/UI";
import { formatDistanceToNow } from "date-fns";

const SEVERITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export default function IncidentList() {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      const data = await fetchIncidents(1);
      setIncidents(data.incidents);
    } catch { /* backend offline */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = incidents
    .filter(i => filterSeverity === "all" || i.severity === filterSeverity)
    .filter(i => filterStatus === "all" || i.status === filterStatus)
    .filter(i =>
      !search ||
      i.title.toLowerCase().includes(search.toLowerCase()) ||
      (i.root_cause_service ?? "").toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      const sa = SEVERITY_ORDER[a.severity] ?? 99;
      const sb = SEVERITY_ORDER[b.severity] ?? 99;
      if (sa !== sb) return sa - sb;
      return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime();
    });

  const stats = {
    total: incidents.length,
    critical: incidents.filter(i => i.severity === "critical").length,
    analyzing: incidents.filter(i => i.status === "analyzing").length,
    resolved: incidents.filter(i => i.status === "resolved").length,
  };

  return (
    <div className="page-content">
      <div className="page-bg" />

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
        style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">Incidents</h1>
          <p className="page-subtitle">All RCA analyses — click to view causal graph and LLM report</p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={13} className={loading ? "spin" : ""} /> Refresh
          </button>
          <button className="btn btn-gradient btn-sm" onClick={() => navigate("/simulate")}>
            <Zap size={13} /> New Simulation
          </button>
        </div>
      </motion.div>

      {/* Summary Cards */}
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
        style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}
      >
        {[
          { label: "Total", value: stats.total, color: "var(--accent-indigo)", icon: <AlertTriangle size={15} /> },
          { label: "Critical", value: stats.critical, color: "var(--status-critical)", icon: <Target size={15} /> },
          { label: "Analyzing", value: stats.analyzing, color: "var(--accent-violet)", icon: <Clock size={15} /> },
          { label: "Resolved", value: stats.resolved, color: "var(--accent-emerald)", icon: <Zap size={15} /> },
        ].map(({ label, value, color, icon }) => (
          <div key={label} style={{
            padding: "1rem 1.25rem", borderRadius: "var(--radius-lg)",
            background: "var(--bg-card)", border: "1px solid var(--border)",
            backdropFilter: "blur(16px)",
            display: "flex", alignItems: "center", gap: 12,
          }}>
            <div style={{ width: 34, height: 34, borderRadius: 9, background: `${color}18`,
              display: "flex", alignItems: "center", justifyContent: "center", color, flexShrink: 0 }}>
              {icon}
            </div>
            <div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, letterSpacing: "-0.03em", color: "var(--text-primary)" }}>{value}</div>
              <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
            </div>
          </div>
        ))}
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}
        style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}
      >
        {/* Search */}
        <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
          <Search size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", pointerEvents: "none" }} />
          <input
            className="input"
            style={{ paddingLeft: "2.25rem" }}
            placeholder="Search incidents or services…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Severity filter */}
        <select className="input" style={{ width: "auto", minWidth: 140 }} value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}>
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        {/* Status filter */}
        <select className="input" style={{ width: "auto", minWidth: 140 }} value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="all">All Statuses</option>
          <option value="analyzing">Analyzing</option>
          <option value="detected">Detected</option>
          <option value="resolved">Resolved</option>
          <option value="error">Error</option>
        </select>
      </motion.div>

      {/* Table */}
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
        className="card"
        style={{ padding: 0, overflow: "hidden" }}
      >
        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}><Spinner /></div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon="🛡️"
            title={incidents.length === 0 ? "No Incidents Yet" : "No Results"}
            desc={incidents.length === 0
              ? "Go to Simulate → inject a fault → see the full RCA pipeline run."
              : "Try adjusting your search or filters."}
            action={incidents.length === 0 ? (
              <button className="btn btn-primary btn-sm" onClick={() => navigate("/simulate")}>
                <Zap size={13} /> Inject Fault
              </button>
            ) : undefined}
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ paddingLeft: "1.25rem" }}>Incident</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Root Cause</th>
                  <th>Confidence</th>
                  <th>Affected</th>
                  <th>Detected</th>
                  <th style={{ width: 36 }} />
                </tr>
              </thead>
              <tbody>
                {filtered.map((inc, i) => (
                  <motion.tr
                    key={inc.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    onClick={() => navigate(`/incidents/${inc.id}`)}
                    style={{ position: "relative" }}
                  >
                    {/* Severity accent bar */}
                    <td style={{ paddingLeft: "1.25rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div style={{
                          width: 3, height: 36, borderRadius: 99, flexShrink: 0,
                          background: inc.severity === "critical" ? "var(--status-critical)"
                            : inc.severity === "high" ? "var(--status-warning)"
                            : inc.severity === "medium" ? "var(--accent-amber)"
                            : "var(--accent-emerald)",
                        }} />
                        <div>
                          <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.875rem" }}>{inc.title}</div>
                          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontFamily: "JetBrains Mono" }}>
                            #{inc.id.slice(0, 8)}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td><StatusBadge status={inc.severity} /></td>
                    <td><StatusBadge status={inc.status} /></td>
                    <td>
                      {inc.root_cause_service ? (
                        <span style={{ fontFamily: "JetBrains Mono", fontSize: "0.8rem", color: "var(--text-primary)", fontWeight: 500 }}>
                          {inc.root_cause_service}
                        </span>
                      ) : (
                        <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                          {inc.status === "analyzing" ? "analyzing…" : "—"}
                        </span>
                      )}
                    </td>
                    <td>
                      {inc.confidence != null ? (
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <div style={{ width: 48, height: 3, background: "var(--border)", borderRadius: 99, overflow: "hidden" }}>
                            <div style={{ height: "100%", width: `${inc.confidence * 100}%`, background: "var(--accent-indigo)", borderRadius: 99 }} />
                          </div>
                          <span style={{ fontWeight: 700, color: "var(--accent-indigo)", fontSize: "0.82rem" }}>
                            {(inc.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      ) : <span style={{ color: "var(--text-muted)" }}>—</span>}
                    </td>
                    <td>
                      <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                        {inc.affected_services?.length ?? 0} services
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {formatDistanceToNow(new Date(inc.detected_at), { addSuffix: true })}
                      </span>
                    </td>
                    <td>
                      <ChevronRight size={15} color="var(--text-muted)" />
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  );
}
