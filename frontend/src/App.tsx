import React, { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar, TopBar } from "./components/Layout";
import { useLiveAnomalies } from "./hooks/useLiveAnomalies";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import { Cyber3DProvider, Cyber3DBackground } from "./components/Cyber3DBackground";
import "./styles/auth.css";

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

// Auth pages
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import ForgotPasswordPage from "./pages/auth/ForgotPasswordPage";
import ResetPasswordPage from "./pages/auth/ResetPasswordPage";
import ProfilePage from "./pages/auth/ProfilePage";

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
        background: "transparent",
        color: "var(--text-primary)",
        display: "flex",
        position: "relative",
      }}
    >
      <Cyber3DBackground />

      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(c => !c)}
      />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden", position: "relative", zIndex: 1 }}>
        <TopBar />
        <main style={{ flex: 1, overflowY: "auto" }}>
          <Routes>
            {/* ── Public auth routes ── */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />

            {/* ── Protected routes ── */}
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/graph" element={<ProtectedRoute><GraphPage /></ProtectedRoute>} />
            <Route path="/incidents" element={<ProtectedRoute><IncidentList /></ProtectedRoute>} />
            <Route path="/incidents/:id" element={<ProtectedRoute><IncidentDetail /></ProtectedRoute>} />
            <Route path="/incidents/:id/actions" element={<ProtectedRoute><ActionsWorkspace /></ProtectedRoute>} />
            <Route path="/simulate" element={<ProtectedRoute><SimulatePage /></ProtectedRoute>} />
            <Route path="/model" element={<ProtectedRoute><ModelStatusPage /></ProtectedRoute>} />
            <Route path="/evaluation" element={<ProtectedRoute><EvaluationPage /></ProtectedRoute>} />
            <Route path="/alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />
            <Route path="/logs" element={<ProtectedRoute><LogsPage /></ProtectedRoute>} />
            <Route path="/notifications" element={<ProtectedRoute><NotificationsPage /></ProtectedRoute>} />
            <Route path="/approval-queue" element={<ProtectedRoute><ApprovalQueuePage /></ProtectedRoute>} />
            <Route path="/platform" element={<ProtectedRoute><PlatformHealthPage /></ProtectedRoute>} />
            <Route path="/audit" element={<ProtectedRoute requiredRole="admin"><AuditPage /></ProtectedRoute>} />
            <Route path="/actions" element={<ProtectedRoute><div style={{ padding: "32px", color: "var(--text-muted)" }}>Select an incident first. <a href="/incidents" style={{ color: "var(--primary)" }}>Go to Incidents →</a></div></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Cyber3DProvider>
          <AppInner />
        </Cyber3DProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
