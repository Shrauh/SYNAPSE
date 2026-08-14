"""
SYNAPSE Learning Stats API — Continual Learning Status Endpoint.

GET /learning/stats — returns EWC, MAML, and CQL agent state

Used by the frontend LearningStats panel to show:
  - EWC task consolidation progress
  - MAML adaptation history
  - CQL Q-table size + replay buffer
  - Estimated forgetting rate
  - AC@1, AC@3 evaluation metrics
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app.models.schemas import LearningStatsResponse

router = APIRouter(prefix="/learning", tags=["Continual Learning"])


@router.get("/stats", response_model=LearningStatsResponse)
async def get_learning_stats():
    """Return comprehensive learning system status."""
    stats: Dict[str, Any] = {
        "ewc": {"tasks_learned": 0, "lambda": 5000.0, "fisher_computed": False},
        "maml": {"initialized": False, "tasks_meta_trained": 0, "adaptation_history": []},
        "cql": {"q_table_states": 0, "replay_buffer_size": 0},
        "replay_buffer": {"size": 0, "capacity": 500},
        "performance": {
            "ac_at_1": 0.0,
            "ac_at_3": 0.0,
            "forgetting_rate": 0.0,
            "total_incidents": 0,
        },
    }

    # EWC stats
    try:
        from app.ai_module.continual.manager import continual_manager
        ewc_status = continual_manager.get_status()
        stats["ewc"] = ewc_status.get("ewc", stats["ewc"])
        stats["replay_buffer"]["size"] = ewc_status.get("replay_buffer_size", 0)
    except Exception:
        pass

    # MAML stats
    try:
        from app.ai_module.meta.maml import maml_adapter
        stats["maml"] = maml_adapter.get_status()
    except Exception:
        pass

    # CQL stats
    try:
        from app.ai_module.remediation.cql_agent import cql_agent
        stats["cql"] = cql_agent.get_status()
    except Exception:
        pass

    # Performance metrics from replay buffer
    try:
        from app.ai_module.continual.manager import continual_manager
        perf = continual_manager.compute_performance_metrics()
        stats["performance"].update(perf)
    except Exception:
        pass

    return LearningStatsResponse(
        ewc_tasks_learned=stats["ewc"].get("tasks_learned", 0),
        ewc_lambda=stats["ewc"].get("lambda", 5000.0),
        ewc_fisher_computed=stats["ewc"].get("fisher_computed", False),
        maml_initialized=stats["maml"].get("initialized", False),
        maml_tasks_trained=stats["maml"].get("tasks_meta_trained", 0),
        maml_inner_lr=stats["maml"].get("inner_lr", 0.01),
        maml_adaptation_history=stats["maml"].get("adaptation_history", []),
        cql_states=stats["cql"].get("q_table_states", 0),
        cql_replay_size=stats["cql"].get("replay_buffer_size", 0),
        replay_buffer_size=stats["replay_buffer"]["size"],
        replay_buffer_capacity=stats["replay_buffer"]["capacity"],
        ac_at_1=stats["performance"].get("ac_at_1", 0.0),
        ac_at_3=stats["performance"].get("ac_at_3", 0.0),
        forgetting_rate=stats["performance"].get("forgetting_rate", 0.0),
        total_incidents_learned=stats["performance"].get("total_incidents", 0),
    )
