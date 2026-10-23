import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  fetchIncidentActions,
  generateActions,
  approveAction,
  executeAction,
  verifyAction,
  getReportDownloadUrl,
  fetchIncidentTimeline,
  fetchSimilarIncidents,
  type SuggestedAction,
  type TimelineEvent,
} from "../api/endpoints";

const RISK_COLORS: Record<string, string> = {
  low: "var(--success)",
  medium: "var(--warning)",
  high: "#f97316",
  critical: "var(--danger)",
};

const STATUS_COLORS: Record<string, string> = {
  PROPOSED: "var(--text-muted)",
  AWAITING_APPROVAL: "var(--warning)",
  APPROVED: "var(--accent-cyan)",
  READY_TO_EXECUTE: "var(--accent-cyan)",
  EXECUTING: "var(--primary)",
  EXECUTED: "var(--primary)",
  VERIFYING: "var(--secondary)",
  VERIFIED_SUCCESS: "var(--success)",
  VERIFICATION_FAILED: "var(--danger)",
  VERIFICATION_INCONCLUSIVE: "var(--warning)",
  EXECUTION_FAILED: "var(--danger)",
  REJECTED: "var(--danger)",
  CANCELLED: "var(--text-muted)",
  ROLLBACK_PENDING: "var(--warning)",
  ROLLING_BACK: "var(--warning)",
  ROLLED_BACK: "var(--accent)",
  MANUAL_INTERVENTION_REQUIRED: "var(--danger)",
};

const STATUS_LABELS: Record<string, string> = {
  PROPOSED: "Proposed",
  AWAITING_APPROVAL: "Awaiting Approval",
  APPROVED: "Approved",
  READY_TO_EXECUTE: "Ready to Execute",
  EXECUTING: "Executing…",
  EXECUTED: "Executed",
  VERIFYING: "Verifying…",
  VERIFIED_SUCCESS: "✓ Verified",
  VERIFICATION_FAILED: "✗ Failed",
  VERIFICATION_INCONCLUSIVE: "? Inconclusive",
  EXECUTION_FAILED: "✗ Exec Failed",
  REJECTED: "Rejected",
  CANCELLED: "Cancelled",
  ROLLBACK_PENDING: "Rollback Pending",
  ROLLING_BACK: "Rolling Back…",
  ROLLED_BACK: "Rolled Back",
  MANUAL_INTERVENTION_REQUIRED: "⚠ Manual Needed",
};

const CATEGORY_ICONS: Record<string, string> = {
  COLLECT_DIAGNOSTICS: "🔍",
  INSPECT_K8S: "☸",
  INSPECT_LOGS: "📄",
  INVESTIGATE_SATURATION: "📊",
  RESTART_WORKLOAD: "↺",
  SCALE_WORKLOAD: "⇕",
  ROLLBACK_DEPLOYMENT: "⏪",
  APPLY_CONFIG: "⚙",
  ESCALATE: "📢",
  MONITOR_ONLY: "👁",
};

