import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { useLiveAnomalies } from "./hooks/useLiveAnomalies";
import Dashboard from "./pages/Dashboard";
import GraphPage from "./pages/GraphPage";
import IncidentList from "./pages/IncidentList";
import IncidentDetail from "./pages/IncidentDetail";
import SimulatePage from "./pages/SimulatePage";
import ModelStatusPage from "./pages/ModelStatus";

function AppInner() {
  useLiveAnomalies(); // Start WebSocket globally
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/"            element={<Dashboard />} />
        <Route path="/graph"       element={<GraphPage />} />
        <Route path="/incidents"   element={<IncidentList />} />
        <Route path="/incidents/:id" element={<IncidentDetail />} />
        <Route path="/simulate"    element={<SimulatePage />} />
        <Route path="/model"       element={<ModelStatusPage />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  );
}
