import axios from "axios";

// Use relative URLs so Vite proxy handles routing to backend
export const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.warn("[SYNAPSE API]", err?.response?.status ?? "network error", err?.config?.url);
    return Promise.reject(err);
  }
);
