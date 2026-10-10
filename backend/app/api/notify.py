"""
Notification API — manage and test SYNAPSE notifications.
"""
from __future__ import annotations
import os
from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.notifications import notify_test, SLACK_WEBHOOK_URL, TEAMS_WEBHOOK_URL, NOTIFY_ON_COMPLETE

router = APIRouter(prefix="/notify", tags=["Notifications"])


@router.get("/status")
def notification_status() -> Dict[str, Any]:
    """Check notification configuration status."""
    return {
        "slack": {
            "configured": bool(SLACK_WEBHOOK_URL),
            "enabled": NOTIFY_ON_COMPLETE,
            "webhook_url_set": bool(SLACK_WEBHOOK_URL),
        },
        "teams": {
            "configured": bool(TEAMS_WEBHOOK_URL),
            "enabled": NOTIFY_ON_COMPLETE,
            "webhook_url_set": bool(TEAMS_WEBHOOK_URL),
        },
        "setup_instructions": {
            "slack": "Set SLACK_WEBHOOK_URL env var to your Slack incoming webhook URL",
            "teams": "Set TEAMS_WEBHOOK_URL env var to your Teams webhook connector URL",
            "enable": "Set NOTIFY_ON_COMPLETE=true (default: true)",
        }
    }


@router.post("/test")
async def send_test_notification(channel: str = "slack") -> Dict[str, Any]:
    """
    Send a test notification to verify webhook setup.
    Use this in demo to show real Slack/Teams integration.
    
    ?channel=slack or ?channel=teams
    """
    if channel == "slack" and not SLACK_WEBHOOK_URL:
        raise HTTPException(
            status_code=400,
            detail="SLACK_WEBHOOK_URL not configured. Set it in your .env file."
        )
    if channel == "teams" and not TEAMS_WEBHOOK_URL:
        raise HTTPException(
            status_code=400,
            detail="TEAMS_WEBHOOK_URL not configured. Set it in your .env file."
        )
    result = await notify_test(channel)
    return {"sent": result, "channel": channel, "message": "Test notification dispatched"}
