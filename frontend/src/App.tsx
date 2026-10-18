import React, { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar, TopBar } from "./components/Layout";
import { useLiveAnomalies } from "./hooks/useLiveAnomalies";

// Existing pages (preserved — not replaced)
import Dashboard from "./pages/Dashboard";
import GraphPage from "./pages/GraphPage";
import IncidentList from "./pages/IncidentList";
import IncidentDetail from "./pages/IncidentDetail";
import SimulatePage from "./pages/SimulatePage";
import ModelStatusPage from "./pages/ModelStatus";
import EvaluationPage from "./pages/EvaluationPage";
import AlertsPage from "./pages/AlertsPage";
import LogsPage from "./pages/LogsPage";
import NotificationsPage from "./pages/NotificationsPage";

// P1 — new enterprise pages (additive)
import ActionsWorkspace from "./pages/ActionsWorkspace";
import PlatformHealthPage from "./pages/PlatformHealthPage";
import AuditPage from "./pages/AuditPage";

// Approval queue — simple redirect to incidents list filtered
function ApprovalQueuePage() {
  return (
    <div style={{ padding: "32px", maxWidth: 720, margin: "0 auto" }}>
      <h1 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
        Approval Queue
      </h1>
      <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "24px" }}>
        Actions currently awaiting operator approval are shown here.
        Go to an incident, open its Actions Workspace, then approve or reject pending actions.
      </p>
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "20px" }}>
        <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
          💡 Navigate to{" "}
          <a href="/incidents" style={{ color: "var(--primary)" }}>Incident Explorer</a>
          {" "}→ open an incident → click "Actions" in the detail view.
        </p>
      </div>
    </div>
  );
}

function AppInner() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  useLiveAnomalies(); // Start WebSocket globally — preserved

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--bg-primary)",
        color: "var(--text-primary)",
        display: "flex",
      }}
    >
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(c => !c)}
      />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        <TopBar />
        <main style={{ flex: 1, overflowY: "auto" }}>
          <Routes>
            {/* Existing routes — all preserved */}
            <Route path="/" element={<Dashboard />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/incidents" element={<IncidentList />} />
            <Route path="/incidents/:id" element={<IncidentDetail />} />
            <Route path="/simulate" element={<SimulatePage />} />
            <Route path="/model" element={<ModelStatusPage />} />
            <Route path="/evaluation" element={<EvaluationPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />

            {/* P1 — new routes (additive) */}
            {/* Actions workspace: reached from incident detail OR directly */}
            <Route path="/incidents/:id/actions" element={<ActionsWorkspace />} />
            <Route path="/actions" element={
              <div style={{ padding: "32px", color: "var(--text-muted)" }}>
                Select an incident first to view its actions.{" "}
                <a href="/incidents" style={{ color: "var(--primary)" }}>Go to Incidents →</a>
              </div>
            } />
            <Route path="/approval-queue" element={<ApprovalQueuePage />} />
            <Route path="/platform" element={<PlatformHealthPage />} />
            <Route path="/audit" element={<AuditPage />} />
          </Routes>
        </main>
      </div>
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
