import axios from "axios";

const isDevPort = typeof window !== "undefined" && (window.location.port === "5173" || window.location.port === "3000");

export const api = axios.create({
  baseURL: isDevPort ? "http://localhost:8000/api/v1" : "/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Auto-retry on network errors
api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("[API Error]", err?.response?.status, err?.config?.url);
    return Promise.reject(err);
  }
);
