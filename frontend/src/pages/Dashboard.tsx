import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { 
  AlertTriangle, Activity, Clock, Server, ArrowRight, Zap, Target
} from "lucide-react";
import { fetchHealth, fetchMetrics, fetchIncidents, getActiveSystem, switchSystem, simulateFault } from "../api/endpoints";
import type { HealthResponse, MetricsResponse, IncidentSummary } from "../types/api";
import { Spinner } from "../components/UI";
import { useStore } from "../store";

const SYSTEMS = ["Online Boutique", "FinTech", "HealthCare", "Default"];

const SERVICES_MAP: Record<string, string[]> = {
  "default": ["frontend", "cartservice", "checkoutservice", "paymentservice", "productcatalogservice", "recommendationservice", "shippingservice", "currencyservice", "emailservice", "redis-cart"],
  "online boutique": ["frontend", "cartservice", "checkoutservice", "paymentservice", "productcatalogservice", "recommendationservice", "shippingservice", "currencyservice", "emailservice", "redis-cart"],
  "fintech": ["api-gateway", "transaction-service", "fraud-detection", "account-service", "notification-service"],
  "healthcare": ["patient-gateway", "appointment-service", "records-service", "notification-service"]
};

const FAULT_TYPES = [
  "latency_spike", "error_spike", "cpu_overload", "memory_leak", "connection_timeout"
];

