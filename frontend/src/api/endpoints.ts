import { api } from "./client";
import type {
  GraphResponse, IncidentSummary, IncidentDetail,
  RCAReport, CausalGraph, HealthResponse, MetricsResponse,
  ModelStatus, SimulateRequest, SimulateResponse,
  CLDetailedStatus, CLForgettingHistory, CLReplayStats,
  CLEWCStats, CLTriggerRequest, CLTriggerResponse, CLTaskRecord,
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

// ─── Continual Learning ───────────────────────────────────────────
export const fetchCLStatus = () =>
  api.get<CLDetailedStatus>("/continual-learning/status").then(r => r.data);
export const fetchCLTasks = () =>
  api.get<CLTaskRecord[]>("/continual-learning/tasks").then(r => r.data);
export const fetchCLForgettingHistory = () =>
  api.get<CLForgettingHistory>("/continual-learning/forgetting-rate").then(r => r.data);
export const fetchCLReplayStats = () =>
  api.get<CLReplayStats>("/continual-learning/replay-buffer").then(r => r.data);
export const fetchCLEWCStats = () =>
  api.get<CLEWCStats>("/continual-learning/ewc-stats").then(r => r.data);
export const triggerCLUpdate = (req: CLTriggerRequest) =>
  api.post<CLTriggerResponse>("/continual-learning/trigger-update", req).then(r => r.data);

