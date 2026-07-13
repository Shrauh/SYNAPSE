"""
Model status endpoint — introspect AI module state.
"""

from fastapi import APIRouter

from app.ai_module.continual.manager import continual_manager
from app.ai_module.meta.maml import maml_adapter
from app.ai_module.orchestrator import pipeline
from app.models.schemas import (
    AdaptationRecord,
    ContinualLearningStatus,
    DEICStatus,
    MAMLStatus,
    ModelStatusResponse,
)

router = APIRouter(tags=["Model"])


@router.get("/model/status", response_model=ModelStatusResponse)
async def get_model_status():
    """Return the current status of all AI module components."""
    # Get real status from the pipeline
    status = pipeline.get_model_status()
    cl_status = continual_manager.get_status()
    maml_status = maml_adapter.get_status()

    return ModelStatusResponse(
        deic_gnn=DEICStatus(
            version="v1.0 (GAT Autoencoder)" if status.get("model_trained") else "v1.0 (untrained)",
            trained_on_tasks=cl_status.get("tasks_learned", 0),
        ),
        maml=MAMLStatus(
            meta_lr=maml_status.get("meta_lr", 0.001),
            inner_lr=maml_status.get("inner_lr", 0.01),
            inner_steps=maml_status.get("inner_steps", 3),
            tasks_meta_trained=maml_status.get("tasks_meta_trained", 0),
            adaptation_history=[
                AdaptationRecord(**rec)
                for rec in maml_status.get("adaptation_history", [])
            ],
        ),
        continual_learning=ContinualLearningStatus(
            ewc_lambda=cl_status.get("ewc_lambda", 5000.0),
            tasks_learned=cl_status.get("tasks_learned", 0),
            replay_buffer_size=cl_status.get("replay_buffer_size", 0),
            forgetting_rate=cl_status.get("forgetting_rate", 0.0),
        ),
    )
