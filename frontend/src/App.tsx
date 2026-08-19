import { useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { useLiveAnomalies } from "./hooks/useLiveAnomalies";
import Dashboard from "./pages/Dashboard";
import GraphPage from "./pages/GraphPage";
import IncidentList from "./pages/IncidentList";
import IncidentDetail from "./pages/IncidentDetail";
import SimulatePage from "./pages/SimulatePage";
import ModelStatusPage from "./pages/ModelStatus";
import { useStore } from "./store";
import { useState } from "react";

function AppInner() {
  useLiveAnomalies();
  const [collapsed, setCollapsed] = useState(false);
  const theme = useStore(s => s.theme);

  // Apply theme attribute to <html> on mount and changes
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <div className="app-shell">
      {/* Animated background blobs — hidden in light mode */}
      <div className="bg-blobs">
        <div className="bg-blob bg-blob-1" />
        <div className="bg-blob bg-blob-2" />
        <div className="bg-blob bg-blob-3" />
      </div>
      <div className="grid-dots" />

      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(v => !v)} />

      <main
        className={`app-main ${collapsed ? "sidebar-closed" : "sidebar-open"}`}
        style={{ position: "relative", zIndex: 1 }}
      >
        <Routes>
          <Route path="/"              element={<Dashboard />} />
          <Route path="/graph"         element={<GraphPage />} />
          <Route path="/incidents"     element={<IncidentList />} />
          <Route path="/incidents/:id" element={<IncidentDetail />} />
          <Route path="/simulate"      element={<SimulatePage />} />
          <Route path="/model"         element={<ModelStatusPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  );
}
