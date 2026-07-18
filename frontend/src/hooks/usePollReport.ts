import { useEffect, useState } from "react";
import { fetchReport } from "../api/endpoints";
import type { RCAReport } from "../types/api";

export function usePollReport(incidentId: string, isAnalyzing: boolean) {
  const [report, setReport] = useState<RCAReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    const load = async () => {
      try {
        const data = await fetchReport(incidentId);
        setReport(data);
        setLoading(false);
        clearInterval(interval);
      } catch {
        // Still analyzing — keep polling
      }
    };

    load();
    if (isAnalyzing) {
      interval = setInterval(load, 3000);
    }

    return () => clearInterval(interval);
  }, [incidentId, isAnalyzing]);

  return { report, loading };
}
