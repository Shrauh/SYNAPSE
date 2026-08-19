import { useEffect, useRef, useCallback } from "react";
import { useStore } from "../store";

export function useLiveAnomalies() {
  const ws = useRef<WebSocket | null>(null);
  const cancelled = useRef(false);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const setScores = useStore((s) => s.setAnomalyScores);
  const setWsConnected = useStore((s) => s.setWsConnected);

  const connect = useCallback(() => {
    if (cancelled.current) return;

    // Close any existing connection first
    if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
      ws.current.onclose = null; // prevent auto-reconnect on deliberate close
      ws.current.close();
    }

    try {
      ws.current = new WebSocket("ws://localhost:8000/api/v1/live");

      ws.current.onopen = () => {
        if (cancelled.current) { ws.current?.close(); return; }
        setWsConnected(true);
        // Only send if OPEN (readyState === 1)
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send("ping");
        }
      };

      ws.current.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "anomaly_update") setScores(msg.scores ?? {});
        } catch { /* ignore */ }
      };

      ws.current.onclose = () => {
        setWsConnected(false);
        if (!cancelled.current) {
          retryTimer.current = setTimeout(connect, 4000);
        }
      };

      ws.current.onerror = () => {
        // onerror always fires before onclose — just close cleanly
        ws.current?.close();
      };
    } catch {
      if (!cancelled.current) {
        retryTimer.current = setTimeout(connect, 4000);
      }
    }
  }, [setScores, setWsConnected]);

  useEffect(() => {
    cancelled.current = false;
    connect();

    return () => {
      cancelled.current = true;
      if (retryTimer.current) clearTimeout(retryTimer.current);
      ws.current?.close();
      ws.current = null;
    };
  }, [connect]);
}
