import React, { useState, useEffect } from "react";
import { fetchAuditLog, type AuditEvent } from "../api/endpoints";

const OUTCOME_COLORS: Record<string, string> = {
  SUCCESS: "var(--success)",
  DENIED: "var(--danger)",
  FAILED: "var(--danger)",
};

const ACTION_ICONS: Record<string, string> = {
  "transition_action": "⇒",
  "execute_action": "▷",
  "approve_action": "✓",
  "reject_action": "✗",
  "verify_action": "◎",
  "generate_report": "📄",
  "create_incident": "⚠",
  "run_rca": "🔍",
};

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState({ incident_id: "", resource_type: "", limit: 100 });
  const [search, setSearch] = useState("");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAuditLog({
        incident_id: filter.incident_id || undefined,
        resource_type: filter.resource_type || undefined,
        limit: filter.limit,
      });
      setEvents(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  const filtered = events.filter(e =>
    !search || (
      e.actor.includes(search) ||
      e.action.includes(search) ||
      e.resource_type.includes(search) ||
      e.resource_id.includes(search) ||
      (e.incident_id || "").includes(search)
    )
  );

  return (
    <div style={{ padding: "24px", maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
          Audit History
        </h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
          Append-only security and operational audit log · {events.length} records loaded
        </p>
      </div>

      {/* Filter bar */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          flexWrap: "wrap",
          padding: "12px 16px",
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
          marginBottom: "16px",
        }}
      >
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search actor, action, resource…"
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-bright)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-primary)",
            padding: "7px 12px",
            fontSize: "13px",
            flex: "1 1 200px",
          }}
        />
        <input
          value={filter.incident_id}
          onChange={e => setFilter(f => ({ ...f, incident_id: e.target.value }))}
          placeholder="Filter incident ID…"
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-bright)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-primary)",
            padding: "7px 12px",
            fontSize: "13px",
            width: 180,
          }}
        />
        <select
          value={filter.resource_type}
          onChange={e => setFilter(f => ({ ...f, resource_type: e.target.value }))}
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-bright)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-secondary)",
            padding: "7px 12px",
            fontSize: "13px",
          }}
        >
          <option value="">All resource types</option>
          <option value="suggested_action">Suggested Actions</option>
          <option value="incident">Incidents</option>
          <option value="report">Reports</option>
        </select>
        <select
          value={filter.limit}
          onChange={e => setFilter(f => ({ ...f, limit: Number(e.target.value) }))}
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-bright)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-secondary)",
            padding: "7px 12px",
            fontSize: "13px",
          }}
        >
          <option value={50}>Last 50</option>
          <option value={100}>Last 100</option>
          <option value={250}>Last 250</option>
          <option value={500}>Last 500</option>
        </select>
        <button
          onClick={load}
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-bright)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-secondary)",
            padding: "7px 12px",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          ↺
        </button>
      </div>

      {error && (
        <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "var(--radius-md)", padding: "12px 16px", color: "var(--danger)", fontSize: "13px", marginBottom: "16px" }}>
          {error}
        </div>
      )}

      {/* Table */}
      <div
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
          overflow: "hidden",
        }}
      >
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
            <thead>
              <tr style={{ background: "var(--bg-elevated)" }}>
                {["Time", "Actor", "Action", "Resource", "Incident", "Outcome"].map(h => (
                  <th
                    key={h}
                    style={{
                      padding: "10px 14px",
                      textAlign: "left",
                      color: "var(--text-muted)",
                      fontWeight: 600,
                      fontSize: "11px",
                      letterSpacing: "0.05em",
                      textTransform: "uppercase",
                      borderBottom: "1px solid var(--border)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)" }}>
                    Loading audit records…
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)" }}>
                    No audit records found
                  </td>
                </tr>
              ) : (
                filtered.map(evt => {
                  const actionKey = Object.keys(ACTION_ICONS).find(k => evt.action.startsWith(k));
                  const icon = actionKey ? ACTION_ICONS[actionKey] : "◆";
                  const outcomeColor = OUTCOME_COLORS[evt.outcome] || "var(--text-muted)";

                  return (
                    <tr
                      key={evt.id}
                      style={{ borderBottom: "1px solid var(--border)", transition: "background 0.1s" }}
                      onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-elevated)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                    >
                      <td style={{ padding: "8px 14px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                        {new Date(evt.event_time).toLocaleString()}
                      </td>
                      <td style={{ padding: "8px 14px" }}>
                        <code style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{evt.actor}</code>
                      </td>
                      <td style={{ padding: "8px 14px", color: "var(--text-secondary)" }}>
                        <span style={{ marginRight: "6px" }}>{icon}</span>
                        {evt.action}
                      </td>
                      <td style={{ padding: "8px 14px" }}>
                        <span style={{ fontSize: "10px", color: "var(--text-muted)", background: "var(--bg-elevated)", padding: "2px 6px", borderRadius: 4, marginRight: 4 }}>
                          {evt.resource_type}
                        </span>
                        <code style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{evt.resource_id.slice(0, 16)}</code>
                      </td>
                      <td style={{ padding: "8px 14px" }}>
                        {evt.incident_id ? (
                          <code style={{ fontSize: "11px", color: "var(--primary)" }}>{evt.incident_id.slice(0, 12)}…</code>
                        ) : (
                          <span style={{ color: "var(--text-muted)" }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: "8px 14px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 600, color: outcomeColor }}>
                          {evt.outcome}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {filtered.length > 0 && (
        <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "8px", textAlign: "right" }}>
          Showing {filtered.length} of {events.length} records · Audit log is append-only and cannot be deleted
        </p>
      )}
    </div>
  );
}