export default function ActionsWorkspace() {
  const { id: incidentId } = useParams<{ id: string }>();
  const [actions, setActions] = useState<SuggestedAction[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [similar, setSimilar] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedAction, setSelectedAction] = useState<SuggestedAction | null>(null);
  const [approvalModal, setApprovalModal] = useState<{ action: SuggestedAction; intent: "APPROVED" | "REJECTED" } | null>(null);
  const [approvalReason, setApprovalReason] = useState("");
  const [operatorId, setOperatorId] = useState("operator-01");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);
  const [activeTab, setActiveTab] = useState<"actions" | "timeline" | "similar">("actions");

  const showToast = (msg: string, type: "success" | "error" = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const load = async () => {
    if (!incidentId) return;
    setLoading(true);
    setError(null);
    try {
      const [acts, events] = await Promise.all([
        fetchIncidentActions(incidentId),
        fetchIncidentTimeline(incidentId).catch(() => []),
      ]);
      setActions(acts);
      setTimeline(events);
      // Refresh selected action data
      if (selectedAction) {
        const refreshed = acts.find(a => a.id === selectedAction.id);
        if (refreshed) setSelectedAction(refreshed);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load actions");
    } finally {
      setLoading(false);
    }
  };

  const loadSimilar = async () => {
    if (!incidentId) return;
    try {
      const r = await fetchSimilarIncidents(incidentId, 5);
      setSimilar(r.similar);
    } catch {}
  };

  useEffect(() => { load(); loadSimilar(); }, [incidentId]);

  const handleGenerate = async () => {
    if (!incidentId) return;
    setGenerating(true);
    try {
      const r = await generateActions(incidentId);
      showToast(`Generated ${r.generated} action(s)`);
      await load();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "Generation failed", "error");
    } finally {
      setGenerating(false);
    }
  };

  const handleApproveSubmit = async () => {
    if (!approvalModal) return;
    try {
      await approveAction(approvalModal.action.id, operatorId, approvalModal.intent, approvalReason);
      showToast(`Action ${approvalModal.intent.toLowerCase()} by ${operatorId}`);
      setApprovalModal(null);
      setApprovalReason("");
      await load();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "Approval failed", "error");
    }
  };

  const handleExecute = async (action: SuggestedAction) => {
    try {
      const r = await executeAction(action.id, operatorId);
      showToast(`Executed — outcome: ${r.outcome}${r.simulated ? " (simulated)" : ""}`);
      await load();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "Execution failed", "error");
    }
  };

  const handleVerify = async (action: SuggestedAction) => {
    try {
      const r = await verifyAction(action.id);
      showToast(`Verification: ${r.outcome}`);
      await load();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "Verification failed", "error");
    }
  };

  const downloadReport = (fmt: string) => {
    if (!incidentId) return;
    window.open(getReportDownloadUrl(incidentId, fmt), "_blank");
  };

  return (
    <div style={{ display: "flex", height: "100%", gap: 0 }}>
      {/* Left panel — action list */}
      <div
        style={{
          width: 340,
          flexShrink: 0,
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          height: "100%",
        }}
      >
        {/* Header */}
        <div style={{ padding: "16px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <div>
              <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>
                Recovery Actions
              </h2>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                {actions.length} action{actions.length !== 1 ? "s" : ""} • Incident{" "}
                <code style={{ fontSize: "11px" }}>{incidentId}</code>
              </p>
            </div>
            <button
              onClick={handleGenerate}
              disabled={generating}
              style={{
                background: "var(--primary)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                color: "#fff",
                padding: "6px 12px",
                fontSize: "12px",
                cursor: generating ? "not-allowed" : "pointer",
                opacity: generating ? 0.7 : 1,
                fontWeight: 500,
              }}
            >
              {generating ? "Generating…" : "⊕ Generate"}
            </button>
          </div>

          {/* Operator ID */}
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Operator:</span>
            <input
              value={operatorId}
              onChange={e => setOperatorId(e.target.value)}
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 4,
                color: "var(--text-primary)",
                padding: "3px 8px",
                fontSize: "11px",
                flex: 1,
              }}
              placeholder="operator-id"
            />
          </div>
        </div>

        {/* Tab bar */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--border)" }}>
          {(["actions", "timeline", "similar"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                flex: 1,
                padding: "8px",
                background: "none",
                border: "none",
                borderBottom: activeTab === tab ? "2px solid var(--primary)" : "2px solid transparent",
                color: activeTab === tab ? "var(--text-primary)" : "var(--text-muted)",
                fontSize: "12px",
                fontWeight: activeTab === tab ? 600 : 400,
                cursor: "pointer",
                textTransform: "capitalize",
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {loading ? (
            <div style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
              Loading…
            </div>
          ) : error ? (
            <div style={{ padding: "16px" }}>
              <div style={{ color: "var(--danger)", fontSize: "13px", marginBottom: "8px" }}>{error}</div>
              <button onClick={load} style={{ fontSize: "12px", color: "var(--primary)", background: "none", border: "none", cursor: "pointer" }}>
                Retry
              </button>
            </div>
          ) : activeTab === "actions" ? (
            actions.length === 0 ? (
              <div style={{ padding: "32px 16px", textAlign: "center" }}>
                <div style={{ fontSize: "24px", marginBottom: "8px" }}>⚙</div>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                  No actions generated yet
                </p>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Complete the RCA pipeline, then click Generate
                </p>
              </div>
            ) : (
              actions.map(action => (
                <ActionCard
                  key={action.id}
                  action={action}
                  selected={selectedAction?.id === action.id}
                  onClick={() => setSelectedAction(action)}
                />
              ))
            )
          ) : activeTab === "timeline" ? (
            timeline.length === 0 ? (
              <div style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)", fontSize: "12px" }}>
                No timeline events
              </div>
            ) : (
              <div style={{ padding: "8px 0" }}>
                {timeline.map(evt => (
                  <TimelineItem key={evt.id} event={evt} />
                ))}
              </div>
            )
          ) : (
            <div style={{ padding: "8px 0" }}>
              {similar.length === 0 ? (
                <div style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)", fontSize: "12px" }}>
                  No similar incidents found
                </div>
              ) : (
                similar.map((s, i) => (
                  <SimilarIncidentCard key={i} incident={s} />
                ))
              )}
            </div>
          )}
        </div>

        {/* Downloads */}
        <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
          <p style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "8px" }}>Download Report</p>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {["json", "markdown", "html", "pdf", "csv", "zip"].map(fmt => (
              <button
                key={fmt}
                onClick={() => downloadReport(fmt)}
                style={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  borderRadius: 4,
                  color: "var(--text-secondary)",
                  padding: "4px 8px",
                  fontSize: "11px",
                  cursor: "pointer",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  transition: "border-color 0.15s",
                }}
              >
                {fmt}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — action detail */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {selectedAction ? (
          <ActionDetail
            action={selectedAction}
            onApprove={(intent) => setApprovalModal({ action: selectedAction, intent })}
            onExecute={() => handleExecute(selectedAction)}
            onVerify={() => handleVerify(selectedAction)}
            operatorId={operatorId}
          />
        ) : (
          <div
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-muted)",
              gap: "12px",
            }}
          >
            <div style={{ fontSize: "48px", opacity: 0.3 }}>▷</div>
            <p style={{ fontSize: "14px" }}>Select an action to view details</p>
          </div>
        )}
      </div>

      {/* Approval modal */}
      {approvalModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setApprovalModal(null)}
        >
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-bright)",
              borderRadius: "var(--radius-lg)",
              padding: "24px",
              width: 420,
              maxWidth: "90vw",
            }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
              {approvalModal.intent === "APPROVED" ? "✓ Approve Action" : "✗ Reject Action"}
            </h3>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "16px" }}>
              {approvalModal.action.title}
            </p>

            {/* Risk warning for medium/high */}
            {approvalModal.intent === "APPROVED" && approvalModal.action.risk_level !== "low" && (
              <div
                style={{
                  background: "rgba(245,158,11,0.1)",
                  border: "1px solid rgba(245,158,11,0.3)",
                  borderRadius: "var(--radius-sm)",
                  padding: "10px 12px",
                  marginBottom: "16px",
                  fontSize: "12px",
                  color: "var(--warning)",
                }}
              >
                ⚠ This is a <strong>{approvalModal.action.risk_level.toUpperCase()}</strong> risk action.{" "}
                {approvalModal.action.risk_level === "high" && "Ensure rollback plan is available."}
              </div>
            )}

            <div style={{ marginBottom: "12px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
                Target
              </label>
              <code style={{ fontSize: "12px", color: "var(--accent-cyan)" }}>
                {approvalModal.action.target_service || "N/A"} · {approvalModal.action.target_namespace}
              </code>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
                Reason (optional)
              </label>
              <textarea
                value={approvalReason}
                onChange={e => setApprovalReason(e.target.value)}
                placeholder="Add context for the audit log…"
                rows={3}
                style={{
                  width: "100%",
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border-bright)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  padding: "8px 10px",
                  fontSize: "12px",
                  resize: "vertical",
                }}
              />
            </div>

            <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
              <button
                onClick={() => setApprovalModal(null)}
                style={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-secondary)",
                  padding: "8px 16px",
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleApproveSubmit}
                style={{
                  background: approvalModal.intent === "APPROVED" ? "var(--success)" : "var(--danger)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  color: "#fff",
                  padding: "8px 16px",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {approvalModal.intent === "APPROVED" ? "Confirm Approval" : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            background: toast.type === "success" ? "var(--bg-elevated)" : "rgba(239,68,68,0.15)",
            border: `1px solid ${toast.type === "success" ? "var(--success)" : "var(--danger)"}`,
            borderRadius: "var(--radius-md)",
            padding: "12px 16px",
            fontSize: "13px",
            color: toast.type === "success" ? "var(--success)" : "var(--danger)",
            zIndex: 2000,
            maxWidth: 360,
            animation: "fadeIn 0.2s ease",
          }}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}

