import { create } from "zustand";
import type { IncidentSummary } from "../types/api";

interface AppStore {
  anomalyScores: Record<string, number>;
  wsConnected: boolean;
  incidents: IncidentSummary[];
  setAnomalyScores: (s: Record<string, number>) => void;
  setWsConnected: (v: boolean) => void;
  setIncidents: (i: IncidentSummary[]) => void;
  addIncident: (i: IncidentSummary) => void;
}

export const useStore = create<AppStore>((set) => ({
  anomalyScores: {},
  wsConnected: false,
  incidents: [],
  setAnomalyScores: (anomalyScores) => set({ anomalyScores }),
  setWsConnected: (wsConnected) => set({ wsConnected }),
  setIncidents: (incidents) => set({ incidents }),
  addIncident: (i) => set((s) => ({ incidents: [i, ...s.incidents] })),
}));
