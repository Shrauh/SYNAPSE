import axios from "axios";

export const api = axios.create({
  baseURL: "http://localhost:8000/api/v1",
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
