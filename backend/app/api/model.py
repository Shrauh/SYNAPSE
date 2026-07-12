"""
Model status endpoint — introspect AI module state.
"""

from fastapi import APIRouter

from app.models.schemas import (
    ContinualLearningStatus,
    DEICStatus,
    MAMLStatus,
    ModelStatusResponse,
)

router = APIRouter(tags=["Model"])


@router.get("/model/status", response_model=ModelStatusResponse)
async def get_model_status():
    """Return the current status of all AI module components."""
    # TODO: Phase 6 — pull real state from loaded models
    return ModelStatusResponse(
        deic_gnn=DEICStatus(version="v1.0", trained_on_tasks=0),
        maml=MAMLStatus(),
        continual_learning=ContinualLearningStatus(),
    )
