import { create } from "zustand";
import type { IncidentSummary } from "../types/api";

export interface RcaResult {
  incidentId?: string;
  service: string;
  confidence: number | null;
  faultType?: string;
  propagationChain?: string;
  severity?: string;
  explanation?: string;
  recommendedActions?: string[];
  recoveryAction?: string;
  recoveryCommand?: string;
  recoverySuccess?: boolean;
  recoveryTarget?: string;
}

interface AppStore {
  anomalyScores: Record<string, number>;
  wsConnected: boolean;
  incidents: IncidentSummary[];
  latestRca: RcaResult | null;
  setAnomalyScores: (s: Record<string, number>) => void;
  setWsConnected: (v: boolean) => void;
  setIncidents: (i: IncidentSummary[]) => void;
  addIncident: (i: IncidentSummary) => void;
  setLatestRca: (rca: RcaResult | null) => void;
}

export const useStore = create<AppStore>((set) => ({
  anomalyScores: {},
  wsConnected: false,
  incidents: [],
  latestRca: null,
  setAnomalyScores: (anomalyScores) => set({ anomalyScores }),
  setWsConnected: (wsConnected) => set({ wsConnected }),
  setIncidents: (incidents) => set({ incidents }),
  addIncident: (i) => set((s) => ({ incidents: [i, ...s.incidents] })),
  setLatestRca: (latestRca) => set({ latestRca }),
}));

