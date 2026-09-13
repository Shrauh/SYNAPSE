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
  uncertainty_scores?: Record<string, number>;
  severity?: {
    level: string;
    reason: string;
    response_strategy: string;
    is_recurring: boolean;
    recurring_count: number;
  };
  recovery?: {
    action: string;
    target: string;
    kubectl_command: string;
    success: boolean;
    simulated: boolean;
  };
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

// ─── Continual Learning ───────────────────────────────────────────

export interface CLTaskRecord {
  task_id: string;
  task_type: "normal_baseline" | "fault_pattern" | "custom";
  samples_in_buffer: number;
  ewc_registered: boolean;
  performance_metric: number;
  registered_at: string | null;
}

export interface CLDetailedStatus {
  initialized: boolean;
  ewc_lambda: number;
  tasks_learned: number;
  task_ids: string[];
  replay_buffer_size: number;
  replay_buffer_max: number;
  replay_buffer_fill_pct: number;
  forgetting_rate: number;
  ewc_tasks_seen: number;
  total_samples_seen: number;
  tasks: CLTaskRecord[];
}

export interface CLForgettingEntry {
  episode: number;
  task_id: string;
  forgetting_rate: number;
  ewc_penalty: number;
}

export interface CLForgettingHistory {
  history: CLForgettingEntry[];
  current_forgetting_rate: number;
}

export interface CLReplayStats {
  buffer_size: number;
  max_size: number;
  total_seen: number;
  fill_percentage: number;
  task_distribution: Record<string, number>;
}

export interface CLEWCTaskStat {
  task_id: string;
  task_type: string;
  fisher_mean: number;
  fisher_max: number;
  ewc_penalty_contribution: number;
  param_count: number;
}

export interface CLEWCStats {
  ewc_lambda: number;
  tasks: CLEWCTaskStat[];
  total_tasks: number;
  protection_strength: "high" | "medium" | "low";
}

export interface CLTriggerRequest {
  task_id: string;
  fault_type: string;
  root_cause_service: string;
  num_scenarios: number;
  ewc_lambda_override?: number;
}

export interface CLTriggerResponse {
  success: boolean;
  task_id: string;
  message: string;
  samples_added: number;
  ewc_registered: boolean;
  new_forgetting_rate: number;
  execution_time_ms: number;
}

