import axios from "axios";

const isDevPort =
  typeof window !== "undefined" &&
  (window.location.port === "5173" || window.location.port === "3000");
const BASE = isDevPort ? "http://localhost:8000/api/v1" : "/api/v1";

// Legacy export — preserved for existing pages
export const api = axios.create({
  baseURL: BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Auth-aware client — sends httpOnly cookies automatically
export const apiClient = axios.create({
  baseURL: BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
  withCredentials: true,   // ← CRITICAL: sends synapse_access / synapse_refresh cookies
});

// Shared response interceptor
const errHandler = (err: any) => {
  console.error("[API Error]", err?.response?.status, err?.config?.url);
  return Promise.reject(err);
};

api.interceptors.response.use(r => r, errHandler);
apiClient.interceptors.response.use(r => r, errHandler);
