import { api } from "./client";
import type {
  GraphResponse, IncidentSummary, IncidentDetail,
  RCAReport, CausalGraph, HealthResponse, MetricsResponse,
  ModelStatus, SimulateRequest, SimulateResponse,
} from "../types/api";

// ── Existing endpoints ────────────────────────────────────────────────────
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

// ── New remediation endpoints ─────────────────────────────────────────────
export const executeRemediation = (req: {
  incident_id: string;
  fault_type?: string;
  root_cause_service?: string;
  anomaly_scores?: Record<string, number>;
  dry_run?: boolean;
}) => api.post("/remediation/execute", req).then(r => r.data);

export const approveRemediation = (recordId: string, actionId: string, service: string) =>
  api.post(`/remediation/approve/${recordId}?action_id=${actionId}&service=${service}`)
    .then(r => r.data);

export const fetchRemediationHistory = () =>
  api.get("/remediation/history").then(r => r.data);

export const fetchRemediationActions = () =>
  api.get("/remediation/actions").then(r => r.data);

// ── Feedback endpoints ────────────────────────────────────────────────────
export const submitFeedback = (req: {
  incident_id: string;
  rca_correct?: boolean;
  correct_root_cause?: string;
  action_taken?: string;
  remediation_successful?: boolean;
  notes?: string;
}) => api.post("/feedback", req).then(r => r.data);

// ── Learning stats ────────────────────────────────────────────────────────
export const fetchLearningStats = () =>
  api.get("/learning/stats").then(r => r.data);

// ── Convenience object for component use ──────────────────────────────────
export const api_endpoints = {
  getIncidentReport: (id: string) =>
    api.get(`/incidents/${id}/report`).then(r => r.data).catch(() => null),
};

// Re-export api_endpoints as `api` for component backward-compat
export { api_endpoints as api };
