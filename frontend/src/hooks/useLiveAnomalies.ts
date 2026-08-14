import { useEffect, useRef } from "react";
import { useStore } from "../store";

const WS_URL = `ws://${window.location.hostname}:8000/api/v1/live`;

/**
 * useLiveAnomalies — global WebSocket hook for real-time dashboard updates.
 *
 * Connects to the SYNAPSE backend WebSocket and:
 *   1. Updates the Zustand store with anomaly scores
 *   2. Dispatches custom DOM events for component-local listeners
 *   3. Auto-reconnects on disconnect with exponential backoff
 *
 * Message types handled:
 *   - anomaly_update: Per-service scores
 *   - incident_detected: New incident
 *   - rca_complete: RCA pipeline finished
 *   - remediation_executed: CQL agent acted
 *   - initial_state: First-connect snapshot
 *   - graph_update: Service graph topology
 */
export function useLiveAnomalies() {
  const ws = useRef<WebSocket | null>(null);
  const reconnectDelay = useRef(1000);
  const setAnomalyScores = useStore(s => s.setAnomalyScores);
  const setConnected = useStore(s => s.setWsConnected);
  const addIncident = useStore(s => s.addLiveIncident);

  useEffect(() => {
    let alive = true;

    const connect = () => {
      if (!alive) return;

      try {
        const socket = new WebSocket(WS_URL);
        ws.current = socket;

        socket.onopen = () => {
          reconnectDelay.current = 1000;
          setConnected(true);
          console.log("[WS] Connected to SYNAPSE");
        };

        socket.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            const { type, data, timestamp } = msg;

            // Dispatch custom event for component-level listeners
            window.dispatchEvent(
              new CustomEvent("synapse_ws_event", {
                detail: { type, data, timestamp },
              })
            );

            // Update global Zustand store
            switch (type) {
              case "anomaly_update":
                if (data?.services) {
                  const scores: Record<string, number> = {};
                  data.services.forEach((s: { id: string; anomaly_score: number }) => {
                    scores[s.id] = s.anomaly_score;
                  });
                  setAnomalyScores(scores);
                }
                break;

              case "initial_state":
                if (data?.graph?.nodes) {
                  const scores: Record<string, number> = {};
                  data.graph.nodes.forEach((n: { id: string; anomaly_score: number }) => {
                    scores[n.id] = n.anomaly_score;
                  });
                  setAnomalyScores(scores);
                }
                break;

              case "incident_detected":
                if (data) {
                  addIncident(data);
                }
                break;

              case "pong":
              case "keepalive":
                // Heartbeat — no action needed
                break;
            }
          } catch (e) {
            // Ignore malformed messages
          }
        };

        socket.onclose = () => {
          setConnected(false);
          ws.current = null;
          if (alive) {
            // Exponential backoff: 1s → 2s → 4s → 8s (max)
            console.log(`[WS] Disconnected. Reconnecting in ${reconnectDelay.current}ms...`);
            setTimeout(connect, reconnectDelay.current);
            reconnectDelay.current = Math.min(reconnectDelay.current * 2, 8000);
          }
        };

        socket.onerror = () => {
          socket.close();
        };

        // Ping every 25 seconds to keep alive
        const pingInterval = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send("ping");
          }
        }, 25_000);

        return () => clearInterval(pingInterval);
      } catch (e) {
        console.warn("[WS] Connection failed:", e);
        if (alive) {
          setTimeout(connect, reconnectDelay.current);
          reconnectDelay.current = Math.min(reconnectDelay.current * 2, 8000);
        }
      }
    };

    connect();

    return () => {
      alive = false;
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
      setConnected(false);
    };
  }, []);
}
