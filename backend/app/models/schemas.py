"""
SYNAPSE Pydantic Schemas — Request/Response models for the API layer.

Every endpoint's input and output is defined here for validation,
serialization, and automatic OpenAPI doc generation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Health & System
# ──────────────────────────────────────────────

class ComponentStatus(BaseModel):
    api: str = "up"
    database: str = "up"
    ai_module: str = "up"
    gnn_model_loaded: bool = False
    maml_ready: bool = False


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    components: ComponentStatus
    uptime_seconds: float


class ModelStats(BaseModel):
    gnn_accuracy: float = 0.0
    maml_adaptation_speed_ms: float = 0.0
    continual_learning_tasks_seen: int = 0
    ewc_lambda: float = 5000.0


class SystemStats(BaseModel):
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


class MetricsResponse(BaseModel):
    total_incidents: int = 0
    active_incidents: int = 0
    avg_resolution_time_sec: float = 0.0
    model_stats: ModelStats = Field(default_factory=ModelStats)
    system: SystemStats = Field(default_factory=SystemStats)


# ──────────────────────────────────────────────
# Service Graph
# ──────────────────────────────────────────────

class ServiceMetrics(BaseModel):
    latency: float = 0.0
    error_rate: float = 0.0
    cpu: float = 0.0
    memory: float = 0.0
    request_rate: float = 0.0


class GraphNode(BaseModel):
    id: str
    label: str
    type: str = "service"
    metrics: ServiceMetrics = Field(default_factory=ServiceMetrics)
    anomaly_score: float = 0.0
    status: str = "healthy"


class GraphEdge(BaseModel):
    source: str
    target: str
    call_type: str = "http"
    avg_latency: float = 0.0
    call_frequency: float = 0.0
    weight: float = 0.0


class GraphMetadata(BaseModel):
    total_services: int = 0
    total_edges: int = 0
    last_updated: Optional[datetime] = None


class GraphResponse(BaseModel):
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    metadata: GraphMetadata = Field(default_factory=GraphMetadata)


# ──────────────────────────────────────────────
# Incidents
# ──────────────────────────────────────────────

class IncidentSummary(BaseModel):
    id: str
    title: str
    status: str
    severity: str
    root_cause_service: Optional[str] = None
    affected_services: Optional[List[str]] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    confidence: Optional[float] = None


class IncidentListResponse(BaseModel):
    incidents: List[IncidentSummary] = []
    total: int = 0
    page: int = 1
    per_page: int = 20


class CreateIncidentRequest(BaseModel):
    title: str
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    description: Optional[str] = None


class CreateIncidentResponse(BaseModel):
    id: str
    status: str = "analyzing"
    message: str = "RCA pipeline triggered."


class TimelineEvent(BaseModel):
    time: str
    event: str
    score: Optional[float] = None


class RootCauseInfo(BaseModel):
    service: str
    confidence: float
    fault_type: Optional[str] = None


class IncidentDetailResponse(BaseModel):
    id: str
    title: str
    status: str
    severity: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    anomaly_scores: Dict[str, float] = {}
    root_cause: Optional[RootCauseInfo] = None
    affected_services: Optional[List[str]] = None
    timeline: List[TimelineEvent] = []


# ──────────────────────────────────────────────
# RCA Reports
# ──────────────────────────────────────────────

class ModelInfo(BaseModel):
    gnn_type: str = "DEIC-GAT Autoencoder"
    maml_adapted: bool = False
    adaptation_steps: int = 0
    causal_method: str = "PC Algorithm"


class RCAReportResponse(BaseModel):
    incident_id: str
    root_cause: RootCauseInfo
    explanation: str = ""
    propagation_chain: str = ""
    metric_deltas: Dict[str, Dict[str, str]] = {}
    recommended_actions: List[str] = []
    model_info: ModelInfo = Field(default_factory=ModelInfo)


class CausalNode(BaseModel):
    id: str
    anomaly_score: float
    is_root: bool = False


class CausalEdge(BaseModel):
    source: str
    target: str
    strength: float = 0.0


class CausalGraphResponse(BaseModel):
    incident_id: str
    causal_nodes: List[CausalNode] = []
    causal_edges: List[CausalEdge] = []


# ──────────────────────────────────────────────
# RCA Pipeline Control
# ──────────────────────────────────────────────

class TriggerRCARequest(BaseModel):
    window_start: datetime
    window_end: datetime
    fault_type_hint: Optional[str] = None


class PipelineStages(BaseModel):
    deic_gnn: str = "pending"
    maml_adaptation: str = "pending"
    causal_inference: str = "pending"
    llm_reasoning: str = "pending"


class TriggerRCAResponse(BaseModel):
    incident_id: str
    pipeline_stages: PipelineStages = Field(default_factory=PipelineStages)
    execution_time_ms: float = 0.0
    result_url: str = ""


class SimulateRequest(BaseModel):
    fault_type: str = "db_latency_spike"
    root_cause_service: str = "database"
    severity: str = "critical"
    duration_minutes: int = 5


class SimulateResponse(BaseModel):
    simulation_id: str
    incident_id: str
    injected_fault: Dict[str, str] = {}
    rca_result: Optional[RCAReportResponse] = None


# ──────────────────────────────────────────────
# Model Status
# ──────────────────────────────────────────────

class AdaptationRecord(BaseModel):
    task: str
    accuracy: float


class DEICStatus(BaseModel):
    version: str = "v1.0"
    trained_on_tasks: int = 0
    last_trained: Optional[datetime] = None


class MAMLStatus(BaseModel):
    meta_lr: float = 0.001
    inner_lr: float = 0.01
    inner_steps: int = 3
    tasks_meta_trained: int = 0
    adaptation_history: List[AdaptationRecord] = []


class ContinualLearningStatus(BaseModel):
    ewc_lambda: float = 5000.0
    tasks_learned: int = 0
    replay_buffer_size: int = 0
    forgetting_rate: float = 0.0


class ModelStatusResponse(BaseModel):
    deic_gnn: DEICStatus = Field(default_factory=DEICStatus)
    maml: MAMLStatus = Field(default_factory=MAMLStatus)
    continual_learning: ContinualLearningStatus = Field(
        default_factory=ContinualLearningStatus
    )


# ──────────────────────────────────────────────
# WebSocket Messages
# ──────────────────────────────────────────────

class WSMessage(BaseModel):
    type: str  # anomaly_update | incident_detected | rca_complete
    data: Dict[str, Any] = {}
