"""
SYNAPSE Notifications — Slack and Teams webhook notifications.

Sends rich messages to Slack/Teams when:
- RCA pipeline completes (root cause found)
- Recovery action is executed
- L4 recurring pattern detected (architectural recommendation)

Configuration (environment variables or .env):
  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
  TEAMS_WEBHOOK_URL=https://xxx.webhook.office.com/...
  NOTIFY_ON_COMPLETE=true
  NOTIFY_ON_RECOVERY=true
"""
from __future__ import annotations
import logging
import os
from typing import Any, Dict, List, Optional
import httpx
from datetime import datetime, timezone

logger = logging.getLogger("synapse.notifications")

# Read from env
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")
NOTIFY_ON_COMPLETE = os.getenv("NOTIFY_ON_COMPLETE", "true").lower() == "true"
NOTIFY_ON_RECOVERY = os.getenv("NOTIFY_ON_RECOVERY", "true").lower() == "true"

# Severity level colors
SEVERITY_COLORS = {
    "L1_SIMPLE": "#36a64f",      # green
    "L2_CASCADING": "#f5a623",   # orange
    "L3_SYSTEMIC": "#d0021b",    # red
    "L4_DESIGN_FLAW": "#9013fe", # purple
}


def _severity_emoji(level: str) -> str:
    return {
        "L1_SIMPLE": "🟢",
        "L2_CASCADING": "🟡",
        "L3_SYSTEMIC": "🔴",
        "L4_DESIGN_FLAW": "🟣",
    }.get(level, "⚪")


def _build_slack_message(pipeline_result: Dict[str, Any], incident_id: str, dashboard_url: str = "http://localhost:5173") -> Dict:
    """Build a rich Slack Block Kit message from pipeline result."""
    root_cause = pipeline_result.get("root_cause", "unknown")
    confidence = pipeline_result.get("confidence", 0.0)
    explanation = pipeline_result.get("explanation", "No explanation available")
    propagation = pipeline_result.get("propagation_chain", "")
    exec_time = pipeline_result.get("execution_time_ms", 0)
    severity = pipeline_result.get("severity", {})
    recovery = pipeline_result.get("recovery", {})
    severity_level = severity.get("level", "L1_SIMPLE")
    color = SEVERITY_COLORS.get(severity_level, "#888")
    emoji = _severity_emoji(severity_level)

    return {
        "attachments": [{
            "color": color,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} SYNAPSE: Root Cause Found — {root_cause}",
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Incident ID*\n`{incident_id}`"},
                        {"type": "mrkdwn", "text": f"*Confidence*\n{confidence*100:.1f}%"},
                        {"type": "mrkdwn", "text": f"*Severity*\n{severity_level}"},
                        {"type": "mrkdwn", "text": f"*Analysis Time*\n{exec_time:.0f}ms"},
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Root Cause Service:* `{root_cause}`\n*Propagation:* {propagation}\n\n*Explanation:* {explanation[:300]}..."
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Recovery Action*\n`{recovery.get('action', 'none')}`"},
                        {"type": "mrkdwn", "text": f"*Recovery Status*\n{'✅ Executed' if recovery.get('success') else '⏳ Pending approval'}"},
                    ]
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*kubectl:* `{recovery.get('kubectl_command', 'N/A')}`"}
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "📊 View Report"},
                            "url": f"{dashboard_url}/incidents/{incident_id}",
                            "style": "primary",
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"SYNAPSE AIOps • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"}]
                }
            ]
        }]
    }


def _build_teams_message(pipeline_result: Dict[str, Any], incident_id: str, dashboard_url: str = "http://localhost:5173") -> Dict:
    """Build a Teams Adaptive Card message from pipeline result."""
    root_cause = pipeline_result.get("root_cause", "unknown")
    confidence = pipeline_result.get("confidence", 0.0)
    severity = pipeline_result.get("severity", {})
    severity_level = severity.get("level", "L1_SIMPLE")
    explanation = pipeline_result.get("explanation", "")[:250]
    recovery = pipeline_result.get("recovery", {})

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": SEVERITY_COLORS.get(severity_level, "#888").lstrip("#"),
        "summary": f"SYNAPSE: Root cause found — {root_cause}",
        "sections": [
            {
                "activityTitle": f"{_severity_emoji(severity_level)} SYNAPSE Alert: {root_cause}",
                "activitySubtitle": f"Severity: {severity_level} | Confidence: {confidence*100:.1f}%",
                "activityText": explanation,
                "facts": [
                    {"name": "Incident ID", "value": incident_id},
                    {"name": "Recovery", "value": recovery.get("action", "none")},
                    {"name": "kubectl", "value": recovery.get("kubectl_command", "N/A")},
                ]
            }
        ],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "View Report",
                "targets": [{"os": "default", "uri": f"{dashboard_url}/incidents/{incident_id}"}]
            }
        ]
    }


async def notify_rca_complete(
    pipeline_result: Dict[str, Any],
    incident_id: str,
    dashboard_url: str = "http://localhost:5173",
) -> Dict[str, bool]:
    """
    Send RCA completion notification to Slack and/or Teams.
    Called automatically by the pipeline when analysis is done.
    """
    if not NOTIFY_ON_COMPLETE:
        return {"slack": False, "teams": False, "reason": "notifications disabled"}

    results = {"slack": False, "teams": False}

    async with httpx.AsyncClient(timeout=10.0) as client:
        if SLACK_WEBHOOK_URL:
            try:
                payload = _build_slack_message(pipeline_result, incident_id, dashboard_url)
                resp = await client.post(SLACK_WEBHOOK_URL, json=payload)
                resp.raise_for_status()
                results["slack"] = True
                logger.info(f"Slack notification sent for incident {incident_id}")
            except Exception as e:
                logger.warning(f"Slack notification failed: {e}")

        if TEAMS_WEBHOOK_URL:
            try:
                payload = _build_teams_message(pipeline_result, incident_id, dashboard_url)
                resp = await client.post(TEAMS_WEBHOOK_URL, json=payload)
                resp.raise_for_status()
                results["teams"] = True
                logger.info(f"Teams notification sent for incident {incident_id}")
            except Exception as e:
                logger.warning(f"Teams notification failed: {e}")

    return results


async def notify_test(channel: str = "slack") -> Dict[str, Any]:
    """Send a test notification to verify webhook configuration."""
    fake_result = {
        "root_cause": "payment-service",
        "confidence": 0.94,
        "explanation": "The payment-service is experiencing high latency (2.3s avg) due to database connection pool exhaustion. 4 downstream services affected.",
        "propagation_chain": "payment-service → order-service → api-gateway",
        "execution_time_ms": 1847,
        "severity": {"level": "L2_CASCADING", "reason": "2 services affected"},
        "recovery": {
            "action": "restart_pod",
            "kubectl_command": "kubectl rollout restart deployment/payment-service -n default",
            "success": True,
            "simulated": True,
        }
    }
    return await notify_rca_complete(fake_result, "test-incident-001")
