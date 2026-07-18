export interface GraphNode {
  id: string;
  label: string;
  type: "gateway" | "service" | "infrastructure";
  anomaly_score: number;
  status: "healthy" | "degraded" | "warning" | "critical";
  metrics: {
    latency: number;
    error_rate: number;
    cpu: number;
    memory: number;
    request_rate: number;
  };
}

export interface GraphEdge {
  source: string;
  target: string;
  call_type: "http" | "tcp" | "async";
  avg_latency: number;
  call_frequency: number;
  weight: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: { total_services: number; total_edges: number; last_updated: string };
}

export interface IncidentSummary {
  id: string;
  title: string;
  status: "analyzing" | "detected" | "resolved" | "error";
  severity: string;
  root_cause_service: string | null;
  affected_services: string[];
  detected_at: string;
  resolved_at: string | null;
  confidence: number | null;
}

export interface IncidentDetail {
  id: string;
  title: string;
  status: string;
  severity: string;
  detected_at: string;
  resolved_at: string | null;
  anomaly_scores: Record<string, number>;
  root_cause: { service: string; confidence: number; fault_type: string } | null;
  affected_services: string[];
  timeline: { time: string; event: string; score: number }[];
}

export interface RCAReport {
  incident_id: string;
  root_cause: { service: string; confidence: number; fault_type: string };
  explanation: string;
  propagation_chain: string;
  metric_deltas: Record<string, Record<string, string>>;
  recommended_actions: string[];
  model_info: Record<string, unknown>;
}

export interface CausalNode {
  id: string;
  anomaly_score: number;
  is_root: boolean;
}

export interface CausalEdge {
  source: string;
  target: string;
  strength: number;
}

export interface CausalGraph {
  incident_id: string;
  causal_nodes: CausalNode[];
  causal_edges: CausalEdge[];
}

export interface HealthResponse {
  status: string;
  version: string;
  components: {
    api: string;
    database: string;
    ai_module: string;
    gnn_model_loaded: boolean;
    maml_ready: boolean;
  };
  uptime_seconds: number;
}

export interface MetricsResponse {
  total_incidents: number;
  active_incidents: number;
  avg_resolution_time_sec: number;
  model_stats: Record<string, unknown>;
}

export interface ModelStatus {
  deic_gnn: { version: string; trained_on_tasks: number };
  maml: { meta_lr: number; inner_lr: number; tasks_meta_trained: number };
  continual_learning: {
    ewc_lambda: number;
    tasks_learned: number;
    replay_buffer_size: number;
    forgetting_rate: number;
  };
}

export interface SimulateRequest {
  root_cause_service: string;
  fault_type: string;
  severity: string;
  duration_minutes: number;
}

export interface SimulateResponse {
  simulation_id: string;
  incident_id: string;
  injected_fault: { service: string; type: string };
}
