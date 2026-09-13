import { create } from "zustand";
import type { IncidentSummary } from "../types/api";

interface AppStore {
  anomalyScores: Record<string, number>;
  wsConnected: boolean;
  incidents: IncidentSummary[];
  theme: "dark" | "light";
  setAnomalyScores: (s: Record<string, number>) => void;
  setWsConnected: (v: boolean) => void;
  setIncidents: (i: IncidentSummary[]) => void;
  addIncident: (i: IncidentSummary) => void;
  toggleTheme: () => void;
}

export const useStore = create<AppStore>((set) => ({
  anomalyScores: {},
  wsConnected: false,
  incidents: [],
  theme: "dark",
  setAnomalyScores: (anomalyScores) => set({ anomalyScores }),
  setWsConnected: (wsConnected) => set({ wsConnected }),
  setIncidents: (incidents) => set({ incidents }),
  addIncident: (i) => set((s) => ({ incidents: [i, ...s.incidents] })),
  toggleTheme: () => set((s) => {
    const next = s.theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    return { theme: next };
  }),
}));