function ActionCard({ action, selected, onClick }: {
  action: SuggestedAction;
  selected: boolean;
  onClick: () => void;
}) {
  const riskColor = RISK_COLORS[action.risk_level] || "var(--text-muted)";
  const statusColor = STATUS_COLORS[action.status] || "var(--text-muted)";
  const icon = CATEGORY_ICONS[action.category] || "⚙";

  return (
    <div
      onClick={onClick}
      style={{
        padding: "12px 16px",
        borderBottom: "1px solid var(--border)",
        cursor: "pointer",
        background: selected ? "var(--bg-elevated)" : "transparent",
        borderLeft: selected ? "3px solid var(--primary)" : "3px solid transparent",
        transition: "all 0.15s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: "var(--radius-sm)",
            background: "var(--bg-elevated)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "14px",
            flexShrink: 0,
          }}
        >
          {icon}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.3, marginBottom: "4px" }}>
            {action.title}
          </div>
          <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontSize: "10px", color: riskColor, fontWeight: 600, letterSpacing: "0.05em" }}>
              {action.risk_level.toUpperCase()}
            </span>
            <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>·</span>
            <span style={{ fontSize: "10px", color: statusColor, fontWeight: 500 }}>
              {STATUS_LABELS[action.status] || action.status}
            </span>
          </div>
          {action.target_service && (
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
              → {action.target_service}
            </div>
          )}
        </div>
        <div style={{ fontSize: "10px", color: "var(--text-muted)", flexShrink: 0 }}>
          #{action.priority_rank}
        </div>
      </div>
    </div>
  );
}

