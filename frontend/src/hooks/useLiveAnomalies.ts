import { useEffect, useRef } from "react";
import { useStore } from "../store";

export function useLiveAnomalies() {
  const ws = useRef<WebSocket | null>(null);
  const setScores = useStore((s) => s.setAnomalyScores);
  const setWsConnected = useStore((s) => s.setWsConnected);

  useEffect(() => {
    const connect = () => {
      try {
        ws.current = new WebSocket("ws://localhost:8000/api/v1/live");

        ws.current.onopen = () => {
          setWsConnected(true);
          ws.current?.send("ping");
        };

        ws.current.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === "anomaly_update") setScores(msg.scores ?? {});
          } catch { /* ignore parse errors */ }
        };

        ws.current.onclose = () => {
          setWsConnected(false);
          setTimeout(connect, 3000); // auto-reconnect
        };

        ws.current.onerror = () => ws.current?.close();
      } catch {
        setTimeout(connect, 3000);
      }
    };

    connect();
    return () => {
      ws.current?.close();
      ws.current = null;
    };
  }, []);
}
