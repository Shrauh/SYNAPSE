import { api } from "./client";
import type {
  GraphResponse, IncidentSummary, IncidentDetail,
  RCAReport, CausalGraph, HealthResponse, MetricsResponse,
  ModelStatus, SimulateRequest, SimulateResponse,
} from "../types/api";

export const fetchHealth = () => api.get<HealthResponse>("/health").then(r => r.data);
export const fetchMetrics = () => api.get<MetricsResponse>("/metrics").then(r => r.data);
export const fetchGraph = () => api.get<GraphResponse>("/graph/current").then(r => r.data);
export const fetchIncidents = (page = 1) =>
  api.get<{ incidents: IncidentSummary[]; total: number; page: number; per_page: number }>(
    `/incidents?page=${page}&per_page=20`
  ).then(r => r.data);
export const fetchIncident = (id: string) =>
  api.get<IncidentDetail>(`/incidents/${id}`).then(r => r.data);
export const fetchReport = (id: string) =>
  api.get<RCAReport>(`/incidents/${id}/report`).then(r => r.data);
export const fetchCausalGraph = (id: string) =>
  api.get<CausalGraph>(`/incidents/${id}/causal-graph`).then(r => r.data);
export const fetchModelStatus = () =>
  api.get<ModelStatus>("/model/status").then(r => r.data);
export const simulateFault = (req: SimulateRequest) =>
  api.post<SimulateResponse>("/rca/simulate", req).then(r => r.data);
export const getSeverityStatus = () => api.get('/severity/status');
export const getRecoveryHistory = () => api.get('/severity/recovery/history');
export const getPatterns = () => api.get('/severity/patterns');

export interface ActiveSystemResponse {
  system: string;
  label: string;
  services: string[];
  service_count: number;
  active_system?: string;
}

export const getActiveSystem = () => api.get<ActiveSystemResponse>("/system/active").then(r => r.data);
export const switchSystem = (system: string) => api.post<ActiveSystemResponse>("/system/switch", { system }).then(r => r.data);
export const getAvailableSystems = () => api.get<{ available: { id: string; label: string; service_count: number; services: string[] }[]; custom?: any }>("/system/available").then(r => r.data);
export const getBenchmark = () => api.get<any>("/eval/benchmark").then(r => r.data);
export const getEvalHistory = () => api.get<any>("/eval/history").then(r => r.data);
export const evaluateManual = (req: { incident_id: string, predicted_ranking: string[], true_root_cause: string }) => api.post<any>("/eval/evaluate", req).then(r => r.data);

// New API endpoints for Alerts, Logs, Notifications
export const getAlertStatus = () => api.get("/alerts/status").then(r => r.data);
export const testAlert = (req: { service: string; fault_type: string }) => api.post("/alerts/test", req).then(r => r.data);
export const analyzeLog = (service: string) => api.get(`/logs/analyze/${service}`).then(r => r.data);
export const pushLogs = (req: { service: string; logs: string[] }) => api.post("/logs/push", req).then(r => r.data);
export const getPushStatus = () => api.get("/logs/push/status").then(r => r.data);
export const getNotifyStatus = () => api.get("/notify/status").then(r => r.data);
export const testNotification = (channel: string) => api.post(`/notify/test?channel=${channel}`).then(r => r.data);

// Connect Your System
export const testConnection = (req: { name: string; type: string; url: string; api_key?: string; namespace?: string }) =>
  api.post<{ name: string; type: string; url: string; status: string; latency_ms: number; message: string; timestamp: string }>("/connect/test", req).then(r => r.data);
export const listConnections = () =>
  api.get<{ name: string; type: string; url: string; status: string; latency_ms: number; last_checked: string }[]>("/connect/list").then(r => r.data);
export const removeConnection = (name: string) =>
  api.delete(`/connect/${name}`).then(r => r.data);

// ── P1: Actions, Verification, Reports, Audit, Platform ────────────────────
export interface SuggestedAction {
  id: string;
  incident_id: string;
  title: string;
  category: string;
  description: string;
  reason: string;
  target_service: string | null;
  target_namespace: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  requires_approval: boolean;
  status: string;
  confidence_score: number;
  priority_rank: number;
  simulated: boolean;
  proposed_by: string;
  created_at: string;
  updated_at: string;
  evidence_refs?: Array<{ type: string; ref: string; description?: string }>;
  preconditions?: string[];
  expected_outcome?: string;
  potential_side_effects?: string[];
  rollback_plan?: string;
  verification_plan?: string;
  verification_metrics?: Array<{ metric: string; threshold: number; direction: string }>;
  timeout_seconds: number;
  approval?: { decision: string; decided_by: string; reason?: string; decided_at: string } | null;
  execution?: {
    id: number; outcome: string; handler_name?: string;
    started_at: string; completed_at?: string; duration_ms?: number;
    simulated: boolean; error_message?: string;
  } | null;
  verification?: {
    id: number; outcome: string; summary?: string;
    metric_comparison?: MetricComparison[];
    missing_metrics?: string[]; data_freshness_seconds?: number;
    next_step_recommendation?: string;
  } | null;
  valid_transitions?: string[];
}

