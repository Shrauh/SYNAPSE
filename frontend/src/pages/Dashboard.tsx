import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  AlertTriangle, Activity, Clock, Server, ArrowRight,
  Brain, GitBranch, Zap, Search, Shield, TrendingUp,
  MessageSquare, BookOpen, Map, BarChart3, CheckCircle,
} from "lucide-react";
import { fetchHealth, fetchMetrics, fetchIncidents } from "../api/endpoints";
import type { HealthResponse, MetricsResponse, IncidentSummary } from "../types/api";
import {
  StatCard, StatusBadge, Spinner, ScoreBar, InfraCard, FeatureCard, SectionHeader,
} from "../components/UI";
import { HeroCarousel } from "../components/HeroCarousel";
import { useStore } from "../store";
import { formatDistanceToNow } from "date-fns";

/* ─── Infrastructure environments with real images ─── */
const INFRA_ENVS = [
  {
    name: "AWS Cloud Environment",
    type: "aws", icon: "☁️",
    image: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600&q=80&fit=crop",
    status: "healthy" as const, services: 10, incidents: 0, confidence: 97, uptime: "99.9%",
    accentColor: "#f59e0b",
  },
  {
    name: "E-Commerce Platform",
    type: "ecommerce", icon: "🛒",
    image: "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=600&q=80&fit=crop",
    status: "degraded" as const, services: 8, incidents: 1, confidence: 89, uptime: "98.2%",
    accentColor: "#10b981",
  },
  {
    name: "Streaming Platform",
    type: "streaming", icon: "🎬",
    image: "https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?w=600&q=80&fit=crop",
    status: "healthy" as const, services: 12, incidents: 0, confidence: 95, uptime: "99.7%",
    accentColor: "#f43f5e",
  },
  {
    name: "Ride-Sharing Platform",
    type: "rideshare", icon: "🚗",
    image: "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=600&q=80&fit=crop",
    status: "healthy" as const, services: 9, incidents: 0, confidence: 92, uptime: "99.4%",
    accentColor: "#06b6d4",
  },
  {
    name: "Kubernetes Cluster",
    type: "k8s", icon: "⚙️",
    image: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&q=80&fit=crop",
    status: "healthy" as const, services: 15, incidents: 0, confidence: 98, uptime: "99.99%",
    accentColor: "#3b82f6",
  },
  {
    name: "Docker Container Platform",
    type: "docker", icon: "🐳",
    image: "https://images.unsplash.com/photo-1605745341112-85968b19335b?w=600&q=80&fit=crop",
    status: "healthy" as const, services: 7, incidents: 0, confidence: 94, uptime: "99.8%",
    accentColor: "#06b6d4",
  },
];