function ActionDetail({ action, onApprove, onExecute, onVerify, operatorId }: {
  action: SuggestedAction;
  onApprove: (intent: "APPROVED" | "REJECTED") => void;
  onExecute: () => void;
  onVerify: () => void;
  operatorId: string;
}) {
  const riskColor = RISK_COLORS[action.risk_level] || "var(--text-muted)";
  const statusColor = STATUS_COLORS[action.status] || "var(--text-muted)";

  const canApprove = ["PROPOSED", "AWAITING_APPROVAL"].includes(action.status);
  const canExecute = ["APPROVED", "READY_TO_EXECUTE"].includes(action.status);
  const canVerify = action.status === "EXECUTED";

  return (
    <div style={{ padding: "24px", maxWidth: 760 }}>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px", marginBottom: "8px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.3 }}>
            {CATEGORY_ICONS[action.category] || "⚙"} {action.title}
          </h2>
          <StatusBadge status={action.status} />
        </div>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ fontSize: "11px", color: riskColor, fontWeight: 600 }}>
            ● {action.risk_level.toUpperCase()} RISK
          </span>
          {action.requires_approval && (
            <span style={{ fontSize: "11px", color: "var(--text-muted)", background: "var(--bg-elevated)", padding: "2px 8px", borderRadius: 20 }}>
              Requires Approval
            </span>
          )}
          {action.simulated && (
            <span style={{ fontSize: "11px", color: "var(--warning)", background: "rgba(245,158,11,0.1)", padding: "2px 8px", borderRadius: 20, border: "1px solid rgba(245,158,11,0.3)" }}>
              SIMULATED
            </span>
          )}
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            {action.category}
          </span>
          <code style={{ fontSize: "11px", color: "var(--text-muted)" }}>{action.id}</code>
        </div>
      </div>

      {/* Actions toolbar */}
      {(canApprove || canExecute || canVerify) && (
        <div
          style={{
            display: "flex",
            gap: "8px",
            padding: "12px 16px",
            background: "var(--bg-elevated)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border)",
            marginBottom: "20px",
            flexWrap: "wrap",
          }}
        >
          {canApprove && (
            <>
              <ActionBtn
                label="✓ Approve"
                color="var(--success)"
                onClick={() => onApprove("APPROVED")}
              />
              <ActionBtn
                label="✗ Reject"
                color="var(--danger)"
                variant="outline"
                onClick={() => onApprove("REJECTED")}
              />
            </>
          )}
          {canExecute && (
            <ActionBtn
              label="▷ Execute"
              color="var(--primary)"
              onClick={onExecute}
            />
          )}
          {canVerify && (
            <ActionBtn
              label="◎ Verify"
              color="var(--secondary)"
              onClick={onVerify}
            />
          )}
        </div>
      )}

      {/* Sections */}
      <Section title="Description">
        <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6 }}>{action.description}</p>
      </Section>

      <Section title="Reason & Evidence">
        <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "12px" }}>{action.reason}</p>
        {action.evidence_refs && action.evidence_refs.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {action.evidence_refs.map((ref, i) => (
              <div
                key={i}
                style={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  padding: "8px 12px",
                  fontSize: "12px",
                }}
              >
                <span style={{ color: "var(--accent-cyan)", fontWeight: 500 }}>[{ref.type}]</span>{" "}
                <span style={{ color: "var(--text-secondary)" }}>{ref.description || ref.ref}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <Section title="Target">
          <KV label="Service" value={action.target_service || "N/A"} mono />
          <KV label="Namespace" value={action.target_namespace} mono />
          <KV label="Resource" value={action.target_resource_type || "N/A"} />
          <KV label="Handler" value={action.action_handler || "N/A"} mono />
          <KV label="Timeout" value={`${action.timeout_seconds}s`} />
        </Section>

        <Section title="Risk & Safety">
          <KV label="Risk Level" value={action.risk_level.toUpperCase()} valueColor={riskColor} />
          <KV label="Confidence" value={`${(action.confidence_score * 100).toFixed(0)}%`} />
          <KV label="Priority" value={`#${action.priority_rank}`} />
          <KV label="Proposed By" value={action.proposed_by} />
          <KV label="Simulation" value={action.simulated ? "Yes — no real changes" : "No"} />
        </Section>
      </div>

      {action.preconditions && action.preconditions.length > 0 && (
        <Section title="Preconditions">
          <ul style={{ paddingLeft: "16px" }}>
            {action.preconditions.map((p, i) => (
              <li key={i} style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>{p}</li>
            ))}
          </ul>
        </Section>
      )}

      {action.expected_outcome && (
        <Section title="Expected Outcome">
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6 }}>{action.expected_outcome}</p>
        </Section>
      )}

      {action.potential_side_effects && action.potential_side_effects.length > 0 && (
        <Section title="Potential Side Effects">
          <ul style={{ paddingLeft: "16px" }}>
            {action.potential_side_effects.map((s, i) => (
              <li key={i} style={{ fontSize: "12px", color: "var(--warning)", marginBottom: "4px" }}>⚠ {s}</li>
            ))}
          </ul>
        </Section>
      )}

      {action.rollback_plan && (
        <Section title="Rollback Plan">
          <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.6, fontFamily: "var(--font-mono)" }}>
            {action.rollback_plan}
          </p>
        </Section>
      )}

      {/* Approval record */}
      {action.approval && (
        <Section title="Approval Record">
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <span
              style={{
                fontSize: "12px",
                fontWeight: 700,
                color: action.approval.decision === "APPROVED" ? "var(--success)" : "var(--danger)",
              }}
            >
              {action.approval.decision}
            </span>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>by</span>
            <code style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{action.approval.decided_by}</code>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {new Date(action.approval.decided_at).toLocaleString()}
            </span>
          </div>
          {action.approval.reason && (
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px" }}>
              {action.approval.reason}
            </p>
          )}
        </Section>
      )}

      {/* Execution record */}
      {action.execution && (
        <Section title="Execution Record">
          <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "8px" }}>
            <KV label="Outcome" value={action.execution.outcome} valueColor={action.execution.outcome === "SUCCESS" ? "var(--success)" : "var(--danger)"} />
            <KV label="Duration" value={action.execution.duration_ms ? `${action.execution.duration_ms.toFixed(0)}ms` : "N/A"} />
            <KV label="Handler" value={action.execution.handler_name || "N/A"} mono />
            <KV label="Simulated" value={action.execution.simulated ? "Yes" : "No"} />
          </div>
          {action.execution.error_message && (
            <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "var(--radius-sm)", padding: "8px 12px", fontSize: "12px", color: "var(--danger)" }}>
              {action.execution.error_message}
            </div>
          )}
        </Section>
      )}

      {/* Verification */}
      {action.verification && (
        <Section title="Verification Result">
          <VerificationDisplay v={action.verification} />
        </Section>
      )}
    </div>
  );
}

