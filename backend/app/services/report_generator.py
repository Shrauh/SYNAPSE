"""
SYNAPSE Report Generator — Multi-format incident report production.

Generates from persisted database records only. The web view and
downloaded reports use identical canonical data. Every report has
a stable ID, version, generation timestamp, and data references.

Supported formats: json | markdown | html | pdf | csv | zip

PDF requires the 'reportlab' package. If unavailable, a human-readable
fallback HTML is returned instead with a clear notice.

Secrets are never included in any output. All artifact content is
derived from the incident, RCA, actions, verifications, and audit records.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import textwrap
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.models import (
    ActionApproval,
    ActionExecution,
    AuditEvent,
    Incident,
    IncidentEvent,
    RCAResult,
    ReportArtifact,
    SuggestedAction,
    VerificationRun,
    _gen_report_id,
)

logger = logging.getLogger("synapse.report_generator")

# ─────────────────────────────────────────────────────────────────────────────
# Data Collection
# ─────────────────────────────────────────────────────────────────────────────

async def _collect_incident_data(db: AsyncSession, incident_id: str) -> Dict[str, Any]:
    """Gather all persisted data for an incident from the database."""
    # Incident
    r = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = r.scalar_one_or_none()
    if not incident:
        raise ValueError(f"Incident {incident_id!r} not found")

    # RCA result (latest)
    r = await db.execute(
        select(RCAResult).where(RCAResult.incident_id == incident_id)
        .order_by(desc(RCAResult.id))
    )
    rca = r.scalars().first()

    # Suggested actions
    r = await db.execute(
        select(SuggestedAction).where(SuggestedAction.incident_id == incident_id)
        .order_by(SuggestedAction.priority_rank)
    )
    actions = list(r.scalars().all())

    # Approvals
    action_ids = [a.id for a in actions]
    approvals = []
    executions = []
    verifications = []
    if action_ids:
        r = await db.execute(
            select(ActionApproval).where(ActionApproval.action_id.in_(action_ids))
        )
        approvals = list(r.scalars().all())
        r = await db.execute(
            select(ActionExecution).where(ActionExecution.action_id.in_(action_ids))
        )
        executions = list(r.scalars().all())
        r = await db.execute(
            select(VerificationRun).where(VerificationRun.action_id.in_(action_ids))
        )
        verifications = list(r.scalars().all())

    # Timeline events
    r = await db.execute(
        select(IncidentEvent).where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.event_time)
    )
    events = list(r.scalars().all())

    return {
        "incident": incident,
        "rca": rca,
        "actions": actions,
        "approvals": approvals,
        "executions": executions,
        "verifications": verifications,
        "events": events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# JSON export (canonical)
# ─────────────────────────────────────────────────────────────────────────────

def _serialize_dt(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def build_incident_json(data: Dict[str, Any], report_id: str) -> Dict[str, Any]:
    inc: Incident = data["incident"]
    rca: Optional[RCAResult] = data["rca"]

    def action_dict(a: SuggestedAction) -> Dict:
        approval = next((x for x in data["approvals"] if x.action_id == a.id), None)
        execution = next((x for x in data["executions"] if x.action_id == a.id), None)
        verification = next((x for x in data["verifications"] if x.action_id == a.id), None)
        return {
            "id": a.id,
            "title": a.title,
            "category": a.category,
            "description": a.description,
            "reason": a.reason,
            "target_service": a.target_service,
            "risk_level": a.risk_level,
            "requires_approval": bool(a.requires_approval),
            "status": a.status,
            "confidence_score": a.confidence_score,
            "priority_rank": a.priority_rank,
            "expected_outcome": a.expected_outcome,
            "preconditions": a.preconditions,
            "potential_side_effects": a.potential_side_effects,
            "evidence_refs": a.evidence_refs,
            "rollback_plan": a.rollback_plan,
            "simulated": bool(a.simulated),
            "created_at": _serialize_dt(a.created_at),
            "updated_at": _serialize_dt(a.updated_at),
            "approval": {
                "decision": approval.decision,
                "decided_by": approval.decided_by,
                "reason": approval.reason,
                "decided_at": _serialize_dt(approval.decided_at),
            } if approval else None,
            "execution": {
                "outcome": execution.outcome,
                "handler": execution.handler_name,
                "started_at": _serialize_dt(execution.started_at),
                "completed_at": _serialize_dt(execution.completed_at),
                "duration_ms": execution.duration_ms,
                "simulated": bool(execution.simulated),
                # NOTE: stdout/stderr omitted here (may contain sensitive info)
                # Use /actions/{id}/log for full execution log
            } if execution else None,
            "verification": {
                "outcome": verification.outcome,
                "summary": verification.summary,
                "metric_comparison": verification.metric_comparison,
                "missing_metrics": verification.missing_metrics,
                "data_freshness_seconds": verification.data_freshness_seconds,
                "next_step_recommendation": verification.next_step_recommendation,
            } if verification else None,
        }

    return {
        "report_metadata": {
            "report_id": report_id,
            "incident_id": inc.id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "SYNAPSE v1.0.0",
            "format": "json",
            "note": "Facts are from persisted SYNAPSE pipeline records. Model-generated fields are labeled.",
        },
        "incident": {
            "id": inc.id,
            "title": inc.title,
            "description": inc.description,
            "status": inc.status,
            "severity": inc.severity,
            "root_cause_service": inc.root_cause_service,
            "confidence": inc.confidence,
            "fault_type": inc.fault_type,
            "affected_services": inc.affected_services,
            "detected_at": _serialize_dt(inc.detected_at),
            "resolved_at": _serialize_dt(inc.resolved_at),
            "anomaly_scores": inc.anomaly_scores,
        },
        "root_cause_analysis": {
            "root_cause_service": rca.root_cause_service if rca else None,
            "confidence": rca.confidence if rca else None,
            "fault_type": rca.fault_type if rca else None,
            "explanation": rca.explanation if rca else None,
            # Label: model-generated hypothesis, not proven fact
            "explanation_source": "LLM-generated hypothesis based on anomaly scores and causal graph",
            "propagation_chain": rca.propagation_chain if rca else None,
            "metric_deltas": rca.metric_deltas if rca else None,
            "causal_graph": rca.causal_graph if rca else None,
            "model_info": rca.model_info if rca else None,
            "created_at": _serialize_dt(rca.created_at) if rca else None,
        },
        "suggested_actions": [action_dict(a) for a in data["actions"]],
        "timeline": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_time": _serialize_dt(e.event_time),
                "actor": e.actor,
                "title": e.title,
                "detail": e.detail,
                "metadata": e.event_metadata,
            }
            for e in data["events"]
        ],
        "simulation_note": (
            "This incident was created in simulation mode. All execution records "
            "are clearly labeled as simulated and did not affect production resources."
            if any(a.simulated for a in data["actions"]) else None
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Markdown report
# ─────────────────────────────────────────────────────────────────────────────

def build_markdown_report(data: Dict[str, Any], report_id: str) -> str:
    inc: Incident = data["incident"]
    rca: Optional[RCAResult] = data["rca"]
    actions: List[SuggestedAction] = data["actions"]

    def fmt_dt(dt) -> str:
        if dt is None:
            return "N/A"
        if isinstance(dt, str):
            return dt
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
        inc.severity, "⚪"
    )
    status_emoji = {"resolved": "✅", "analyzing": "🔄", "detected": "⚠️"}.get(inc.status, "❓")

    lines = [
        f"# SYNAPSE Incident Report",
        f"",
        f"**Report ID:** `{report_id}`  ",
        f"**Incident ID:** `{inc.id}`  ",
        f"**Generated:** {fmt_dt(datetime.now(timezone.utc))}  ",
        f"**Generator:** SYNAPSE v1.0.0",
        f"",
        f"---",
        f"",
        f"## Incident Summary",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Title | {inc.title} |",
        f"| Status | {status_emoji} {inc.status.upper()} |",
        f"| Severity | {severity_emoji} {inc.severity.upper()} |",
        f"| Detected | {fmt_dt(inc.detected_at)} |",
        f"| Resolved | {fmt_dt(inc.resolved_at)} |",
        f"| Root Cause Service | {inc.root_cause_service or 'Unknown'} |",
        f"| Confidence | {f'{inc.confidence:.0%}' if inc.confidence else 'N/A'} |",
        f"| Affected Services | {', '.join(inc.affected_services or [])} |",
        f"",
    ]

    # RCA Section
    lines += [f"## Root Cause Analysis", f""]
    if rca:
        lines += [
            f"> ⚠️ **Note:** The explanation below is a model-generated hypothesis based on "
            f"anomaly scores and causal graph analysis. It is not a proven causal statement.",
            f"",
            f"**Root Cause Service:** `{rca.root_cause_service}`  ",
            f"**Confidence:** {rca.confidence:.0%}  ",
            f"**Fault Type:** {rca.fault_type or 'Unknown'}  ",
            f"",
            f"### Explanation",
            f"",
            rca.explanation or "_No explanation generated._",
            f"",
            f"**Propagation Chain:** {rca.propagation_chain or 'N/A'}",
            f"",
        ]
        if rca.metric_deltas:
            lines += [f"### Metric Deltas", f""]
            for svc, deltas in (rca.metric_deltas or {}).items():
                lines.append(f"**{svc}:**")
                for metric, val in (deltas if isinstance(deltas, dict) else {}).items():
                    lines.append(f"  - {metric}: {val}")
            lines.append("")
    else:
        lines += [f"_RCA pipeline has not completed for this incident._", f""]

    # Actions Section
    lines += [f"## Suggested Actions", f""]
    if actions:
        for i, action in enumerate(actions, 1):
            approval = next((x for x in data["approvals"] if x.action_id == action.id), None)
            execution = next((x for x in data["executions"] if x.action_id == action.id), None)
            verification = next((x for x in data["verifications"] if x.action_id == action.id), None)

            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(
                action.risk_level, "⚪"
            )
            lines += [
                f"### Action {i}: {action.title}",
                f"",
                f"- **ID:** `{action.id}`",
                f"- **Category:** {action.category}",
                f"- **Risk:** {risk_emoji} {action.risk_level.upper()}",
                f"- **Status:** `{action.status}`",
                f"- **Target:** {action.target_service or 'N/A'}",
                f"",
                f"**Description:** {action.description}",
                f"",
                f"**Reason:** {action.reason}",
                f"",
            ]
            if action.preconditions:
                lines += [f"**Preconditions:**"]
                for p in action.preconditions:
                    lines.append(f"  - {p}")
                lines.append("")

            if action.expected_outcome:
                lines.append(f"**Expected Outcome:** {action.expected_outcome}")
                lines.append("")

            if approval:
                lines += [
                    f"**Approval:** {approval.decision} by `{approval.decided_by}` at {fmt_dt(approval.decided_at)}",
                    f"  - Reason: {approval.reason or 'N/A'}",
                    f"",
                ]

            if execution:
                sim_label = " *(simulated)*" if execution.simulated else ""
                lines += [
                    f"**Execution{sim_label}:** {execution.outcome}",
                    f"  - Duration: {execution.duration_ms:.0f}ms" if execution.duration_ms else "",
                    f"  - Handler: `{execution.handler_name}`",
                    f"",
                ]

            if verification:
                voutcome_emoji = {"VERIFIED_SUCCESS": "✅", "VERIFICATION_FAILED": "❌",
                                   "VERIFICATION_INCONCLUSIVE": "❓"}.get(verification.outcome, "⚪")
                lines += [
                    f"**Verification:** {voutcome_emoji} {verification.outcome}",
                    f"  - {verification.summary or 'No summary.'}",
                ]
                if verification.metric_comparison:
                    lines += [f"", f"  | Metric | Baseline | Post | Change | Interpretation |",
                               f"  |--------|---------|------|--------|----------------|"]
                    for m in verification.metric_comparison:
                        pct = f"{m.get('pct_change', 0):+.1f}%" if m.get("pct_change") is not None else "N/A"
                        lines.append(
                            f"  | {m['metric']} | {m.get('baseline','N/A')} | {m.get('post','N/A')} | {pct} | {m.get('interpretation','N/A')} |"
                        )
                lines += [f"", f"  **Next step:** {verification.next_step_recommendation or 'N/A'}", f""]
    else:
        lines += [f"_No suggested actions generated for this incident._", f""]

    # Timeline
    lines += [f"## Incident Timeline", f""]
    if data["events"]:
        for evt in data["events"]:
            lines.append(f"- **{fmt_dt(evt.event_time)}** [{evt.event_type}] {evt.title}")
    else:
        lines.append("_No timeline events recorded._")

    lines += [
        f"",
        f"---",
        f"",
        f"*Generated by SYNAPSE AIOps Platform. Model-generated content is labeled as hypothesis.*  ",
        f"*Facts are sourced from persisted database records — incident ID `{inc.id}`.*",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# HTML report (self-contained)
# ─────────────────────────────────────────────────────────────────────────────

def build_html_report(data: Dict[str, Any], report_id: str) -> str:
    md_content = build_markdown_report(data, report_id)
    # Convert simple markdown to HTML (no external dependencies needed)
    import html as html_lib
    inc: Incident = data["incident"]

    # Simple conversion: wrap in styled HTML
    body_lines = []
    for line in md_content.split("\n"):
        esc = html_lib.escape(line)
        if line.startswith("# "):
            body_lines.append(f"<h1>{html_lib.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body_lines.append(f"<h2>{html_lib.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            body_lines.append(f"<h3>{html_lib.escape(line[4:])}</h3>")
        elif line.startswith("---"):
            body_lines.append("<hr/>")
        elif line.startswith("- "):
            body_lines.append(f"<li>{esc[2:]}</li>")
        elif line.startswith("> "):
            body_lines.append(f"<blockquote>{esc[2:]}</blockquote>")
        elif line.strip() == "":
            body_lines.append("<br/>")
        else:
            # Bold text
            import re
            esc = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', esc)
            esc = re.sub(r'`(.+?)`', r'<code>\1</code>', esc)
            body_lines.append(f"<p>{esc}</p>")

    body_html = "\n".join(body_lines)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>SYNAPSE Incident Report — {inc.id}</title>
<style>
  :root {{
    --bg: #0f172a; --surface: #1e293b; --border: #334155;
    --text: #e2e8f0; --muted: #94a3b8; --accent: #3b82f6;
    --green: #22c55e; --yellow: #eab308; --red: #ef4444;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif;
         line-height: 1.6; padding: 2rem; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  .header {{ background: var(--surface); border: 1px solid var(--border);
             border-radius: 8px; padding: 2rem; margin-bottom: 2rem; }}
  .header h1 {{ color: var(--accent); font-size: 1.75rem; margin-bottom: 0.5rem; }}
  .header p {{ color: var(--muted); font-size: 0.875rem; }}
  h1 {{ color: var(--accent); margin: 2rem 0 1rem; font-size: 1.75rem; }}
  h2 {{ color: #7dd3fc; margin: 1.5rem 0 0.75rem; font-size: 1.25rem;
        border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
  h3 {{ color: #93c5fd; margin: 1rem 0 0.5rem; font-size: 1.1rem; }}
  p {{ margin: 0.5rem 0; }}
  li {{ margin: 0.25rem 0 0.25rem 1.5rem; }}
  code {{ background: #1e293b; border: 1px solid var(--border); border-radius: 4px;
          padding: 0.1rem 0.3rem; font-size: 0.875rem; color: #67e8f9; }}
  blockquote {{ border-left: 4px solid var(--yellow); padding: 0.75rem 1rem;
               background: rgba(234,179,8,0.1); border-radius: 0 4px 4px 0; margin: 1rem 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
  th, td {{ border: 1px solid var(--border); padding: 0.5rem 0.75rem; text-align: left; }}
  th {{ background: var(--surface); color: var(--muted); }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }}
  strong {{ color: #f1f5f9; }}
  .footer {{ margin-top: 3rem; padding: 1rem; color: var(--muted);
             font-size: 0.75rem; border-top: 1px solid var(--border); }}
  .badge-critical {{ color: var(--red); }} .badge-high {{ color: #f97316; }}
  .badge-medium {{ color: var(--yellow); }} .badge-low {{ color: var(--green); }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>🔍 SYNAPSE Incident Report</h1>
  <p>Report ID: <code>{html_lib.escape(report_id)}</code> &nbsp;|&nbsp;
     Incident: <code>{html_lib.escape(inc.id)}</code> &nbsp;|&nbsp;
     Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>
{body_html}
<div class="footer">
  Generated by SYNAPSE AIOps Platform v1.0.0 &mdash; 
  Self-Evolving Neuro-Symbolic Causal Architecture.
  Model-generated explanations are labeled as hypotheses and do not constitute proven facts.
</div>
</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# CSV summary
# ─────────────────────────────────────────────────────────────────────────────

def build_csv_summary(data: Dict[str, Any]) -> str:
    inc: Incident = data["incident"]
    output = io.StringIO()
    writer = csv.writer(output)

    # Incident summary
    writer.writerow(["INCIDENT SUMMARY"])
    writer.writerow(["Field", "Value"])
    for field, val in [
        ("Incident ID", inc.id),
        ("Title", inc.title),
        ("Status", inc.status),
        ("Severity", inc.severity),
        ("Root Cause", inc.root_cause_service or "Unknown"),
        ("Confidence", f"{inc.confidence:.0%}" if inc.confidence else "N/A"),
        ("Detected At", str(inc.detected_at)),
        ("Resolved At", str(inc.resolved_at) if inc.resolved_at else "N/A"),
    ]:
        writer.writerow([field, val])

    writer.writerow([])
    writer.writerow(["SUGGESTED ACTIONS"])
    writer.writerow(["Action ID", "Title", "Category", "Risk", "Status", "Target", "Simulated"])
    for a in data["actions"]:
        writer.writerow([
            a.id, a.title, a.category, a.risk_level, a.status,
            a.target_service or "", "Yes" if a.simulated else "No",
        ])

    writer.writerow([])
    writer.writerow(["VERIFICATION RESULTS"])
    writer.writerow(["Action ID", "Outcome", "Summary", "Data Freshness (s)"])
    for v in data["verifications"]:
        writer.writerow([
            v.action_id, v.outcome, v.summary or "", v.data_freshness_seconds or "N/A",
        ])

    return output.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# ZIP evidence bundle
# ─────────────────────────────────────────────────────────────────────────────

def build_zip_bundle(data: Dict[str, Any], report_id: str) -> bytes:
    """
    ZIP bundle containing all available evidence.
    Secrets are never included. Execution logs are sanitized.
    """
    buf = io.BytesIO()
    inc: Incident = data["incident"]

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Incident JSON
        incident_json = json.dumps(build_incident_json(data, report_id), indent=2)
        zf.writestr(f"{inc.id}/incident.json", incident_json)

        # 2. Markdown report
        zf.writestr(f"{inc.id}/report.md", build_markdown_report(data, report_id))

        # 3. Actions JSON
        actions_data = []
        for a in data["actions"]:
            approval = next((x for x in data["approvals"] if x.action_id == a.id), None)
            execution = next((x for x in data["executions"] if x.action_id == a.id), None)
            actions_data.append({
                "id": a.id,
                "title": a.title,
                "category": a.category,
                "status": a.status,
                "risk_level": a.risk_level,
                "simulated": bool(a.simulated),
                "approval": {
                    "decision": approval.decision,
                    "decided_by": approval.decided_by,
                } if approval else None,
                "execution_outcome": execution.outcome if execution else None,
                # NOTE: raw stdout/stderr NOT included (may have sensitive content)
            })
        zf.writestr(f"{inc.id}/actions.json", json.dumps(actions_data, indent=2))

        # 4. Verification evidence
        vev = []
        for v in data["verifications"]:
            vev.append({
                "action_id": v.action_id,
                "outcome": v.outcome,
                "metric_comparison": v.metric_comparison,
                "missing_metrics": v.missing_metrics,
                "summary": v.summary,
            })
        zf.writestr(f"{inc.id}/verification_evidence.json", json.dumps(vev, indent=2))

        # 5. Timeline
        timeline = [
            {"time": str(e.event_time), "type": e.event_type, "title": e.title, "actor": e.actor}
            for e in data["events"]
        ]
        zf.writestr(f"{inc.id}/timeline.json", json.dumps(timeline, indent=2))

        # 6. CSV summary
        zf.writestr(f"{inc.id}/summary.csv", build_csv_summary(data))

        # 7. Manifest
        manifest = {
            "report_id": report_id,
            "incident_id": inc.id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "contents": [
                f"{inc.id}/incident.json",
                f"{inc.id}/report.md",
                f"{inc.id}/actions.json",
                f"{inc.id}/verification_evidence.json",
                f"{inc.id}/timeline.json",
                f"{inc.id}/summary.csv",
            ],
            "security_note": "Secrets, credentials, and raw shell output are excluded from this bundle.",
        }
        manifest_str = json.dumps(manifest, indent=2)
        zf.writestr(f"{inc.id}/MANIFEST.json", manifest_str)

    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

async def generate_report(
    db: AsyncSession,
    incident_id: str,
    fmt: str = "json",
    generated_by: str = "api",
) -> Dict[str, Any]:
    """
    Generate and persist a report artifact.
    Returns: {"content": bytes|str, "content_type": str, "filename": str, "report_id": str}
    """
    data = await _collect_incident_data(db, incident_id)
    inc: Incident = data["incident"]
    report_id = _gen_report_id()

    content: Any
    content_type: str
    filename: str

    safe_id = incident_id.replace("/", "-").replace("..", "")  # path traversal protection

    if fmt == "json":
        content = json.dumps(build_incident_json(data, report_id), indent=2).encode("utf-8")
        content_type = "application/json"
        filename = f"synapse-incident-{safe_id}.json"

    elif fmt == "markdown":
        content = build_markdown_report(data, report_id).encode("utf-8")
        content_type = "text/markdown; charset=utf-8"
        filename = f"synapse-incident-{safe_id}.md"

    elif fmt == "html":
        content = build_html_report(data, report_id).encode("utf-8")
        content_type = "text/html; charset=utf-8"
        filename = f"synapse-incident-{safe_id}.html"

    elif fmt == "csv":
        content = build_csv_summary(data).encode("utf-8")
        content_type = "text/csv; charset=utf-8"
        filename = f"synapse-incident-{safe_id}-summary.csv"

    elif fmt == "zip":
        content = build_zip_bundle(data, report_id)
        content_type = "application/zip"
        filename = f"synapse-incident-{safe_id}-bundle.zip"

    elif fmt == "pdf":
        # Try reportlab; fall back to HTML with notice
        try:
            content = _build_pdf(data, report_id)
            content_type = "application/pdf"
            filename = f"synapse-incident-{safe_id}.pdf"
        except ImportError:
            logger.warning("reportlab not installed — returning HTML instead of PDF")
            html_content = build_html_report(data, report_id)
            notice = "<!-- PDF generation requires reportlab. Serving HTML equivalent. -->\n"
            content = (notice + html_content).encode("utf-8")
            content_type = "text/html; charset=utf-8"
            filename = f"synapse-incident-{safe_id}.html"

    else:
        raise ValueError(f"Unsupported format: {fmt!r}. Supported: json, markdown, html, csv, zip, pdf")

    # Persist report artifact metadata
    checksum = hashlib.sha256(content if isinstance(content, bytes) else content.encode()).hexdigest()
    artifact = ReportArtifact(
        id=report_id,
        incident_id=incident_id,
        report_format=fmt,
        generated_by=generated_by,
        file_size_bytes=len(content),
        checksum_sha256=checksum,
        incident_status_at_generation=inc.status,
        data_references={
            "rca_result_id": data["rca"].id if data["rca"] else None,
            "action_count": len(data["actions"]),
            "verification_count": len(data["verifications"]),
            "event_count": len(data["events"]),
        },
    )
    db.add(artifact)
    await db.commit()

    return {
        "content": content,
        "content_type": content_type,
        "filename": filename,
        "report_id": report_id,
        "checksum_sha256": checksum,
    }


def _build_pdf(data: Dict[str, Any], report_id: str) -> bytes:
    """Build PDF using reportlab. Raises ImportError if not installed."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.units import mm

    inc: Incident = data["incident"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                             topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("Title", parent=styles["Title"],
                                  textColor=colors.HexColor("#3b82f6"), fontSize=20, spaceAfter=6)
    story.append(Paragraph("SYNAPSE Incident Report", title_style))
    story.append(Paragraph(
        f"Report ID: {report_id} | Incident: {inc.id} | "
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        styles["Normal"]
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#334155")))
    story.append(Spacer(1, 6))

    # Summary table
    story.append(Paragraph("Incident Summary", styles["Heading2"]))
    tdata = [
        ["Field", "Value"],
        ["Title", inc.title],
        ["Status", inc.status.upper()],
        ["Severity", inc.severity.upper()],
        ["Detected", str(inc.detected_at)[:19] if inc.detected_at else "N/A"],
        ["Root Cause", inc.root_cause_service or "Unknown"],
        ["Confidence", f"{inc.confidence:.0%}" if inc.confidence else "N/A"],
    ]
    t = Table(tdata, colWidths=[50*mm, 120*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#94a3b8")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # RCA
    rca = data["rca"]
    story.append(Paragraph("Root Cause Analysis", styles["Heading2"]))
    if rca:
        story.append(Paragraph(
            f"<b>Root Cause:</b> {rca.root_cause_service} ({rca.confidence:.0%} confidence)", styles["Normal"]
        ))
        story.append(Paragraph(
            f"<b>Note:</b> The following explanation is a model-generated hypothesis.", styles["Italic"]
        ))
        if rca.explanation:
            story.append(Paragraph(rca.explanation[:1500], styles["Normal"]))
    else:
        story.append(Paragraph("RCA not yet completed.", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Actions
    story.append(Paragraph("Suggested Actions", styles["Heading2"]))
    for i, action in enumerate(data["actions"], 1):
        story.append(Paragraph(f"{i}. {action.title} [{action.status}]", styles["Heading3"]))
        story.append(Paragraph(f"Risk: {action.risk_level.upper()} | Category: {action.category}", styles["Normal"]))
        story.append(Paragraph(action.reason[:500], styles["Normal"]))
        story.append(Spacer(1, 6))

    doc.build(story)
    return buf.getvalue()
