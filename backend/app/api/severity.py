"""
Severity & Recovery API endpoints.

Provides endpoints for:
- Viewing severity classification history
- Viewing recovery action logs
- Detecting recurring patterns
- Getting architectural recommendations
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_module.severity.classifier import severity_classifier
from app.ai_module.rl.recovery_engine import recovery_engine
from app.ai_module.pattern.analyzer import pattern_analyzer
from app.db.database import get_db

router = APIRouter(prefix="/severity", tags=["Severity & Recovery"])


@router.get("/status")
async def get_severity_status() -> Dict[str, Any]:
    """Get current severity classification status and history."""
    return {
        "recurring_patterns": severity_classifier.get_recurring_patterns(),
        "incident_history": severity_classifier.get_history()[-20:],  # Last 20
        "total_incidents_tracked": len(severity_classifier.get_history()),
    }


@router.get("/recovery/status")
async def get_recovery_status() -> Dict[str, Any]:
    """Get recovery engine status and action history."""
    return {
        "engine_status": recovery_engine.get_status(),
        "recent_actions": recovery_engine.get_action_history()[-20:],  # Last 20
    }


@router.get("/recovery/history")
async def get_recovery_history() -> List[Dict[str, Any]]:
    """Get full recovery action history."""
    return recovery_engine.get_action_history()


@router.get("/patterns")
async def get_recurring_patterns() -> Dict[str, Any]:
    """Detect and return recurring failure patterns."""
    return pattern_analyzer.get_summary()


@router.get("/patterns/recommendations")
async def get_recommendations() -> List[Dict[str, Any]]:
    """Get architectural recommendations for recurring issues."""
    patterns = pattern_analyzer.detect_recurring()
    recommendations = pattern_analyzer.generate_recommendations(patterns)
    return [
        {
            "service": r.service,
            "problem": r.problem,
            "recommendation": r.recommendation,
            "estimated_effort": r.estimated_effort,
            "priority": r.priority,
            "evidence": r.evidence,
        }
        for r in recommendations
    ]
