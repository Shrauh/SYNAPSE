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

// Kubernetes Cluster
export const getK8sPods = async (): Promise<any> => {
  const res = await fetch("http://localhost:8000/api/v1/k8s/pods");
  if (!res.ok) throw new Error('Failed to fetch pods');
  return res.json();
};

export const injectK8sFault = async (service: string, faultType: string = 'pod_kill'): Promise<any> => {
  const res = await fetch("http://localhost:8000/api/v1/k8s/inject-fault", {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service, fault_type: faultType })
  });
  if (!res.ok) throw new Error('Failed to inject fault');
  return res.json();
};

export const recoverK8sService = async (service: string, action: string = 'restart_pod'): Promise<any> => {
  const res = await fetch("http://localhost:8000/api/v1/k8s/recover", {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service, action })
  });
  if (!res.ok) throw new Error('Recovery failed');
  return res.json();
};