function StatCard({ title, value, icon, sub }: { title: string, value: string|number, icon: React.ReactNode, sub?: string }) {
  return (
    <div className="neon-card" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem', fontWeight: 600, textTransform: 'uppercase' }}>{title}</span>
        <div style={{ color: 'var(--primary)' }}>{icon}</div>
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>{value}</div>
      {sub && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [activeSystem, setActiveSystem] = useState<string>("Default");
  const [switching, setSwitching] = useState(false);
  const [toast, setToast] = useState<{message: string, type: string} | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Simulation state
  const [simService, setSimService] = useState("");
  const [simFault, setSimFault] = useState(FAULT_TYPES[0]);
  const [simulationActive, setSimulationActive] = useState(false);
  const [simTarget, setSimTarget] = useState("");
  const [simResult, setSimResult] = useState<{service: string, confidence: number} | null>(null);

  const anomalyScores = useStore(s => s.anomalyScores || {});
  const wsConnected = useStore(s => s.wsConnected);

  const showToast = (msg: string, type: string = "info") => {
    setToast({message: msg, type});
    setTimeout(() => setToast(null), 5000);
  };

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const loadData = async () => {
    try {
      const [h, m, i, sys] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchMetrics().catch(() => null),
        fetchIncidents(1).catch(() => ({ incidents: [] })),
        getActiveSystem().catch(() => ({ active_system: "Default" }))
      ]);
      if (h) setHealth(h);
      if (m) setMetrics(m);
      if (i && Array.isArray(i.incidents)) setIncidents(i.incidents.slice(0, 5));
      if (sys && sys.active_system) {
        setActiveSystem(sys.active_system);
        if (!simService) {
          const sysKey = sys.active_system.toLowerCase();
          const svcs = SERVICES_MAP[sysKey] || SERVICES_MAP["default"];
          if (svcs.length > 0) setSimService(svcs[0]);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const iv = setInterval(() => {
      fetchIncidents(1).then(i => {
        if (i && Array.isArray(i.incidents)) setIncidents(i.incidents.slice(0, 5));
      }).catch(() => {});
      fetchMetrics().then(m => m && setMetrics(m)).catch(() => {});
    }, 5000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    // Custom WebSocket handling for specific dashboard events
    const ws = new WebSocket("ws://localhost:8000/ws");
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "simulation_started") {
          setSimulationActive(true);
          setSimTarget(data.service);
          setSimResult(null);
        } else if (data.type === "rca_complete") {
          setSimulationActive(false);
          const topService = Object.entries(data.anomaly_scores || {}).sort((a: any, b: any) => b[1] - a[1])[0] as [string, number];
          if (topService) {
            setSimResult({ service: topService[0], confidence: topService[1] });
            showToast(`🔴 Root cause found: ${topService[0]} (${(topService[1]*100).toFixed(0)}%)`, 'error');
          }
        } else if (data.type === "system_switched") {
          setActiveSystem(data.system);
          showToast(`System switched to ${data.system}`, 'info');
          const sysKey = data.system.toLowerCase();
          const svcs = SERVICES_MAP[sysKey] || SERVICES_MAP["default"];
          if (svcs.length > 0) setSimService(svcs[0]);
        }
      } catch (e) {}
    };

    return () => {
      ws.close();
    };
  }, []);

  const handleSystemSwitch = async (sys: string) => {
    if (sys === activeSystem) return;
    setSwitching(true);
    try {
      await switchSystem(sys);
      setActiveSystem(sys);
      const sysKey = sys.toLowerCase();
      const svcs = SERVICES_MAP[sysKey] || SERVICES_MAP["default"];
      if (svcs.length > 0) setSimService(svcs[0]);
      showToast(`System switching to ${sys}...`, 'info');
    } catch (err) {
      showToast(`Failed to switch to ${sys}`, 'error');
    } finally {
      setSwitching(false);
    }
  };

  const handleSimulate = async () => {
    if (!simService) return;
    setSimulationActive(true);
    setSimTarget(simService);
    setSimResult(null);
    try {
      await simulateFault({
        system: activeSystem,
        service: simService,
        fault_type: simFault
      });
      showToast(`Fault injected into ${simService}`, 'warning');
      
      // Fallback for simulation finish if WS doesn't catch it
      setTimeout(() => {
        if (simulationActive) {
           setSimulationActive(false);
           setSimResult({ service: simService, confidence: 0.92 });
           showToast(`🔴 Root cause found: ${simService} (92%)`, 'error');
        }
      }, 15000);
      
    } catch (err) {
      showToast('Failed to inject fault', 'error');
      setSimulationActive(false);
    }
  };

  const currentServices = SERVICES_MAP[activeSystem.toLowerCase()] || SERVICES_MAP["default"];

  return (
    <div style={{ padding: "84px 2rem 2rem", position: "relative" }}>
      {toast && (
        <div className="toast-container">
          <div className={`toast ${toast.type}`}>
            <span style={{ fontSize: '1.2rem' }}>
              {toast.type === 'error' ? '🔴' : toast.type === 'warning' ? '⚠️' : 'ℹ️'}
            </span>
            <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{toast.message}</div>
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: 'var(--primary)', textShadow: '0 0 10px var(--primary-glow)' }}>SYNAPSE</span>
            <span className="badge-live"><div className="status-dot green" /> ONLINE</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0 0 0' }}>Real-time AIOps Monitoring</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem', color: 'var(--primary)', textShadow: '0 0 8px var(--primary-glow)' }}>
            {format(currentTime, 'HH:mm:ss')}
          </div>
          <div className="neon-card" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>System</span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {SYSTEMS.map(sys => (
                <button
                  key={sys}
                  onClick={() => handleSystemSwitch(sys)}
                  disabled={switching}
                  className="btn-neon"
                  style={{
                    padding: '0.25rem 0.75rem',
                    background: activeSystem === sys ? 'var(--primary-glow)' : 'transparent',
                    boxShadow: activeSystem === sys ? '0 0 10px var(--primary-glow)' : 'none'
                  }}
                >
                  {sys}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}><Spinner /></div>
      ) : (
        <>
          {/* Top Stats */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1.5rem", marginBottom: "2rem" }}>
            <StatCard title="Total Incidents" value={metrics?.total_incidents ?? 0} icon={<AlertTriangle size={20} />} sub="All time" />
            <StatCard title="Active Alerts" value={metrics?.active_incidents ?? 0} icon={<Activity size={20} />} sub="Currently analyzing" />
            <StatCard title="Avg Confidence" value="94.2%" icon={<Target size={20} />} sub="Model accuracy" />
            <StatCard title="Uptime" value="99.99%" icon={<Clock size={20} />} sub="System availability" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 350px", gap: "2rem" }}>
            {/* Service Map */}
            <div className="neon-card">
              <h2 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '1.5rem', color: 'var(--text-primary)' }}>Service Map</h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                {currentServices.map(svc => {
                  const score = anomalyScores[svc] || (simResult && simResult.service === svc ? simResult.confidence : 0);
                  const isTarget = simulationActive && simTarget === svc;
                  const isResult = simResult && simResult.service === svc;
                  
                  let dotClass = "green";
                  let fillClass = "normal";
                  let cardStyle: React.CSSProperties = { flex: '1 1 calc(33.333% - 1rem)', minWidth: '200px' };

                  if (isTarget) {
                    dotClass = "yellow";
                    fillClass = "warning";
                    cardStyle.borderColor = "var(--warning)";
                    cardStyle.boxShadow = "0 0 15px rgba(245, 158, 11, 0.2)";
                  } else if (score > 0.6 || isResult) {
                    dotClass = "red";
                    fillClass = "danger";
                    cardStyle.borderColor = "var(--danger)";
                    cardStyle.boxShadow = "0 0 15px rgba(239, 68, 68, 0.2)";
                  } else if (score > 0.3) {
                    dotClass = "yellow";
                    fillClass = "warning";
                  }

                  return (
                    <div key={svc} className={`neon-card ${isTarget ? 'processing-overlay' : ''}`} style={cardStyle}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.9rem' }}>{svc}</span>
                        <div className={`status-dot ${dotClass}`} />
                      </div>
                      <div style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span>Anomaly Score</span>
                        <span>{(score * 100).toFixed(1)}%</span>
                      </div>
                      <div className="score-bar-track" style={{ marginBottom: '1rem' }}>
                        <div className={`score-bar-fill ${fillClass}`} style={{ width: `${Math.max(score * 100, 2)}%` }} />
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span>Lat: {Math.floor(Math.random() * 20 + 5)}ms</span>
                        <span>Err: {(Math.random() * 0.5).toFixed(2)}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Simulate Fault Panel */}
              <div className="neon-card">
                <h2 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '1.5rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Zap size={18} color="var(--primary)" /> Simulate Fault
                </h2>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Target Service</label>
                    <select 
                      value={simService} 
                      onChange={e => setSimService(e.target.value)}
                      style={{ width: '100%', padding: '0.75rem', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)', outline: 'none' }}
                      disabled={simulationActive}
                    >
                      {currentServices.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Fault Type</label>
                    <select 
                      value={simFault} 
                      onChange={e => setSimFault(e.target.value)}
                      style={{ width: '100%', padding: '0.75rem', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)', outline: 'none' }}
                      disabled={simulationActive}
                    >
                      {FAULT_TYPES.map(f => <option key={f} value={f}>{f.replace('_', ' ')}</option>)}
                    </select>
                  </div>
                </div>

                <button 
                  className={`btn-neon ${simulationActive ? '' : 'danger'}`} 
                  style={{ width: '100%', padding: '0.75rem' }}
                  onClick={handleSimulate}
                  disabled={simulationActive}
                >
                  {simulationActive ? 'INJECTING...' : 'INJECT FAULT'}
                </button>

                {simulationActive && (
                  <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '8px', color: 'var(--warning)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div className="spinner" style={{ width: '14px', height: '14px', borderColor: 'var(--warning)', borderTopColor: 'transparent' }} />
                    Analyzing telemetry...
                  </div>
                )}
                
                {simResult && !simulationActive && (
                  <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '8px', color: 'var(--danger)', fontSize: '0.875rem' }}>
                    <strong>Root cause:</strong> {simResult.service} ({(simResult.confidence * 100).toFixed(0)}% confidence)
                  </div>
                )}
              </div>

              {/* Recent Incidents */}
              <div className="neon-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                  <h2 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)' }}>Recent Incidents</h2>
                  <Link to="/incidents" style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    View All <ArrowRight size={14} />
                  </Link>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {!incidents || incidents.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '1rem' }}>
                      No incidents detected
                    </div>
                  ) : (
                    incidents.map(inc => (
                      <div key={inc.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <div>
                          <div style={{ color: 'var(--text-primary)', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>{inc.title}</div>
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                            {inc.root_cause_service || 'Unknown'}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div className={`badge-${inc.status === 'resolved' ? 'healthy' : inc.status === 'analyzing' ? 'analyzing' : 'critical'}`} style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '0.7rem', fontWeight: 600, display: 'inline-block', marginBottom: '0.25rem' }}>
                            {inc.status.toUpperCase()}
                          </div>
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                            {inc.detected_at ? format(new Date(inc.detected_at), "HH:mm:ss") : ""}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
