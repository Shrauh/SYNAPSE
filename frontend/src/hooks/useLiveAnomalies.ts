import { useEffect, useRef } from "react";
import { useStore, type RcaResult } from "../store";

export function useLiveAnomalies() {
  const ws = useRef<WebSocket | null>(null);
  const setScores = useStore((s) => s.setAnomalyScores);
  const setWsConnected = useStore((s) => s.setWsConnected);
  const setLatestRca = useStore((s) => s.setLatestRca);

  useEffect(() => {
    let unmounted = false;

    const connect = () => {
      if (unmounted) return;
      try {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const host = window.location.port === "5173" || window.location.port === "3000"
          ? "localhost:8000"
          : (window.location.host || "localhost:8000");
        ws.current = new WebSocket(`${protocol}//${host}/api/v1/live`);

        ws.current.onopen = () => {
          if (unmounted) return;
          setWsConnected(true);
          ws.current?.send("ping");
        };

        ws.current.onmessage = (e) => {
          if (unmounted) return;
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === "anomaly_update" && msg.scores) {
              setScores(msg.scores);
            } else if (msg.type === "rca_complete") {
              if (msg.anomaly_scores) {
                setScores(msg.anomaly_scores);
              }
              const rootCause = msg.root_cause || (msg.anomaly_scores ? Object.entries(msg.anomaly_scores).sort((a: any, b: any) => b[1] - a[1])[0]?.[0] : null) || "unknown";
              const conf = typeof msg.confidence === "number" ? msg.confidence : null;
              const rcaData: RcaResult = {
                incidentId: msg.incident_id,
                service: rootCause,
                confidence: conf,
                faultType: msg.fault_type,
                propagationChain: msg.propagation_chain,
                severity: msg.severity || "HIGH",
                explanation: msg.explanation,
                recommendedActions: msg.recommended_actions || [],
                recoveryAction: msg.recovery_action && msg.recovery_action !== "none" ? msg.recovery_action : undefined,
                recoveryCommand: msg.recovery_command,
                recoverySuccess: msg.recovery_action && msg.recovery_action !== "none" ? true : undefined,
                recoveryTarget: rootCause,
              };
              setLatestRca(rcaData);
            }
          } catch { /* ignore parse errors */ }
        };

        ws.current.onclose = () => {
          if (unmounted) return;
          setWsConnected(false);
          setTimeout(connect, 3000); // auto-reconnect
        };

        ws.current.onerror = () => ws.current?.close();
      } catch {
        if (!unmounted) setTimeout(connect, 3000);
      }
    };

    connect();
    return () => {
      unmounted = true;
      ws.current?.close();
      ws.current = null;
    };
  }, [setScores, setWsConnected, setLatestRca]);
}