function VerificationDisplay({ v }: { v: NonNullable<SuggestedAction["verification"]> }) {
  const outcomeColors: Record<string, string> = {
    VERIFIED_SUCCESS: "var(--success)",
    VERIFICATION_FAILED: "var(--danger)",
    VERIFICATION_INCONCLUSIVE: "var(--warning)",
  };
  const color = outcomeColors[v.outcome] || "var(--text-muted)";

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
        <span style={{ fontSize: "14px", fontWeight: 700, color }}>{v.outcome}</span>
        {v.data_freshness_seconds !== undefined && (
          <span style={{ fontSize: "11px", color: v.data_freshness_seconds > 300 ? "var(--danger)" : "var(--text-muted)" }}>
            Data age: {v.data_freshness_seconds.toFixed(0)}s
          </span>
        )}
      </div>

      {v.summary && (
        <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "12px", lineHeight: 1.5 }}>
          {v.summary}
        </p>
      )}

      {v.missing_metrics && v.missing_metrics.length > 0 && (
        <div style={{ fontSize: "12px", color: "var(--warning)", marginBottom: "10px" }}>
          ⚠ Missing metrics: {v.missing_metrics.join(", ")}
        </div>
      )}

      {v.metric_comparison && v.metric_comparison.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
            <thead>
              <tr>
                {["Metric", "Baseline", "Post-Action", "Change", "Status"].map(h => (
                  <th key={h} style={{ padding: "6px 10px", textAlign: "left", color: "var(--text-muted)", fontWeight: 500, borderBottom: "1px solid var(--border)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {v.metric_comparison.map((m, i) => {
                const interpretColor = m.interpretation === "improved" ? "var(--success)"
                  : m.interpretation === "regressed" ? "var(--danger)"
                  : "var(--text-muted)";
                return (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "6px 10px", color: "var(--text-secondary)", fontWeight: 500 }}>{m.metric}</td>
                    <td style={{ padding: "6px 10px", color: "var(--text-muted)" }}>{m.baseline ?? "N/A"} {m.unit}</td>
                    <td style={{ padding: "6px 10px", color: "var(--text-secondary)" }}>{m.post ?? "N/A"} {m.unit}</td>
                    <td style={{ padding: "6px 10px", color: m.pct_change && m.pct_change < 0 ? "var(--success)" : "var(--warning)" }}>
                      {m.pct_change != null ? `${m.pct_change > 0 ? "+" : ""}${m.pct_change.toFixed(1)}%` : "N/A"}
                    </td>
                    <td style={{ padding: "6px 10px", color: interpretColor, fontWeight: 500 }}>
                      {m.interpretation}
                      {!m.data_fresh && " ⚠"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {v.next_step_recommendation && (
        <p style={{ fontSize: "12px", color: "var(--accent-cyan)", marginTop: "10px" }}>
          → {v.next_step_recommendation}
        </p>
      )}
    </div>
  );
}

function TimelineItem({ event }: { event: TimelineEvent }) {
  const typeColors: Record<string, string> = {
    METRIC_ANOMALY: "var(--danger)",
    RCA_STARTED: "var(--warning)",
    RCA_COMPLETED: "var(--primary)",
    ACTION_PROPOSED: "var(--accent-cyan)",
    ACTION_APPROVED: "var(--success)",
    ACTION_REJECTED: "var(--danger)",
    ACTION_EXECUTED: "var(--primary)",
    VERIFICATION_COMPLETED: "var(--secondary)",
    STATUS_CHANGED: "var(--text-muted)",
  };
  const color = typeColors[event.event_type] || "var(--text-muted)";

  return (
    <div style={{ display: "flex", gap: "10px", padding: "8px 16px", alignItems: "flex-start" }}>
      <div style={{ width: 6, height: 6, borderRadius: "50%", background: color, marginTop: "5px", flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.3 }}>{event.title}</div>
        <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>
          {new Date(event.event_time).toLocaleString()} · {event.actor}
        </div>
      </div>
    </div>
  );
}

function SimilarIncidentCard({ incident }: { incident: any }) {
  return (
    <Link
      to={`/incidents/${incident.incident_id}`}
      style={{ display: "block", padding: "10px 16px", borderBottom: "1px solid var(--border)", textDecoration: "none" }}
    >
      <div style={{ fontSize: "12px", fontWeight: 500, color: "var(--text-secondary)", marginBottom: "2px" }}>
        {incident.title}
      </div>
      <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{incident.similarity_reason}</div>
      <div style={{ fontSize: "10px", color: "var(--primary)", marginTop: "2px" }}>
        Score: {(incident.similarity_score * 100).toFixed(0)}%
      </div>
    </Link>
  );
}

// ── Shared components ────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "20px" }}>
      <h3 style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "10px" }}>
        {title}
      </h3>
      {children}
    </div>
  );
}

