import React, { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { 
  AlertTriangle, Activity, Clock, ArrowRight, Zap, Target,
  Plug, X, Check, RefreshCw, RotateCw
} from "lucide-react";
import { 
  fetchHealth, fetchMetrics, fetchIncidents, fetchIncident, fetchReport,
  getActiveSystem, switchSystem, simulateFault, getAvailableSystems,
  testConnection, listConnections, getK8sPods, injectK8sFault, recoverK8sService
} from "../api/endpoints";
import type { HealthResponse, MetricsResponse, IncidentSummary } from "../types/api";
import { useStore } from "../store";

export interface K8sPodItem {
  name: string;
  service: string;
  status: string;
  restarts: number;
}


interface SimResultData {
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

interface SystemOption {
  id: string;
  label: string;
}

const DEFAULT_SYSTEMS: SystemOption[] = [
  { id: "online-boutique", label: "Online Boutique" },
  { id: "fintech", label: "FinTech" },
  { id: "healthcare", label: "HealthCare" },
  { id: "default", label: "Default" },
];

const FALLBACK_SERVICES = ["api-gateway", "auth-service"];

const FAULT_TYPES = [
  "latency_spike", "error_spike", "cpu_overload", "memory_leak", "connection_timeout"
];

function normalizePods(data: any, fallbackServices: string[] = []): K8sPodItem[] {
  if (!data) return [];
  const list: K8sPodItem[] = [];

  if (Array.isArray(data)) {
    data.forEach((item: any) => {
      const name = item.pod_name || item.name || item.id || "unknown-pod";
      const service = item.service || item.app || (typeof name === "string" ? name.split("-")[0] : "unknown");
      list.push({
        name,
        service,
        status: item.status || "Running",
        restarts: typeof item.restarts === "number" ? item.restarts : 0,
      });
    });
  } else if (typeof data === "object") {
    if (Array.isArray(data.pods)) {
      return normalizePods(data.pods, fallbackServices);
    }
    Object.entries(data).forEach(([svc, val]) => {
      if (Array.isArray(val)) {
        val.forEach((p: any) => {
          list.push({
            name: p.pod_name || p.name || `${svc}-${svc.slice(0, 3)}1`,
            service: p.service || svc,
            status: p.status || "Running",
            restarts: typeof p.restarts === "number" ? p.restarts : 0,
          });
        });
      } else if (val && typeof val === "object") {
        const p: any = val;
        list.push({
          name: p.pod_name || p.name || `${svc}-${svc.slice(0, 3)}1`,
          service: p.service || svc,
          status: p.status || "Running",
          restarts: typeof p.restarts === "number" ? p.restarts : 0,
        });
      } else if (typeof val === "string") {
        list.push({
          name: `${svc}-${svc.slice(0, 3)}1`,
          service: svc,
          status: val,
          restarts: 0,
        });
      }
    });
  }

  if (list.length === 0 && fallbackServices.length > 0) {
    return fallbackServices.map(svc => ({
      name: `${svc}-7f4b89-${svc.slice(0, 3)}1`,
      service: svc,
      status: "Running",
      restarts: 0,
    }));
  }

  return list;
}

function getPodStatusMeta(status: string) {
  const s = (status || "").toLowerCase();
  if (s === "running") {
    return {
      dotClass: "green",
      badgeColor: "#10b981",
      badgeBg: "rgba(16, 185, 129, 0.12)",
      badgeBorder: "rgba(16, 185, 129, 0.35)",
      label: "Running",
    };
  }
  if (s.includes("pending") || s.includes("containercreating") || s.includes("init")) {
    return {
      dotClass: "yellow",
      badgeColor: "#f59e0b",
      badgeBg: "rgba(245, 158, 11, 0.12)",
      badgeBorder: "rgba(245, 158, 11, 0.35)",
      label: "Pending",
    };
  }
  return {
    dotClass: "red",
    badgeColor: "#ef4444",
    badgeBg: "rgba(239, 68, 68, 0.12)",
    badgeBorder: "rgba(239, 68, 68, 0.35)",
    label: status === "crashloopbackoff" ? "CrashLoopBackOff" : (status || "Error"),
  };
}


function AnimatedNumber({ value }: { value: string | number }) {
  const [displayValue, setDisplayValue] = useState<number>(() => (typeof value === "number" ? value : 0));
  const [fadeKey, setFadeKey] = useState<number>(0);
  const prevValueRef = useRef<number>(typeof value === "number" ? value : 0);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof value === "number") {
      const start = prevValueRef.current;
      const end = value;
      const duration = 750;
      const startTime = performance.now();

      const updateCount = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (end - start) * ease);
        setDisplayValue(current);

        if (progress < 1) {
          animFrameRef.current = requestAnimationFrame(updateCount);
        } else {
          prevValueRef.current = end;
        }
      };

      animFrameRef.current = requestAnimationFrame(updateCount);
      return () => {
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      };
    } else {
      setFadeKey(prev => prev + 1);
    }
  }, [value]);

  if (typeof value === "number") {
    return <span>{displayValue.toLocaleString()}</span>;
  }

  return (
    <span key={fadeKey} className="fade-in" style={{ display: "inline-block" }}>
      {value}
    </span>
  );
}