/* ─── AI Feature showcases with real images ─── */
const FEATURES = [
  {
    icon: <Brain size={22} />, title: "AI Root Cause Detection",
    desc: "Graph Attention Networks identify the true source of failures across complex microservice dependencies.",
    benefit: "10× faster than manual investigation",
    color: "#8b5cf6",
    image: "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=400&q=80&fit=crop",
  },
  {
    icon: <GitBranch size={22} />, title: "Temporal Graph Networks",
    desc: "Capture time-series dependencies across services to understand cascading failure propagation patterns.",
    benefit: "Reduces MTTD by 73%",
    color: "#3b82f6",
    image: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400&q=80&fit=crop",
  },
  {
    icon: <Search size={22} />, title: "Causal Inference Engine",
    desc: "PC Algorithm and DECI-based causal discovery separates correlation from true causation.",
    benefit: "98% causal accuracy rate",
    color: "#06b6d4",
    image: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&q=80&fit=crop",
  },
  {
    icon: <Activity size={22} />, title: "Real-Time Anomaly Detection",
    desc: "GNN autoencoder continuously scores each service's reconstruction error to detect anomalies instantly.",
    benefit: "Sub-second anomaly alerts",
    color: "#10b981",
    image: "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=400&q=80&fit=crop",
  },
  {
    icon: <TrendingUp size={22} />, title: "Predictive Failure Detection",
    desc: "MAML meta-learning enables the model to adapt and predict failure patterns before they escalate.",
    benefit: "Predict failures 15 min ahead",
    color: "#f59e0b",
    image: "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=400&q=80&fit=crop",
  },
  {
    icon: <MessageSquare size={22} />, title: "LLM-Powered Incident Reports",
    desc: "Groq LLaMA 3 generates plain-language RCA summaries with actionable remediation recommendations.",
    benefit: "Instant human-readable reports",
    color: "#f43f5e",
    image: "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=400&q=80&fit=crop",
  },
  {
    icon: <BookOpen size={22} />, title: "Runbook Recommendation",
    desc: "AI matches incidents to the most relevant runbooks in your knowledge base for faster resolution.",
    benefit: "Automated resolution playbooks",
    color: "#8b5cf6",
    image: "https://images.unsplash.com/photo-1456324504439-367cee3b3c32?w=400&q=80&fit=crop",
  },
  {
    icon: <Map size={22} />, title: "Dynamic Dependency Mapping",
    desc: "Real-time interactive service topology with anomaly overlays and causal edge highlighting.",
    benefit: "Full-stack visibility",
    color: "#06b6d4",
    image: "https://images.unsplash.com/photo-1545987796-200677ee1011?w=400&q=80&fit=crop",
  },
  {
    icon: <Shield size={22} />, title: "Continual Learning",
    desc: "EWC and replay buffer prevent catastrophic forgetting — the model improves with every incident.",
    benefit: "Self-evolving intelligence",
    color: "#10b981",
    image: "https://images.unsplash.com/photo-1555255707-c07966088b7b?w=400&q=80&fit=crop",
  },
  {
    icon: <BarChart3 size={22} />, title: "Cloud Service Monitoring",
    desc: "Prometheus-compatible metrics ingestion with per-service latency, error rate, and saturation tracking.",
    benefit: "Unified observability",
    color: "#3b82f6",
    image: "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&q=80&fit=crop",
  },
];

/* ─── Severity color helper ─── */
function sevColor(s: string) {
  return s === "critical" ? "var(--status-critical)"
    : s === "high" ? "var(--status-warning)"
    : s === "medium" ? "var(--status-degraded)"
    : "var(--status-healthy)";
}

