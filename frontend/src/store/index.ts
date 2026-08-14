import { create } from "zustand";
import type { IncidentSummary } from "../types/api";

interface AppStore {
  anomalyScores: Record<string, number>;
  wsConnected: boolean;
  connected: boolean;
  incidents: IncidentSummary[];
  liveIncidents: any[];
  simulateInProgress: boolean;
  theme: "dark" | "light";
  setAnomalyScores: (s: Record<string, number>) => void;
  setWsConnected: (v: boolean) => void;
  setIncidents: (i: IncidentSummary[]) => void;
  addIncident: (i: IncidentSummary) => void;
  addLiveIncident: (i: any) => void;
  setSimulateInProgress: (v: boolean) => void;
  toggleTheme: () => void;
}

export const useStore = create<AppStore>((set) => ({
  anomalyScores: {},
  wsConnected: false,
  connected: false,
  incidents: [],
  liveIncidents: [],
  simulateInProgress: false,
  theme: "dark",
  setAnomalyScores: (anomalyScores) => set({ anomalyScores }),
  setWsConnected: (v) => set({ wsConnected: v, connected: v }),
  setIncidents: (incidents) => set({ incidents }),
  addIncident: (i) => set((s) => ({ incidents: [i, ...s.incidents] })),
  addLiveIncident: (i) => set((s) => ({ liveIncidents: [i, ...s.liveIncidents].slice(0, 50) })),
  setSimulateInProgress: (simulateInProgress) => set({ simulateInProgress }),
  toggleTheme: () => set((s) => {
    const next = s.theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    return { theme: next };
  }),
}));