export interface MetricComparison {
  metric: string; source: string; unit: string;
  baseline: number | null; post: number | null;
  diff: number | null; pct_change: number | null;
  interpretation: string; data_fresh: boolean;
  missing_data_reason?: string;
}

export interface VerificationResult {
  id: number; action_id: string; outcome: string;
  summary?: string; criteria?: any[];
  metric_comparison?: MetricComparison[];
  baseline_snapshot?: Record<string, number>;
  post_action_snapshot?: Record<string, number>;
  data_freshness_seconds?: number;
  missing_metrics?: string[];
  symptoms_resolved?: boolean;
  next_step_recommendation?: string;
  started_at: string; completed_at?: string;
}

export interface TimelineEvent {
  id: string; event_type: string; event_time: string;
  actor: string; title: string; detail?: string;
  metadata?: Record<string, any>; severity?: string;
}

export interface AuditEvent {
  id: number; event_time: string; actor: string;
  action: string; resource_type: string; resource_id: string;
  incident_id?: string; outcome: string; detail?: Record<string, any>;
}

export interface PlatformHealth {
  overall: string;
  components: Record<string, { status: string; detail?: string; [key: string]: any }>;
  checked_at: string;
}

// Action API calls
export const fetchIncidentActions = (incidentId: string, status?: string) =>
  api.get<SuggestedAction[]>(`/incidents/${incidentId}/actions${status ? `?status=${status}` : ''}`).then(r => r.data);

export const generateActions = (incidentId: string, force = false) =>
  api.post<{ generated: number; action_ids: string[] }>(`/incidents/${incidentId}/actions/generate`, { force_regenerate: force }).then(r => r.data);

export const fetchAction = (actionId: string) =>
  api.get<SuggestedAction>(`/actions/${actionId}`).then(r => r.data);

export const approveAction = (actionId: string, decidedBy: string, decision: 'APPROVED' | 'REJECTED', reason?: string) =>
  api.post(`/actions/${actionId}/approve`, { decided_by: decidedBy, decision, reason }).then(r => r.data);

export const executeAction = (actionId: string, requestedBy = 'operator') =>
  api.post(`/actions/${actionId}/execute`, { requested_by: requestedBy }).then(r => r.data);

export const verifyAction = (actionId: string) =>
  api.post<VerificationResult>(`/actions/${actionId}/verify`).then(r => r.data);

export const fetchVerification = (actionId: string) =>
  api.get<VerificationResult>(`/actions/${actionId}/verification`).then(r => r.data);

export const rollbackAction = (actionId: string, requestedBy: string, reason: string) =>
  api.post(`/actions/${actionId}/rollback`, { requested_by: requestedBy, reason }).then(r => r.data);

export const fetchExecutionLog = (actionId: string) =>
  api.get(`/actions/${actionId}/log`).then(r => r.data);

// Report downloads
export const getReportDownloadUrl = (incidentId: string, fmt: string) =>
  `/api/v1/incidents/${incidentId}/download/${fmt}`;

// Timeline events
export const fetchIncidentTimeline = (incidentId: string) =>
  api.get<TimelineEvent[]>(`/incidents/${incidentId}/timeline-events`).then(r => r.data);

// Similar incidents
export const fetchSimilarIncidents = (incidentId: string, limit = 5) =>
  api.get<{ incident_id: string; similar: any[]; count: number }>(`/incidents/${incidentId}/similar?limit=${limit}`).then(r => r.data);

// Audit log
export const fetchAuditLog = (params?: { incident_id?: string; resource_type?: string; limit?: number }) => {
  const q = new URLSearchParams();
  if (params?.incident_id) q.set('incident_id', params.incident_id);
  if (params?.resource_type) q.set('resource_type', params.resource_type);
  if (params?.limit) q.set('limit', String(params.limit));
  return api.get<AuditEvent[]>(`/audit?${q}`).then(r => r.data);
};

// Platform health
export const fetchPlatformHealth = () =>
  api.get<PlatformHealth>('/platform/health').then(r => r.data);

// Kubernetes Cluster
export const getK8sPods = async (): Promise<any> => {
  const res = await api.get("/k8s/pods");
  return res.data;
};

export const injectK8sFault = async (service: string, faultType: string = 'pod_kill'): Promise<any> => {
  const res = await api.post("/k8s/inject-fault", { service, fault_type: faultType });
  return res.data;
};

export const recoverK8sService = async (service: string, action: string = 'restart_pod'): Promise<any> => {
  const res = await api.post("/k8s/recover", { service, action });
  return res.data;
};