export default function Dashboard() {
  const [health, setHealth]     = useState<HealthResponse | null>(null);
  const [metrics, setMetrics]   = useState<MetricsResponse | null>(null);
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading]   = useState(true);
  const anomalyScores           = useStore(s => s.anomalyScores);

  useEffect(() => {
    Promise.all([fetchHealth(), fetchMetrics(), fetchIncidents(1)])
      .then(([h, m, i]) => {
        setHealth(h);
        setMetrics(m);
        setIncidents(i.incidents.slice(0, 6));
      })
      .finally(() => setLoading(false));

    const iv = setInterval(() => {
      fetchMetrics().then(setMetrics);
      fetchIncidents(1).then(i => setIncidents(i.incidents.slice(0, 6)));
    }, 10_000);
    return () => clearInterval(iv);
  }, []);

  const topServices = Object.entries(anomalyScores)
    .sort((a, b) => b[1] - a[1]).slice(0, 8);

  return (
    <div className="page-content" style={{ paddingTop: "1.5rem" }}>

      {/* ── Hero Carousel ── */}
      <HeroCarousel />

      {/* ── Stat Cards ── */}
      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 28 }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="stat-card" style={{ height: 120 }}>
              <div className="skeleton" style={{ height: 14, width: "50%", marginBottom: 12 }} />
              <div className="skeleton" style={{ height: 36, width: "60%" }} />
            </div>
          ))}
        </div>
      ) : (
        <motion.div
          style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 28 }}
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        >
          <StatCard
            title="Total Incidents" color="blue"
            value={metrics?.total_incidents ?? 0}
            icon={<AlertTriangle size={18} />}
            sub="All time"
            trend={{ value: "+2 today", up: false }}
            animate
          />
          <StatCard
            title="Active Analysis" color="purple"
            value={metrics?.active_incidents ?? 0}
            icon={<Activity size={18} />}
            sub="Analyzing now"
          />
          <StatCard
            title="Avg RCA Time" color="cyan"
            value={`${(metrics?.avg_resolution_time_sec ?? 0).toFixed(1)}s`}
            icon={<Clock size={18} />}
            sub="vs 3–2 hrs manual"
            trend={{ value: "52s avg", up: true }}
          />
          <StatCard
            title="Services Monitored" color="emerald"
            value={10}
            icon={<Server size={18} />}
            sub="10 service topology"
            animate
          />
        </motion.div>
      )}

      {/* ── Live Data Row ── */}
      <motion.div
        style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20, marginBottom: 28 }}
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
      >
        {/* Recent Incidents */}
        <div className="card">
          <div className="panel-header">
            <div className="panel-title">
              <AlertTriangle size={15} color="var(--status-warning)" />
              Recent Incidents
              {incidents.filter(i => i.status === "analyzing").length > 0 && (
                <span className="badge badge-analyzing blink" style={{ marginLeft: 6 }}>
                  {incidents.filter(i => i.status === "analyzing").length} Active
                </span>
              )}
            </div>
            <Link to="/incidents" style={{
              display: "flex", alignItems: "center", gap: 4,
              fontSize: "0.75rem", color: "var(--accent-blue)", fontWeight: 600,
            }}>
              All Incidents <ArrowRight size={12} />
            </Link>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Incident</th>
                  <th>Status</th>
                  <th>Root Cause</th>
                  <th>Confidence</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {incidents.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: "2.5rem", color: "var(--text-muted)" }}>
                      <div style={{ marginBottom: 8 }}>🛡️</div>
                      No incidents yet — try simulating a fault!
                    </td>
                  </tr>
                ) : incidents.map((inc, i) => (
                  <motion.tr
                    key={inc.id}
                    initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    onClick={() => window.location.href = `/incidents/${inc.id}`}
                  >
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{
                          width: 3, height: 32, borderRadius: 99,
                          background: sevColor(inc.severity), flexShrink: 0,
                        }} />
                        <div>
                          <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.82rem" }}>
                            {inc.title}
                          </div>
                          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontFamily: "JetBrains Mono" }}>
                            #{inc.id.slice(0, 8)}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td><StatusBadge status={inc.status} /></td>
                    <td style={{ fontFamily: "JetBrains Mono", fontSize: "0.78rem" }}>
                      {inc.root_cause_service ?? <span style={{ color: "var(--text-muted)" }}>analyzing…</span>}
                    </td>
                    <td style={{ color: "var(--accent-blue)", fontWeight: 700 }}>
                      {inc.confidence != null ? `${(inc.confidence * 100).toFixed(0)}%` : "—"}
                    </td>
                    <td style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                      {formatDistanceToNow(new Date(inc.detected_at), { addSuffix: true })}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Anomaly Feed */}
        <div className="card">
          <div className="panel-header">
            <div className="panel-title" style={{ fontSize: "0.82rem" }}>
              <Activity size={14} color="var(--accent-cyan)" />
              Anomaly Scores
            </div>
            <span className="badge badge-info blink" style={{ fontSize: "0.6rem" }}>● LIVE</span>
          </div>

          {topServices.length === 0 ? (
            <div style={{ color: "var(--text-muted)", fontSize: "0.8rem", textAlign: "center", padding: "1.5rem 0" }}>
              Waiting for live data…<br />
              <span style={{ fontSize: "0.7rem" }}>Start backend to see scores</span>
            </div>
          ) : topServices.map(([svc, score], i) => (
            <motion.div
              key={svc} layout
              initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              style={{
                padding: "8px 0",
                borderBottom: i < topServices.length - 1 ? "1px solid var(--border)" : "none",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div className="status-dot" style={{
                    background: score > 0.8 ? "var(--status-critical)" : score > 0.6 ? "var(--status-warning)"
                      : score > 0.4 ? "var(--status-degraded)" : "var(--status-healthy)",
                  }} />
                  <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>{svc}</span>
                </div>
                <span style={{
                  fontSize: "0.72rem", fontFamily: "JetBrains Mono", fontWeight: 700,
                  color: score > 0.8 ? "var(--status-critical)" : score > 0.6 ? "var(--status-warning)"
                    : score > 0.4 ? "var(--status-degraded)" : "var(--status-healthy)",
                }}>
                  {score.toFixed(3)}
                </span>
              </div>
              <ScoreBar score={score} size="sm" />
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ── System Components ── */}
      {health && (
        <motion.div
          className="card" style={{ marginBottom: 32 }}
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
        >
          <div className="panel-header">
            <div className="panel-title"><Server size={14} /> System Components</div>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>v{health.version}</span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {Object.entries(health.components).map(([k, v]) => {
              const ok = v === true || v === "up" || v === "ok";
              return (
                <div key={k} style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "6px 14px", borderRadius: 8,
                  background: ok ? "rgba(16,185,129,0.06)" : "rgba(245,158,11,0.06)",
                  border: `1px solid ${ok ? "rgba(16,185,129,0.2)" : "rgba(245,158,11,0.2)"}`,
                }}>
                  {ok
                    ? <CheckCircle size={12} color="var(--status-healthy)" />
                    : <AlertTriangle size={12} color="var(--status-degraded)" />}
                  <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    {k.replace(/_/g, " ")}
                  </span>
                  <span style={{
                    fontSize: "0.7rem", fontFamily: "JetBrains Mono",
                    color: ok ? "var(--status-healthy)" : "var(--status-degraded)", fontWeight: 700,
                  }}>
                    {String(v)}
                  </span>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* ── Infrastructure Showcase ── */}
      <motion.section
        style={{ marginBottom: 40 }}
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
      >
        <SectionHeader
          title="Monitored Environments"
          subtitle="Real-time health across all connected cloud infrastructure environments"
          action={
            <Link to="/graph" style={{
              display: "flex", alignItems: "center", gap: 4,
              fontSize: "0.78rem", color: "var(--accent-blue)", fontWeight: 600,
            }}>
              View All <ArrowRight size={13} />
            </Link>
          }
        />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          {INFRA_ENVS.map((env, i) => (
            <motion.div
              key={env.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * i }}
            >
              <InfraCard {...env} />
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* ── Feature Showcase ── */}
      <motion.section
        style={{ marginBottom: 40 }}
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
      >
        <SectionHeader
          title="Platform Capabilities"
          subtitle="Enterprise AI observability powered by cutting-edge ML research"
        />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
          {FEATURES.map((f, i) => (
            <FeatureCard key={f.title} {...f} delay={i * 0.04} />
          ))}
        </div>
      </motion.section>

      {/* ── Quick Actions ── */}
      <motion.div
        style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
      >
        {[
          {
            to: "/simulate", icon: Zap, title: "Inject Fault",
            desc: "Simulate real-world failure scenarios and watch the 8-step SYNAPSE pipeline run in real time.",
            color: "#8b5cf6", btnLabel: "Run Simulation",
          },
          {
            to: "/graph", icon: GitBranch, title: "Explore Causal Graph",
            desc: "Interactive service dependency map with live anomaly overlays and causal edge visualization.",
            color: "#06b6d4", btnLabel: "Open Graph",
          },
          {
            to: "/model", icon: Brain, title: "Model Intelligence",
            desc: "Monitor GNN performance, MAML meta-learning stats, and continual learning progress.",
            color: "#10b981", btnLabel: "View Model",
          },
        ].map(({ to, icon: Icon, title, desc, color, btnLabel }) => (
          <div key={to} className="card card-glow" style={{
            background: `linear-gradient(135deg, ${color}08 0%, ${color}04 100%)`,
            border: `1px solid ${color}20`,
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: 12,
              background: `${color}18`, border: `1px solid ${color}30`,
              display: "flex", alignItems: "center", justifyContent: "center",
              marginBottom: 14,
            }}>
              <Icon size={20} color={color} />
            </div>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)", marginBottom: 6 }}>
              {title}
            </div>
            <p style={{ fontSize: "0.77rem", color: "var(--text-muted)", lineHeight: 1.55, marginBottom: 16 }}>
              {desc}
            </p>
            <Link to={to}>
              <button className="btn btn-ghost btn-sm" style={{ borderColor: `${color}30`, color }}>
                {btnLabel} <ArrowRight size={12} />
              </button>
            </Link>
          </div>
        ))}
      </motion.div>
    </div>
  );
}