function KV({ label, value, mono, valueColor }: { label: string; value: string; mono?: boolean; valueColor?: string }) {
  return (
    <div style={{ display: "flex", gap: "8px", marginBottom: "4px", alignItems: "baseline" }}>
      <span style={{ fontSize: "11px", color: "var(--text-muted)", minWidth: 80, flexShrink: 0 }}>{label}</span>
      <span style={{ fontSize: "12px", color: valueColor || "var(--text-secondary)", fontFamily: mono ? "var(--font-mono)" : undefined }}>
        {value}
      </span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || "var(--text-muted)";
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        padding: "3px 10px",
        borderRadius: 20,
        border: `1px solid ${color}33`,
        background: `${color}11`,
        fontSize: "11px",
        color,
        fontWeight: 600,
        whiteSpace: "nowrap",
        flexShrink: 0,
      }}
    >
      <div style={{ width: 5, height: 5, borderRadius: "50%", background: color }} />
      {STATUS_LABELS[status] || status}
    </div>
  );
}

function ActionBtn({ label, color, variant, onClick }: {
  label: string;
  color: string;
  variant?: "outline";
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        background: variant === "outline" ? "transparent" : color,
        border: `1px solid ${color}`,
        borderRadius: "var(--radius-sm)",
        color: variant === "outline" ? color : "#fff",
        padding: "7px 14px",
        fontSize: "12px",
        fontWeight: 600,
        cursor: "pointer",
        transition: "opacity 0.15s",
      }}
    >
      {label}
    </button>
  );
}