function TypewriterText({ text, speed = 18 }: { text: string; speed?: number }) {
  const [displayedText, setDisplayedText] = useState("");
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    setDisplayedText("");
    setIsTyping(true);
    let index = 0;
    const interval = setInterval(() => {
      index++;
      setDisplayedText(text.slice(0, index));
      if (index >= text.length) {
        clearInterval(interval);
        setIsTyping(false);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return (
    <span>
      {displayedText}
      {isTyping && <span className="typewriter-cursor" />}
    </span>
  );
}

function getSeverityDetails(severity?: string) {
  const s = (severity || 'HIGH').toUpperCase();
  if (s.includes('L1') || s.includes('LOW')) {
    return {
      cardClass: 'severity-green',
      badgeBg: 'rgba(16, 185, 129, 0.2)',
      badgeColor: '#10b981',
      badgeBorder: 'rgba(16, 185, 129, 0.5)',
      glowColor: '#10b981'
    };
  }
  if (s.includes('L2') || s.includes('MED') || s.includes('WARN')) {
    return {
      cardClass: 'severity-orange',
      badgeBg: 'rgba(245, 158, 11, 0.2)',
      badgeColor: '#f59e0b',
      badgeBorder: 'rgba(245, 158, 11, 0.5)',
      glowColor: '#f59e0b'
    };
  }
  return {
    cardClass: 'severity-red',
    badgeBg: 'rgba(239, 68, 68, 0.2)',
    badgeColor: '#ef4444',
    badgeBorder: 'rgba(239, 68, 68, 0.5)',
    glowColor: '#ef4444'
  };
}

function StatCard({ title, value, icon, sub }: { title: string, value: string|number, icon: React.ReactNode, sub?: string }) {
  return (
    <div className="neon-card" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem', fontWeight: 600, textTransform: 'uppercase' }}>{title}</span>
        <div style={{ color: 'var(--primary)' }}>{icon}</div>
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
        <AnimatedNumber value={value} />
      </div>
      {sub && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  );
}

const Sparkline = ({ data, color = '#6366f1', width = 80, height = 24 }: { data: number[], color?: string, width?: number, height?: number }) => {
  if (!data || data.length < 2) return null;
  const max = Math.max(...data, 0.1);
  const min = Math.min(...data, 0);
  const range = max - min || 0.1;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={width} height={height} style={{ display: 'block', marginTop: '0.5rem' }}>
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={points} opacity="0.8" />
    </svg>
  );
};

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [apiLatency, setApiLatency] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [activeSystem, setActiveSystem] = useState<string>("Default");
  const [currentServices, setCurrentServices] = useState<string[]>([]);
  const [availableSystems, setAvailableSystems] = useState<SystemOption[]>(DEFAULT_SYSTEMS);
  const [switching, setSwitching] = useState(false);
  const [toast, setToast] = useState<{message: string, type: string} | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Simulation state
  const [simService, setSimService] = useState("");
  const [simFault, setSimFault] = useState(FAULT_TYPES[0]);
  const [simulationActive, setSimulationActive] = useState(false);
  const [simTarget, setSimTarget] = useState("");
  const [simResult, setSimResult] = useState<SimResultData | null>(null);
  const simIncidentIdRef = useRef<string | null>(null);

  // Kubernetes Cluster Pods state
  const [k8sPods, setK8sPods] = useState<K8sPodItem[]>([]);
  const [k8sLoading, setK8sLoading] = useState(true);
  const [k8sRefreshing, setK8sRefreshing] = useState(false);
  const [killingPod, setKillingPod] = useState<string | null>(null);
  const [restartingPod, setRestartingPod] = useState<string | null>(null);

  const anomalyScores = useStore(s => s.anomalyScores || {});
  const latestRca = useStore(s => s.latestRca);
  const [scoreHistory, setScoreHistory] = useState<Record<string, number[]>>({});

  const simServiceRef = useRef(simService);
  simServiceRef.current = simService;
  const simFaultRef = useRef(simFault);
  simFaultRef.current = simFault;

  useEffect(() => {
    if (latestRca) {
      setSimResult(latestRca);
      setSimulationActive(false);
      showToast(
        `🔴 Root cause found: ${latestRca.service}${latestRca.confidence !== null ? ` (${(latestRca.confidence * 100).toFixed(0)}%)` : ''}`,
        'error'
      );
      fetchIncidents(1).then(i => {
        if (i && Array.isArray(i.incidents)) {
          setIncidents(i.incidents.slice(0, 5));
          if (i.incidents.length > 0) {
            fetchIncident(i.incidents[0].id).then(incDetail => {
              if (incDetail?.anomaly_scores && Object.keys(incDetail.anomaly_scores).length > 0) {
                useStore.getState().setAnomalyScores(incDetail.anomaly_scores);
              }
            }).catch(() => {});
          }
        }
      }).catch(() => {});
    }
  }, [latestRca]);

  useEffect(() => {
    // Pre-populate initial score history so sparklines appear immediately
    setScoreHistory(prev => {
      const next = { ...prev };
      let changed = false;
      for (const svc of currentServices) {
        if (!next[svc] || next[svc].length < 2) {
          const realScore = anomalyScores[svc] ?? anomalyScores[svc.toLowerCase()];
          const score = typeof realScore === "number"
            ? realScore
            : (simResult && simResult.service === svc ? (simResult.confidence ?? 0) : 0);
          next[svc] = Array.from({ length: 8 }, () => score);
          changed = true;
        }
      }
      return changed ? next : prev;
    });

    const interval = setInterval(() => {
      setScoreHistory(prev => {
        const next = { ...prev };
        for (const svc of currentServices) {
          const realScore = anomalyScores[svc] ?? anomalyScores[svc.toLowerCase()];
          const score = typeof realScore === "number"
            ? realScore
            : (simResult && simResult.service === svc ? (simResult.confidence ?? 0) : 0);
          const history = [...(prev[svc] || []), score];
          next[svc] = history.slice(-20); // Keep last 20 points
        }
        return next;
      });
    }, 3000);
    return () => clearInterval(interval);
  }, [currentServices, anomalyScores, simResult]);


  // Connect Your System modal
  const [connectModalOpen, setConnectModalOpen] = useState(false);
  const [connName, setConnName] = useState("my-prometheus");
  const [connType, setConnType] = useState("prometheus");
  const [connUrl, setConnUrl] = useState("http://localhost:9090");
  const [connApiKey, setConnApiKey] = useState("");
  const [connNamespace, setConnNamespace] = useState("default");
  const [connTesting, setConnTesting] = useState(false);
  const [connResult, setConnResult] = useState<{ status: string; message: string; latency_ms: number } | null>(null);
  const [savedConnections, setSavedConnections] = useState<{ name: string; type: string; url: string; status: string; latency_ms: number; last_checked: string }[]>([]);

  const handleTestConnection = async () => {
    setConnTesting(true);
    setConnResult(null);
    try {
      const res = await testConnection({
        name: connName,
        type: connType,
        url: connUrl,
        api_key: connApiKey || undefined,
        namespace: connNamespace || undefined,
      });
      setConnResult({ status: res.status, message: res.message, latency_ms: res.latency_ms });
      // Refresh saved connections
      const conns = await listConnections();
      if (Array.isArray(conns)) setSavedConnections(conns);
    } catch {
      setConnResult({ status: "failed", message: "Could not reach SYNAPSE backend", latency_ms: 0 });
    } finally {
      setConnTesting(false);
    }
  };

  // Load saved connections when modal opens
  useEffect(() => {
    if (connectModalOpen) {
      listConnections().then(conns => {
        if (Array.isArray(conns)) setSavedConnections(conns);
      }).catch(() => {});
    }
  }, [connectModalOpen]);

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
      const t0 = performance.now();
      const [h, m, i, sys] = await Promise.all([
        fetchHealth().then(res => {
          setApiLatency(Math.round(performance.now() - t0));
          return res;
        }).catch(() => {
          setApiLatency(null);
          return null;
        }),
        fetchMetrics().catch(() => null),
        fetchIncidents(1).catch(() => ({ incidents: [] })),
        getActiveSystem().catch(() => null)
      ]);
      if (h) setHealth(h);
      if (m) setMetrics(m);
      if (i && Array.isArray(i.incidents)) {
        setIncidents(i.incidents.slice(0, 5));
        if (i.incidents.length > 0) {
          fetchIncident(i.incidents[0].id).then(incDetail => {
            if (incDetail?.anomaly_scores && Object.keys(incDetail.anomaly_scores).length > 0) {
              useStore.getState().setAnomalyScores(incDetail.anomaly_scores);
            }
          }).catch(() => {});
        }
      }
      if (sys && sys.system) {
        setActiveSystem(sys.system);
        if (sys.services && sys.services.length > 0) {
          setCurrentServices(sys.services);
          if (!simService) setSimService(sys.services[0]);
        }
      } else {
        setCurrentServices(prev => (prev.length > 0 ? prev : FALLBACK_SERVICES));
        if (!simService) setSimService(FALLBACK_SERVICES[0]);
      }

      getAvailableSystems().then(res => {
        if (res && res.available && res.available.length > 0) {
          const sysList: SystemOption[] = res.available.map(a => ({
            id: a.id,
            label: a.id === "online-boutique" ? "Online Boutique" :
                   a.id === "fintech" ? "FinTech" :
                   a.id === "healthcare" ? "HealthCare" :
                   a.id === "default" ? "Default" :
                   a.label || a.id
          }));
          setAvailableSystems(sysList);
        }
      }).catch(() => {});
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const iv = setInterval(() => {
      const t0 = performance.now();
      fetchHealth().then(h => {
        setApiLatency(Math.round(performance.now() - t0));
        if (h) setHealth(h);
      }).catch(() => {
        setApiLatency(null);
      });
      fetchIncidents(1).then(i => {
        if (i && Array.isArray(i.incidents)) {
        setIncidents(i.incidents.slice(0, 5));
        if (i.incidents.length > 0) {
          fetchIncident(i.incidents[0].id).then(incDetail => {
            if (incDetail?.anomaly_scores && Object.keys(incDetail.anomaly_scores).length > 0) {
              useStore.getState().setAnomalyScores(incDetail.anomaly_scores);
            }
          }).catch(() => {});
        }
      }
      }).catch(() => {});
      fetchMetrics().then(m => m && setMetrics(m)).catch(() => {});
    }, 5000);
    return () => clearInterval(iv);
  }, []);

  // Fetch active system services dynamically on mount and when active system changes
  useEffect(() => {
    let mounted = true;
    getActiveSystem()
      .then(sys => {
        if (!mounted) return;
        if (sys?.services && sys.services.length > 0) {
          setCurrentServices(sys.services);
          setSimService(prev => (sys.services.includes(prev) ? prev : sys.services[0]));
        } else {
          setCurrentServices(FALLBACK_SERVICES);
          setSimService(prev => (FALLBACK_SERVICES.includes(prev) ? prev : FALLBACK_SERVICES[0]));
        }
      })
      .catch(() => {
        if (!mounted) return;
        setCurrentServices(prev => (prev.length > 0 ? prev : FALLBACK_SERVICES));
        setSimService(prev => (prev ? prev : FALLBACK_SERVICES[0]));
      });

    return () => {
      mounted = false;
    };
  }, [activeSystem]);

  const loadCompletedRCA = async (incidentId: string, wsData?: any) => {
    try {
      const [inc, rep] = await Promise.all([
        fetchIncident(incidentId).catch(() => null),
        fetchReport(incidentId).catch(() => null)
      ]);
      const service = rep?.root_cause?.service || inc?.root_cause?.service || wsData?.root_cause || wsData?.service || simServiceRef.current;
      const confidence = (typeof rep?.root_cause?.confidence === 'number' && rep.root_cause.confidence > 0)
        ? rep.root_cause.confidence
        : ((typeof inc?.root_cause?.confidence === 'number' && inc.root_cause.confidence > 0)
          ? inc.root_cause.confidence
          : (typeof wsData?.confidence === 'number' ? wsData.confidence : null));
      const faultType = rep?.root_cause?.fault_type || inc?.root_cause?.fault_type || wsData?.fault_type || simFaultRef.current;
      const propagationChain = rep?.propagation_chain || wsData?.propagation_chain || (inc?.affected_services && inc.affected_services.length > 0 ? `${service} → ${inc.affected_services.join(' → ')}` : undefined);
      const severity = rep?.severity?.level || inc?.severity || wsData?.severity || 'HIGH';
      const explanation = rep?.explanation || wsData?.explanation;
      const recommendedActions = rep?.recommended_actions || wsData?.recommended_actions || [];
      const recoveryAction = rep?.recovery?.action_type || rep?.recovery?.action || (wsData?.recovery_action && wsData.recovery_action !== 'none' ? wsData.recovery_action : undefined);
      const recoveryCommand = rep?.recovery?.kubectl_command || wsData?.recovery_command || undefined;
      const recoverySuccess = rep?.recovery ? rep.recovery.success : (recoveryAction ? true : undefined);
      const recoveryTarget = rep?.recovery?.target || (recoveryAction ? service : undefined);

      if (inc?.anomaly_scores && Object.keys(inc.anomaly_scores).length > 0) {
        useStore.getState().setAnomalyScores(inc.anomaly_scores);
      } else if (wsData?.anomaly_scores) {
        useStore.getState().setAnomalyScores(wsData.anomaly_scores);
      }

      setSimResult({
        incidentId,
        service,
        confidence,
        faultType,
        propagationChain,
        severity,
        explanation,
        recommendedActions,
        recoveryAction,
        recoveryCommand,
        recoverySuccess,
        recoveryTarget,
      });
    } catch {
      if (wsData?.anomaly_scores) {
        useStore.getState().setAnomalyScores(wsData.anomaly_scores);
      }
      setSimResult({
        incidentId,
        service: wsData?.root_cause || wsData?.service || simServiceRef.current,
        confidence: typeof wsData?.confidence === 'number' ? wsData.confidence : null,
        faultType: wsData?.fault_type || simFaultRef.current,
        propagationChain: wsData?.propagation_chain,
        severity: wsData?.severity || 'HIGH',
        explanation: wsData?.explanation,
        recommendedActions: wsData?.recommended_actions || [],
        recoveryAction: wsData?.recovery_action && wsData.recovery_action !== 'none' ? wsData.recovery_action : undefined,
        recoveryCommand: wsData?.recovery_command,
        recoverySuccess: wsData?.recovery_action && wsData.recovery_action !== 'none' ? true : undefined,
        recoveryTarget: wsData?.root_cause || wsData?.service || simServiceRef.current,
      });
    }
  };

  const fetchPodsData = async (isManual = false) => {
    if (isManual) setK8sRefreshing(true);
    try {
      const data = await getK8sPods();
      const parsed = normalizePods(data, currentServices);
      setK8sPods(parsed);
    } catch (err) {
      console.error("Failed to load K8s pods", err);
      setK8sPods(prev => {
        if (prev.length > 0) return prev;
        const svcs = currentServices.length > 0 ? currentServices : FALLBACK_SERVICES;
        return svcs.map(svc => ({
          name: `${svc}-7f4b89-${svc.slice(0, 3)}1`,
          service: svc,
          status: "Running",
          restarts: 0,
        }));
      });
    } finally {
      setK8sLoading(false);
      if (isManual) setTimeout(() => setK8sRefreshing(false), 500);
    }
  };

  // Poll Kubernetes pods every 10 seconds and on mount / currentServices change
  useEffect(() => {
    fetchPodsData();
    const interval = setInterval(() => {
      fetchPodsData();
    }, 10000);
    return () => clearInterval(interval);
  }, [currentServices]);

  const handleKillPod = async (service: string, podName: string) => {
    setKillingPod(podName);
    try {
      const k8sRes = await injectK8sFault(service, "pod_kill");
      showToast(`Pod ${podName} killed! Simulating failure on ${service}...`, "error");

      // Optimistically mark pod as crashed in UI
      setK8sPods(prev =>
        prev.map(p =>
          p.name === podName || p.service === service
            ? { ...p, status: "CrashLoopBackOff", restarts: p.restarts + 1 }
            : p
        )
      );

      // Trigger simulation flow
      setSimService(service);
      setSimFault("pod_kill");
      setSimulationActive(true);
      setSimTarget(service);
      setSimResult(null);

      let incidentId = k8sRes?.incident_id;
      if (!incidentId) {
        try {
          const simRes = await simulateFault({
            fault_type: "error_spike",
            root_cause_service: service,
            severity: "critical",
            duration_minutes: 3
          });
          incidentId = simRes?.incident_id;
        } catch {}
      }

      if (incidentId) {
        simIncidentIdRef.current = incidentId;
        // Wait for RCA pipeline to provide real results via API if WebSocket doesn't catch it
        let attempts = 0;
        const maxAttempts = 15;
        const pollInterval = setInterval(async () => {
          attempts++;
          try {
            const report = await fetchReport(incidentId!).catch(() => null);
            if (report && report.root_cause && report.root_cause.service) {
              clearInterval(pollInterval);
              setSimulationActive(false);
              await loadCompletedRCA(incidentId!);
              const conf = typeof report.root_cause.confidence === 'number' ? report.root_cause.confidence : null;
              showToast(
                `🔴 Root cause found: ${report.root_cause.service}${conf !== null ? ` (${(conf * 100).toFixed(0)}%)` : ''}`,
                'error'
              );
              return;
            }
          } catch {}

          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            if (simulationActive) {
              const inc = await fetchIncident(incidentId!).catch(() => null);
              if (inc?.root_cause?.service) {
                setSimulationActive(false);
                await loadCompletedRCA(incidentId!);
              } else {
                setSimulationActive(false);
                showToast(`RCA pipeline timed out for ${service}`, 'warning');
              }
            }
          }
        }, 2000);
      }

      setTimeout(() => fetchPodsData(), 1200);
    } catch (err) {
      showToast(`Failed to kill pod ${podName}`, "error");
    } finally {
      setKillingPod(null);
    }
  };

  const handleRestartPod = async (service: string, podName: string) => {
    setRestartingPod(podName);
    try {
      await recoverK8sService(service, "restart_pod");
      showToast(`Pod for ${service} restarted and recovered`, "info");

      // Optimistically restore pod in UI
      setK8sPods(prev =>
        prev.map(p =>
          p.name === podName || p.service === service
            ? { ...p, status: "Running" }
            : p
        )
      );

      // Clear simulation if this service was targeted
      if (simTarget === service) {
        setSimulationActive(false);
        setSimResult(null);
        setSimTarget("");
      }

      setTimeout(() => fetchPodsData(), 1200);
    } catch (err) {
      showToast(`Failed to recover pod for ${service}`, "error");
    } finally {
      setRestartingPod(null);
    }
  };



  useEffect(() => {
    // Custom WebSocket handling for specific dashboard events
    let ws: WebSocket | null = null;
    let unmounted = false;

    const connect = () => {
      if (unmounted) return;
      try {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const host = window.location.port === "5173" || window.location.port === "3000"
          ? "localhost:8000"
          : (window.location.host || "localhost:8000");
        ws = new WebSocket(`${protocol}//${host}/api/v1/live`);

        ws.onmessage = (event) => {
          if (unmounted) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === "simulation_started") {
              setSimulationActive(true);
              const target = data.root_cause_service || data.service || simServiceRef.current;
              setSimTarget(target);
              if (data.incident_id) {
                simIncidentIdRef.current = data.incident_id;
              }
              setSimResult(null);
            } else if (data.type === "k8s_fault_injected") {
              setSimulationActive(true);
              const target = data.service || simServiceRef.current;
              setSimTarget(target);
              if (data.incident_id) {
                simIncidentIdRef.current = data.incident_id;
              }
              setSimResult(null);
            } else if (data.type === "rca_complete") {
              setSimulationActive(false);
              if (data.anomaly_scores) {
                useStore.getState().setAnomalyScores(data.anomaly_scores);
              }
              const incId = data.incident_id || simIncidentIdRef.current;
              const topService = data.root_cause || (data.anomaly_scores ? Object.entries(data.anomaly_scores).sort((a: any, b: any) => b[1] - a[1])[0]?.[0] : null) || simServiceRef.current;
              const conf = typeof data.confidence === 'number' ? data.confidence : null;

              if (incId) {
                loadCompletedRCA(incId, data);
              } else {
                setSimResult({
                  incidentId: incId,
                  service: topService,
                  confidence: conf,
                  faultType: data.fault_type || simFaultRef.current,
                  propagationChain: data.propagation_chain,
                  severity: data.severity || 'HIGH',
                  explanation: data.explanation,
                  recommendedActions: data.recommended_actions || [],
                  recoveryAction: data.recovery_action && data.recovery_action !== 'none' ? data.recovery_action : undefined,
                  recoveryCommand: data.recovery_command,
                  recoverySuccess: data.recovery_action && data.recovery_action !== 'none' ? true : undefined,
                  recoveryTarget: topService,
                });
              }
              showToast(`🔴 Root cause found: ${topService}${conf !== null ? ` (${(conf * 100).toFixed(0)}%)` : ''}`, 'error');

              fetchIncidents(1).then(i => {
                if (i && Array.isArray(i.incidents)) {
                  setIncidents(i.incidents.slice(0, 5));
                  if (i.incidents.length > 0) {
                    fetchIncident(i.incidents[0].id).then(incDetail => {
                      if (incDetail?.anomaly_scores && Object.keys(incDetail.anomaly_scores).length > 0) {
                        useStore.getState().setAnomalyScores(incDetail.anomaly_scores);
                      }
                    }).catch(() => {});
                  }
                }
              }).catch(() => {});
            } else if (data.type === "anomaly_update") {
              if (data.scores) {
                useStore.getState().setAnomalyScores(data.scores);
              }
            } else if (data.type === "system_switched") {
              setActiveSystem(data.system);
              useStore.getState().setAnomalyScores({});
              setSimResult(null);
              setSimTarget("");
              if (data.services && data.services.length > 0) {
                setCurrentServices([...data.services]);
                setSimService(data.services[0]);
              }
              showToast(`System switched to ${data.system}`, 'info');
            }
          } catch (e) {}
        };

        ws.onclose = () => {
          if (!unmounted) setTimeout(connect, 3000);
        };
      } catch {
        if (!unmounted) setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      unmounted = true;
      ws?.close();
    };
  }, []);

  const handleSystemSwitch = async (sys: string) => {
    const sysId = sys.toLowerCase().replace(/ /g, "-");
    const currentId = activeSystem.toLowerCase().replace(/ /g, "-");
    if (sysId === currentId) return;
    setSwitching(true);
    try {
      await switchSystem(sysId);
      setActiveSystem(sys);
      useStore.getState().setAnomalyScores({});
      setSimResult(null);
      setSimTarget("");
      // Refresh services from backend
      const updated = await getActiveSystem();
      if (updated && updated.services) {
        setCurrentServices([...updated.services]);
        if (updated.services.length > 0) setSimService(updated.services[0]);
      }
      showToast(`System switched to ${sys}`, 'info');
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
      const res = await simulateFault({
        fault_type: simFault,
        root_cause_service: simService,
        severity: "high",
        duration_minutes: 3
      });
      if (res?.incident_id) {
        simIncidentIdRef.current = res.incident_id;
        const incidentId = res.incident_id;

        // Wait for RCA pipeline to provide real results via API if WebSocket doesn't catch it
        let attempts = 0;
        const maxAttempts = 15;
        const pollInterval = setInterval(async () => {
          attempts++;
          try {
            const report = await fetchReport(incidentId).catch(() => null);
            if (report && report.root_cause && report.root_cause.service) {
              clearInterval(pollInterval);
              setSimulationActive(false);
              await loadCompletedRCA(incidentId);
              const conf = typeof report.root_cause.confidence === 'number' ? report.root_cause.confidence : null;
              showToast(
                `🔴 Root cause found: ${report.root_cause.service}${conf !== null ? ` (${(conf * 100).toFixed(0)}%)` : ''}`,
                'error'
              );
              return;
            }
          } catch {}

          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            if (simulationActive) {
              const inc = await fetchIncident(incidentId).catch(() => null);
              if (inc?.root_cause?.service) {
                setSimulationActive(false);
                await loadCompletedRCA(incidentId);
              } else {
                setSimulationActive(false);
                showToast(`RCA pipeline timed out for ${simService}`, 'warning');
              }
            }
          }
        }, 2000);
      }
      showToast(`Fault injected into ${simService}`, 'warning');
    } catch (err) {
      showToast('Failed to inject fault', 'error');
      setSimulationActive(false);
    }
  };

  const isHealthy = health?.status === "healthy" || health?.status === "up";

  const avgConfidenceDisplay = (() => {
    if (metrics?.avg_confidence != null) {
      return typeof metrics.avg_confidence === "number"
        ? `${metrics.avg_confidence}%`
        : `${metrics.avg_confidence}`;
    }
    const confs = incidents
      .map(i => i.confidence)
      .filter((c): c is number => typeof c === "number" && c > 0);
    if (confs.length > 0) {
      return `${((confs.reduce((a, b) => a + b, 0) / confs.length) * 100).toFixed(1)}%`;
    }
    return "N/A";
  })();

  const uptimeDisplay = (() => {
    if (metrics?.uptime) return metrics.uptime;
    if (health?.uptime_seconds != null) {
      const s = health.uptime_seconds;
      return s < 3600 ? `${Math.floor(s / 60)}m ${Math.floor(s % 60)}s` : `${(s / 3600).toFixed(1)}h`;
    }
    return "N/A";
  })();

  return (
    <div className="dashboard-bg" style={{ padding: "84px 2rem 2rem", position: "relative", minHeight: "100vh" }}>
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

      {/* Connect Your System Modal */}
      {connectModalOpen && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => setConnectModalOpen(false)}>
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: 'linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(241, 245, 249, 0.95))',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              borderRadius: '16px',
              padding: '2rem',
              width: '600px',
              maxHeight: '85vh',
              overflowY: 'auto',
              boxShadow: '0 0 60px rgba(99, 102, 241, 0.1), 0 25px 50px rgba(0, 0, 0, 0.06)',
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                  width: '40px', height: '40px', borderRadius: '12px',
                  background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2))',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                }}>
                  <Plug size={20} color="#6366f1" />
                </div>
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>Connect Your System</h2>
                  <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>Link Prometheus, Kubernetes, or any webhook</p>
                </div>
              </div>
              <button onClick={() => setConnectModalOpen(false)} style={{
                background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)',
                borderRadius: '8px', padding: '0.4rem', cursor: 'pointer', color: 'var(--text-muted)',
              }}><X size={18} /></button>
            </div>

            {/* Connection Form */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
              {/* Row 1: Name + Type */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Connection Name</label>
                  <input
                    value={connName} onChange={e => setConnName(e.target.value)}
                    placeholder="my-prometheus"
                    style={{ width: '100%', padding: '0.6rem 0.75rem', background: 'rgba(99,102,241,0.04)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)', outline: 'none', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>System Type</label>
                  <select
                    value={connType} onChange={e => {
                      setConnType(e.target.value);
                      if (e.target.value === 'prometheus') setConnUrl('http://localhost:9090');
                      else if (e.target.value === 'alertmanager') setConnUrl('http://localhost:9093');
                      else if (e.target.value === 'kubernetes') setConnUrl('https://kubernetes.default.svc');
                      else setConnUrl('http://');
                    }}
                    style={{ width: '100%', padding: '0.6rem 0.75rem', background: 'rgba(99,102,241,0.04)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)', outline: 'none', fontSize: '0.85rem', boxSizing: 'border-box' }}
                  >
                    <option value="prometheus">Prometheus</option>
                    <option value="alertmanager">Alertmanager</option>
                    <option value="kubernetes">Kubernetes API</option>
                    <option value="webhook">Custom Webhook</option>
                  </select>
                </div>
              </div>

              {/* Row 2: URL */}
              <div>
                <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Endpoint URL</label>
                <input
                  value={connUrl} onChange={e => setConnUrl(e.target.value)}
                  placeholder="http://localhost:9090"
                  style={{ width: '100%', padding: '0.6rem 0.75rem', background: 'rgba(99,102,241,0.04)', border: '1px solid var(--border)', borderRadius: '8px', color: '#6366f1', outline: 'none', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', boxSizing: 'border-box' }}
                />
              </div>

              {/* Row 3: API Key + Namespace */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>API Key / Token <span style={{ opacity: 0.5 }}>(optional)</span></label>
                  <input
                    type="password"
                    value={connApiKey} onChange={e => setConnApiKey(e.target.value)}
                    placeholder="Bearer token..."
                    style={{ width: '100%', padding: '0.6rem 0.75rem', background: 'rgba(99,102,241,0.04)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)', outline: 'none', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Namespace <span style={{ opacity: 0.5 }}>(K8s)</span></label>
                  <input
                    value={connNamespace} onChange={e => setConnNamespace(e.target.value)}
                    placeholder="default"
                    style={{ width: '100%', padding: '0.6rem 0.75rem', background: 'rgba(99,102,241,0.04)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)', outline: 'none', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', boxSizing: 'border-box' }}
                  />
                </div>
              </div>
            </div>

            {/* Test Connection Button */}
            <button
              onClick={handleTestConnection}
              disabled={connTesting || !connUrl}
              className="btn-neon"
              style={{
                width: '100%', padding: '0.75rem', marginBottom: '1rem',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
                background: connTesting ? 'rgba(99,102,241,0.05)' : 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15))',
                border: '1px solid rgba(99, 102, 241, 0.4)',
                color: '#6366f1', fontWeight: 700, fontSize: '0.9rem',
              }}
            >
              {connTesting ? (
                <><div className="spinner" style={{ width: '14px', height: '14px', borderColor: '#6366f1', borderTopColor: 'transparent' }} /> Testing Connection...</>
              ) : (
                <><Zap size={16} /> Test Connection</>
              )}
            </button>

            {/* Connection Result */}
            {connResult && (
              <div style={{
                padding: '0.85rem 1rem', borderRadius: '10px', marginBottom: '1rem',
                background: connResult.status === 'connected'
                  ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                border: `1px solid ${connResult.status === 'connected'
                  ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
              }}>
                <div style={{
                  width: '28px', height: '28px', borderRadius: '50%', flexShrink: 0,
                  background: connResult.status === 'connected'
                    ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginTop: '2px',
                }}>
                  {connResult.status === 'connected'
                    ? <Check size={14} color="#10b981" />
                    : <X size={14} color="#ef4444" />
                  }
                </div>
                <div>
                  <div style={{
                    fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.25rem',
                    color: connResult.status === 'connected' ? '#10b981' : '#ef4444',
                  }}>
                    {connResult.status === 'connected' ? '✓ Connected Successfully' : '✗ Connection Failed'}
                    {connResult.latency_ms > 0 && (
                      <span style={{ fontWeight: 500, fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                        {connResult.latency_ms}ms
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                    {connResult.message}
                  </div>
                </div>
              </div>
            )}

            {/* Saved Connections */}
            {savedConnections.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
                  Saved Connections
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {savedConnections.map(c => (
                    <div key={c.name} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '0.5rem 0.75rem', borderRadius: '8px',
                      background: 'rgba(255,255,255,0.5)', border: '1px solid var(--border)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div className={`status-dot ${c.status === 'connected' ? 'green' : 'red'}`} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-primary)', fontWeight: 600 }}>{c.name}</span>
                        <span style={{
                          fontSize: '0.65rem', padding: '1px 6px', borderRadius: '4px',
                          background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)',
                          color: '#818cf8', textTransform: 'uppercase',
                        }}>{c.type}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          {c.latency_ms}ms
                        </span>
                        <span style={{
                          fontSize: '0.65rem', padding: '1px 6px', borderRadius: '4px',
                          background: c.status === 'connected' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                          color: c.status === 'connected' ? '#10b981' : '#ef4444',
                          fontWeight: 600,
                        }}>
                          {c.status === 'connected' ? 'LIVE' : 'OFFLINE'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Footer Tip */}
            <div style={{
              padding: '0.75rem 1rem', borderRadius: '10px',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.05))',
              border: '1px solid rgba(99, 102, 241, 0.15)',
              fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.5,
            }}>
              <span style={{ color: '#6366f1', fontWeight: 600 }}>No live cluster?</span>{' '}
              Use the <strong style={{ color: 'var(--text-primary)' }}>Simulate Fault</strong> panel to inject synthetic faults — the AI pipeline runs the same GNN + Causal + LLM analysis on simulated data.
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: 'var(--primary)' }}>SYNAPSE</span>
            <span className="badge-live" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
              <div className={`status-dot ${isHealthy ? 'green' : 'red'}`} />
              <span>{health ? (health.status === 'healthy' ? 'ONLINE' : health.status.toUpperCase()) : 'OFFLINE'}</span>
            </span>
            {apiLatency !== null && (
              <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontWeight: 500, background: 'rgba(255,255,255,0.5)', padding: '2px 8px', borderRadius: '4px', border: '1px solid var(--border)' }}>
                {apiLatency}ms API
              </span>
            )}
          </h1>
          <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0 0 0' }}>Real-time AIOps Monitoring</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem', color: 'var(--primary)' }}>
            {format(currentTime, 'HH:mm:ss')}
          </div>
          <div className="neon-card" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>System</span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {availableSystems.map(sys => {
                const isSelected = activeSystem.toLowerCase() === sys.id.toLowerCase() ||
                  activeSystem.toLowerCase() === sys.label.toLowerCase() ||
                  activeSystem.toLowerCase().replace(/ /g, "-") === sys.id.toLowerCase();
                return (
                  <button
                    key={sys.id}
                    onClick={() => handleSystemSwitch(sys.label)}
                    disabled={switching}
                    className="btn-neon"
                    style={{
                      padding: '0.25rem 0.75rem',
                      background: isSelected ? 'var(--primary-glow)' : 'transparent',
                      boxShadow: isSelected ? '0 0 10px var(--primary-glow)' : 'none'
                    }}
                  >
                    {sys.label}
                  </button>
                );
              })}
            </div>
          </div>
          <button
            onClick={() => setConnectModalOpen(true)}
            className="btn-neon"
            style={{
              padding: '0.4rem 1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15))',
              border: '1px solid rgba(99, 102, 241, 0.4)',
              color: '#6366f1',
              fontWeight: 600,
              fontSize: '0.8rem',
              whiteSpace: 'nowrap',
            }}
          >
            <Plug size={14} /> Connect Your System
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1.5rem", marginBottom: "2rem" }}>
          {[1,2,3,4].map(i => (
            <div key={i} className="skeleton-card">
              <div className="skeleton-line w-50" />
              <div className="skeleton-line h-lg w-75" />
              <div className="skeleton-line w-40" />
            </div>
          ))}
        </div>
      ) : (
        <>
          {/* Top Stats */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1.5rem", marginBottom: "2rem" }}>
            <StatCard title="Total Incidents" value={metrics?.total_incidents ?? 0} icon={<AlertTriangle size={20} />} sub="All time" />
            <StatCard title="Active Alerts" value={metrics?.active_incidents ?? 0} icon={<Activity size={20} />} sub="Currently analyzing" />
            <StatCard title="Avg Confidence" value={avgConfidenceDisplay} icon={<Target size={20} />} sub="Model accuracy" />
            <StatCard title="Uptime" value={uptimeDisplay} icon={<Clock size={20} />} sub="System availability" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 350px", gap: "2rem" }}>
            {/* Service Map */}
            <div className="neon-card">
              <h2 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '1.5rem', color: 'var(--text-primary)' }}>Service Map</h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                {currentServices.map(svc => {
                  const realScore = anomalyScores[svc] ?? anomalyScores[svc.toLowerCase()];
                  const score = typeof realScore === "number"
                    ? realScore
                    : (simResult && simResult.service === svc ? (simResult.confidence ?? 0) : 0);
                  const isTarget = simulationActive && (simTarget === svc || (!simTarget && simService === svc));
                  const isResult = Boolean(simResult && simResult.service === svc);
                  
                  let dotClass = "green";
                  let fillClass = "normal";
                  const cardStyle: React.CSSProperties = { 
                    flex: '1 1 calc(33.333% - 1rem)', 
                    minWidth: '200px',
                    transition: 'all 0.3s ease'
                  };

                  let statusLabel = "HEALTHY";
                  let statusColor = "var(--success)";
                  let statusBg = "rgba(16, 185, 129, 0.12)";
                  let statusBorder = "rgba(16, 185, 129, 0.3)";

                  if (isTarget) {
                    dotClass = "yellow";
                    fillClass = "warning";
                    cardStyle.borderColor = "var(--warning)";
                    cardStyle.boxShadow = "0 0 20px rgba(245, 158, 11, 0.4)";
                    cardStyle.animation = "pulse-warn 1.5s infinite";
                    statusLabel = "INJECTING";
                    statusColor = "var(--warning)";
                    statusBg = "rgba(245, 158, 11, 0.15)";
                    statusBorder = "rgba(245, 158, 11, 0.4)";
                  } else if (score > 0.6 || isResult) {
                    dotClass = "red";
                    fillClass = "danger";
                    cardStyle.borderColor = "var(--danger)";
                    cardStyle.boxShadow = "0 0 18px rgba(239, 68, 68, 0.3)";
                    statusLabel = "CRITICAL";
                    statusColor = "var(--danger)";
                    statusBg = "rgba(239, 68, 68, 0.15)";
                    statusBorder = "rgba(239, 68, 68, 0.4)";
                  } else if (score > 0.3) {
                    dotClass = "yellow";
                    fillClass = "warning";
                    statusLabel = "WARNING";
                    statusColor = "var(--warning)";
                    statusBg = "rgba(245, 158, 11, 0.15)";
                    statusBorder = "rgba(245, 158, 11, 0.4)";
                  }

                  return (
                    <div key={svc} className={`neon-card ${isTarget ? 'processing-overlay fault-ripple' : ''}`} style={cardStyle}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.95rem' }}>{svc}</span>
                        <div className={`status-dot ${dotClass}`} />
                      </div>
                      <div style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span>Anomaly Score</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: score > 0.3 ? statusColor : 'var(--text-muted)' }}>
                          {(score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <Sparkline data={scoreHistory[svc] || []} color={score > 0.3 ? '#ef4444' : '#6366f1'} />
                      <div className="score-bar-track" style={{ marginBottom: '1rem' }}>
                        <div className={`score-bar-fill ${fillClass}`} style={{ width: `${Math.max(score * 100, 2)}%` }} />
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Status</span>
                        <span style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          fontFamily: 'var(--font-mono)',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          color: statusColor,
                          background: statusBg,
                          border: `1px solid ${statusBorder}`,
                          textTransform: 'uppercase'
                        }}>
                          {statusLabel}
                        </span>
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
                      style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.5)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)', outline: 'none' }}
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
                      style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.5)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)', outline: 'none' }}
                      disabled={simulationActive}
                    >
                      {FAULT_TYPES.map(f => <option key={f} value={f}>{f.replace('_', ' ')}</option>)}
                    </select>
                  </div>
                </div>

                <button 
                  className={`btn-neon ${simulationActive ? 'fault-ripple' : 'danger'}`} 
                  style={{ width: '100%', padding: '0.75rem', position: 'relative' }}
                  onClick={handleSimulate}
                  disabled={simulationActive}
                >
                  {simulationActive ? 'INJECTING FAULT...' : 'INJECT FAULT'}
                </button>

                {simulationActive && (
                  <div className="fault-ripple" style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '8px', color: 'var(--warning)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem', position: 'relative' }}>
                    <div className="spinner" style={{ width: '14px', height: '14px', borderColor: 'var(--warning)', borderTopColor: 'transparent' }} />
                    Injecting telemetry fault into <strong style={{ color: 'var(--text-primary)' }}>{simTarget || simService}</strong>...
                  </div>
                )}
                
                {simResult && !simulationActive && (() => {
                  const sevInfo = getSeverityDetails(simResult.severity);
                  return (
                    <div className={`neon-card rca-severity-card ${sevInfo.cardClass}`} style={{
                      marginTop: '1.25rem',
                      padding: '1.25rem',
                      boxShadow: '0 0 25px rgba(99,102,241,0.04)'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: sevInfo.badgeColor }}>
                          ROOT CAUSE ANALYSIS COMPLETE
                        </span>
                        {simResult.severity && (
                          <span style={{
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '12px',
                            background: sevInfo.badgeBg,
                            color: sevInfo.badgeColor,
                            border: `1px solid ${sevInfo.badgeBorder}`,
                            textTransform: 'uppercase'
                          }}>
                            {simResult.severity}
                          </span>
                        )}
                      </div>

                      <div style={{
                        fontSize: '1.4rem',
                        fontWeight: 800,
                        fontFamily: 'var(--font-mono)',
                        color: sevInfo.badgeColor,
                        textShadow: `0 0 14px ${sevInfo.glowColor}66`,
                        marginBottom: '0.75rem',
                        wordBreak: 'break-all'
                      }}>
                        {simResult.service}
                      </div>

                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                        {simResult.confidence != null ? (
                        <div style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          background: simResult.confidence > 0.8 ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)',
                          border: `1px solid ${simResult.confidence > 0.8 ? '#ef4444' : '#f59e0b'}`,
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: simResult.confidence > 0.8 ? '#f87171' : '#fbbf24'
                        }}>
                          <span>Confidence:</span>
                          <span style={{ fontFamily: 'var(--font-mono)' }}>{(simResult.confidence * 100).toFixed(0)}%</span>
                        </div>
                        ) : (
                        <div style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          background: 'rgba(99,102,241,0.15)',
                          border: '1px solid rgba(99,102,241,0.3)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: '#a5b4fc'
                        }}>
                          <span>Confidence:</span>
                          <span style={{ fontFamily: 'var(--font-mono)' }}>Analyzing...</span>
                        </div>
                        )}

                        {simResult.faultType && (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: 'rgba(99,102,241,0.15)',
                            border: '1px solid rgba(99,102,241,0.4)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            color: '#818cf8',
                            textTransform: 'capitalize'
                          }}>
                            {simResult.faultType.replace(/_/g, ' ')}
                          </div>
                        )}
                      </div>

                      {/* Propagation Chain Visual */}
                      {simResult?.propagationChain && (
                        <div style={{ margin: '16px 0', padding: '16px', background: 'rgba(99,102,241,0.06)', borderRadius: 12, border: '1px solid rgba(99,102,241,0.15)' }}>
                          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 10 }}>Failure Propagation Chain</div>
                          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                            {(simResult.propagationChain.includes(' → ') ? simResult.propagationChain.split(' → ') : simResult.propagationChain.split(/\s*(?:→|->)\s*/).filter(Boolean)).map((svc: string, i: number, arr: string[]) => (
                              <React.Fragment key={`${svc}-${i}`}>
                                <span style={{
                                  padding: '6px 14px',
                                  borderRadius: 20,
                                  fontSize: 13,
                                  fontWeight: 600,
                                  background: i === 0 ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.12)',
                                  color: i === 0 ? '#ef4444' : '#f59e0b',
                                  border: `1px solid ${i === 0 ? 'rgba(239,68,68,0.3)' : 'rgba(245,158,11,0.25)'}`,
                                }}>
                                  {i === 0 && '⚠ '}{svc}
                                </span>
                                {i < arr.length - 1 && (
                                  <span style={{ color: 'var(--text-tertiary)', fontSize: 18, fontWeight: 700 }}>→</span>
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      )}

                      <div style={{ marginBottom: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5, background: 'rgba(255, 255, 255, 0.75)', boxShadow: '0 1px 4px rgba(99,102,241,0.06)', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--primary)', textTransform: 'uppercase', marginBottom: '0.35rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <Zap size={12} /> AI Diagnosis
                        </div>
                        <TypewriterText text={simResult.explanation || `Algorithmic analysis confirmed root cause anomaly in ${simResult.service}. Degradation profile matches ${simResult.faultType?.replace(/_/g, ' ') || 'injected fault'}${simResult.confidence != null ? ` with ${(simResult.confidence * 100).toFixed(0)}% model certainty` : '. Computing confidence score'}.`} />
                      </div>

                      {/* Auto-Recovery Action Status */}
                      {((simResult.recoveryAction && simResult.recoveryAction !== 'none') || simResult.recoveryCommand) && (
                        <div style={{
                          margin: '16px 0',
                          padding: '12px 14px',
                          background: 'rgba(99,102,241,0.06)',
                          borderRadius: 10,
                          border: '1px solid rgba(99,102,241,0.2)',
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#818cf8', display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span>⚡</span> Auto-Recovery Action
                            </div>
                            <span style={{
                              fontSize: 11,
                              fontWeight: 700,
                              fontFamily: 'var(--font-mono)',
                              padding: '2px 8px',
                              borderRadius: 4,
                              background: simResult.recoverySuccess !== false ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                              color: simResult.recoverySuccess !== false ? '#10b981' : '#f59e0b',
                              border: `1px solid ${simResult.recoverySuccess !== false ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                            }}>
                              {simResult.recoverySuccess !== false ? '✓ EXECUTED' : '⏳ PENDING'}
                            </span>
                          </div>
                          {simResult.recoveryAction && simResult.recoveryAction !== 'none' && (
                            <div style={{ fontSize: 12, color: 'var(--text-primary)', marginBottom: simResult.recoveryCommand ? 8 : 0, display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span style={{ color: 'var(--text-muted)' }}>Action:</span>
                              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#818cf8', background: 'rgba(99,102,241,0.12)', padding: '2px 6px', borderRadius: 4 }}>
                                {simResult.recoveryAction.replace(/_/g, ' ')}
                              </span>
                              {simResult.recoveryTarget && (
                                <span style={{ color: 'var(--text-muted)' }}>
                                  on <strong style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{simResult.recoveryTarget}</strong>
                                </span>
                              )}
                            </div>
                          )}
                          {simResult.recoveryCommand && (
                            <div style={{
                              background: 'rgba(241, 245, 249, 0.9)',
                              border: '1px solid rgba(99, 102, 241, 0.2)',
                              borderRadius: 6,
                              padding: '8px 12px',
                              fontFamily: 'var(--font-mono)',
                              fontSize: 12,
                              color: '#10b981',
                              wordBreak: 'break-all',
                            }}>
                              <span style={{ color: 'var(--text-muted)' }}>$ </span>
                              {simResult.recoveryCommand}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Recovery Actions */}
                      {simResult.recommendedActions && simResult.recommendedActions.length > 0 && (
                        <div style={{ margin: '16px 0' }}>
                          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>Recommended Recovery Actions</div>
                          {simResult.recommendedActions.map((action: string, i: number) => (
                            <div key={i} style={{
                              display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 12px',
                              background: i === 0 ? 'rgba(99,102,241,0.06)' : 'transparent',
                              borderRadius: 8, marginBottom: 4,
                              border: i === 0 ? '1px solid rgba(99,102,241,0.15)' : 'none',
                            }}>
                              <span style={{ color: i === 0 ? '#6366f1' : 'var(--text-tertiary)', flexShrink: 0 }}>{i === 0 ? '▶' : '○'}</span>
                              <span style={{ fontSize: 13, color: 'var(--text-primary)', fontFamily: action.includes('kubectl') ? 'monospace' : 'inherit', wordBreak: 'break-all' }}>{action}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {simResult.incidentId && (
                        <Link
                          to={`/incidents/${simResult.incidentId}`}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            color: 'var(--primary)',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            textDecoration: 'none',
                            marginTop: '0.25rem'
                          }}
                        >
                          View Full Report <ArrowRight size={14} />
                        </Link>
                      )}
                    </div>
                  );
                })()}
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
                      <div key={inc.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(255,255,255,0.45)', borderRadius: '8px', border: '1px solid var(--border)' }}>
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

          {/* Kubernetes Cluster Panel */}
          <div className="neon-card" style={{ marginTop: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: '#6366f1' }}>⎈</span> Kubernetes Cluster
                </h2>
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 600,
                    padding: '2px 10px',
                    borderRadius: '999px',
                    background: k8sPods.filter(p => p.status.toLowerCase() === 'running').length === k8sPods.length && k8sPods.length > 0 ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                    color: k8sPods.filter(p => p.status.toLowerCase() === 'running').length === k8sPods.length && k8sPods.length > 0 ? '#10b981' : '#ef4444',
                    border: `1px solid ${k8sPods.filter(p => p.status.toLowerCase() === 'running').length === k8sPods.length && k8sPods.length > 0 ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)'}`,
                  }}
                >
                  {k8sPods.filter(p => p.status.toLowerCase() === 'running').length}/{k8sPods.length} pods running
                </span>
              </div>

              <button
                onClick={() => fetchPodsData(true)}
                disabled={k8sRefreshing}
                className="btn-neon"
                title="Refresh pod statuses"
                style={{
                  padding: '0.35rem 0.85rem',
                  fontSize: '0.75rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  background: 'rgba(99, 102, 241, 0.1)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  color: '#818cf8',
                  cursor: k8sRefreshing ? 'not-allowed' : 'pointer',
                }}
              >
                <RefreshCw size={13} style={{ animation: k8sRefreshing ? 'spin 1s linear infinite' : 'none' }} />
                Refresh
              </button>
            </div>

            {k8sLoading ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1rem' }}>
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="skeleton-card" style={{ height: '110px' }}>
                    <div className="skeleton-line w-50" />
                    <div className="skeleton-line w-75" />
                  </div>
                ))}
              </div>
            ) : k8sPods.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '2rem', background: 'rgba(255,255,255,0.45)', borderRadius: '8px' }}>
                No Kubernetes pods found in cluster. Connect a cluster or select an active system.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1rem' }}>
                {k8sPods.map(pod => {
                  const meta = getPodStatusMeta(pod.status);
                  const isKilling = killingPod === pod.name;
                  const isRestarting = restartingPod === pod.name;

                  return (
                    <div
                      key={pod.name}
                      style={{
                        padding: '0.85rem 1rem',
                        background: 'rgba(255, 255, 255, 0.85)',
                        border: meta.dotClass === 'red' ? '1.5px solid rgba(239, 68, 68, 0.5)' : '1px solid rgba(148, 163, 184, 0.25)',
                        borderRadius: '10px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.6rem',
                        boxShadow: meta.dotClass === 'red' ? '0 2px 12px rgba(239, 68, 68, 0.15)' : '0 2px 8px rgba(0, 0, 0, 0.04)',
                        transition: 'all 0.25s ease',
                      }}
                    >
                      {/* Name + Status Dot + Badge */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0, flex: 1 }}>
                          <div className={`status-dot ${meta.dotClass}`} />
                          <span
                            title={pod.name}
                            style={{
                              fontFamily: 'var(--font-mono)',
                              fontWeight: 700,
                              fontSize: '0.82rem',
                              color: 'var(--text-primary)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              maxWidth: '160px',
                            }}
                          >
                            {pod.name}
                          </span>
                        </div>
                        <span
                          style={{
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            fontFamily: 'var(--font-mono)',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            color: meta.badgeColor,
                            background: meta.badgeBg,
                            border: `1px solid ${meta.badgeBorder}`,
                            textTransform: 'uppercase',
                            flexShrink: 0,
                          }}
                        >
                          {meta.label}
                        </span>
                      </div>

                      {/* Service & Restarts */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        <span>
                          Service: <strong style={{ color: 'var(--text-secondary)' }}>{pod.service}</strong>
                        </span>
                        <span>
                          Restarts: <strong style={{ color: pod.restarts > 0 ? '#f59e0b' : 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{pod.restarts}</strong>
                        </span>
                      </div>

                      {/* Action Buttons */}
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.1rem' }}>
                        <button
                          onClick={() => handleKillPod(pod.service, pod.name)}
                          disabled={isKilling || isRestarting}
                          title={`Kill pod ${pod.name}`}
                          style={{
                            padding: '3px 8px',
                            fontSize: '0.7rem',
                            fontWeight: 600,
                            borderRadius: '5px',
                            background: 'rgba(239, 68, 68, 0.12)',
                            border: '1px solid rgba(239, 68, 68, 0.4)',
                            color: '#ef4444',
                            cursor: isKilling || isRestarting ? 'not-allowed' : 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            transition: 'all 0.2s',
                          }}
                          onMouseEnter={e => {
                            if (!isKilling && !isRestarting) {
                              (e.currentTarget as HTMLElement).style.background = 'rgba(239, 68, 68, 0.25)';
                              (e.currentTarget as HTMLElement).style.borderColor = '#ef4444';
                            }
                          }}
                          onMouseLeave={e => {
                            (e.currentTarget as HTMLElement).style.background = 'rgba(239, 68, 68, 0.12)';
                            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(239, 68, 68, 0.4)';
                          }}
                        >
                          {isKilling ? (
                            <div className="spinner" style={{ width: '10px', height: '10px', borderColor: '#ef4444', borderTopColor: 'transparent' }} />
                          ) : null}
                          Kill Pod
                        </button>

                        <button
                          onClick={() => handleRestartPod(pod.service, pod.name)}
                          disabled={isKilling || isRestarting}
                          title={`Restart pod ${pod.name}`}
                          style={{
                            padding: '3px 8px',
                            fontSize: '0.7rem',
                            fontWeight: 600,
                            borderRadius: '5px',
                            background: 'rgba(99, 102, 241, 0.12)',
                            border: '1px solid rgba(99, 102, 241, 0.4)',
                            color: '#818cf8',
                            cursor: isKilling || isRestarting ? 'not-allowed' : 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            transition: 'all 0.2s',
                          }}
                          onMouseEnter={e => {
                            if (!isKilling && !isRestarting) {
                              (e.currentTarget as HTMLElement).style.background = 'rgba(99, 102, 241, 0.25)';
                              (e.currentTarget as HTMLElement).style.borderColor = '#6366f1';
                            }
                          }}
                          onMouseLeave={e => {
                            (e.currentTarget as HTMLElement).style.background = 'rgba(99, 102, 241, 0.12)';
                            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(99, 102, 241, 0.4)';
                          }}
                        >
                          {isRestarting ? (
                            <div className="spinner" style={{ width: '10px', height: '10px', borderColor: '#818cf8', borderTopColor: 'transparent' }} />
                          ) : (
                            <RotateCw size={10} />
                          )}
                          Restart
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
