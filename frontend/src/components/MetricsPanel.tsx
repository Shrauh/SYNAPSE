import { useEffect, useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { TrendingUp, Activity } from "lucide-react";

interface ServiceMetricPoint {
  time: string;
  latency: number;
  error_rate: number;
  cpu: number;
  memory: number;
}

interface ServiceMetrics {
  [service: string]: ServiceMetricPoint[];
}

const SERVICE_COLORS: Record<string, string> = {
  frontend:  "#06b6d4",
  checkout:  "#a78bfa",
  cart:      "#34d399",
  payment:   "#f59e0b",
  order:     "#f87171",
  catalog:   "#60a5fa",
  ad:        "#fb923c",
  redis:     "#4ade80",
  email:     "#e879f9",
  orderdb:   "#fbbf24",
};

const SERVICES = ["frontend", "checkout", "cart", "payment", "order", "catalog", "ad", "redis", "email", "orderdb"];

function generateMockPoint(service: string, t: number, hasAnomaly: boolean): ServiceMetricPoint {
  const base = {
    frontend:  { lat: 120, err: 0.02, cpu: 0.35, mem: 0.45 },
    checkout:  { lat: 95,  err: 0.01, cpu: 0.28, mem: 0.38 },
    cart:      { lat: 40,  err: 0.01, cpu: 0.20, mem: 0.30 },
    payment:   { lat: 200, err: 0.02, cpu: 0.40, mem: 0.50 },
    order:     { lat: 150, err: 0.02, cpu: 0.35, mem: 0.42 },
    catalog:   { lat: 30,  err: 0.005,cpu: 0.15, mem: 0.25 },
    ad:        { lat: 25,  err: 0.005,cpu: 0.12, mem: 0.20 },
    redis:     { lat: 2,   err: 0.001,cpu: 0.10, mem: 0.60 },
    email:     { lat: 80,  err: 0.01, cpu: 0.18, mem: 0.28 },
    orderdb:   { lat: 50,  err: 0.01, cpu: 0.30, mem: 0.55 },
  }[service] ?? { lat: 100, err: 0.02, cpu: 0.30, mem: 0.40 };

  const spike = hasAnomaly ? 1 + Math.sin(t * 0.5) * 3 : 1;
  const noise = () => 1 + (Math.random() - 0.5) * 0.1;

  return {
    time: new Date(Date.now() - (29 - t) * 5000).toLocaleTimeString(),
    latency: parseFloat((base.lat * spike * noise()).toFixed(1)),
    error_rate: parseFloat((Math.min(1, base.err * spike * noise())).toFixed(3)),
    cpu: parseFloat((Math.min(1, base.cpu * spike * noise())).toFixed(3)),
    memory: parseFloat((Math.min(1, base.mem * noise())).toFixed(3)),
  };
}

type MetricKey = "latency" | "error_rate" | "cpu" | "memory";

const METRIC_LABELS: Record<MetricKey, { label: string; unit: string; color: string }> = {
  latency:    { label: "Latency",    unit: "ms",   color: "#06b6d4" },
  error_rate: { label: "Error Rate", unit: "%",    color: "#f87171" },
  cpu:        { label: "CPU",        unit: "%",    color: "#a78bfa" },
  memory:     { label: "Memory",     unit: "%",    color: "#34d399" },
};

export default function MetricsPanel() {
  const [metric, setMetric] = useState<MetricKey>("latency");
  const [selectedServices, setSelectedServices] = useState(["frontend", "checkout", "payment", "orderdb"]);
  const [chartData, setChartData] = useState<Record<string, number | string>[]>([]);
  const [anomalousService, setAnomalousService] = useState<string>("");

  // Build multi-service time series
  useEffect(() => {
    const history: Record<string, ServiceMetricPoint[]> = {};
    SERVICES.forEach(svc => {
      history[svc] = Array.from({ length: 30 }, (_, i) =>
        generateMockPoint(svc, i, false)
      );
    });

    const updateChart = () => {
      const now: Record<string, number | string> = { time: new Date().toLocaleTimeString() };
      SERVICES.forEach(svc => {
        const hasAnomaly = svc === anomalousService;
        const pt = generateMockPoint(svc, Date.now() / 1000, hasAnomaly);
        history[svc].push(pt);
        if (history[svc].length > 30) history[svc].shift();
        now[svc] = pt[metric];
      });
      setChartData(prev => [...prev, now].slice(-30));
    };

    updateChart();
    const id = setInterval(updateChart, 3000);
    return () => clearInterval(id);
  }, [metric, anomalousService]);

  // Listen for anomaly events
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      const { type, data } = e.detail;
      if (type === "anomaly_update" && data?.critical_services?.length > 0) {
        setAnomalousService(data.critical_services[0]);
      }
    };
    window.addEventListener("synapse_ws_event" as any, handler);
    return () => window.removeEventListener("synapse_ws_event" as any, handler);
  }, []);

  const toggleService = (svc: string) => {
    setSelectedServices(prev =>
      prev.includes(svc) ? prev.filter(s => s !== svc) : [...prev, svc]
    );
  };

  const metricInfo = METRIC_LABELS[metric];

  return (
    <div className="synapse-card h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Live Metrics</h3>
        </div>
        <div className="flex gap-1">
          {(Object.keys(METRIC_LABELS) as MetricKey[]).map(m => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                metric === m
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {METRIC_LABELS[m].label}
            </button>
          ))}
        </div>
      </div>

      {/* Service toggles */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {SERVICES.map(svc => (
          <button
            key={svc}
            onClick={() => toggleService(svc)}
            className={`px-2 py-0.5 rounded text-[10px] font-medium border transition-all ${
              selectedServices.includes(svc)
                ? "border-transparent text-white"
                : "border-slate-700 text-slate-500 bg-transparent"
            } ${anomalousService === svc ? "ring-1 ring-rose-500" : ""}`}
            style={selectedServices.includes(svc) ? {
              background: SERVICE_COLORS[svc] + "30",
              borderColor: SERVICE_COLORS[svc] + "60",
              color: SERVICE_COLORS[svc],
            } : {}}
          >
            {svc}
          </button>
        ))}
      </div>

      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%" minHeight={160}>
          <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <defs>
              {selectedServices.map(svc => (
                <linearGradient key={svc} id={`grad-${svc}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={SERVICE_COLORS[svc]} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={SERVICE_COLORS[svc]} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" tick={{ fontSize: 9, fill: "#475569" }} tickLine={false} />
            <YAxis tick={{ fontSize: 9, fill: "#475569" }} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{
                background: "#0f172a",
                border: "1px solid #1e293b",
                borderRadius: 8,
                fontSize: 11,
              }}
              labelStyle={{ color: "#94a3b8" }}
              itemStyle={{ color: "#e2e8f0" }}
            />
            {selectedServices.map(svc => (
              <Area
                key={svc}
                type="monotone"
                dataKey={svc}
                name={svc}
                stroke={SERVICE_COLORS[svc]}
                strokeWidth={anomalousService === svc ? 2.5 : 1.5}
                fill={`url(#grad-${svc})`}
                dot={false}
                activeDot={{ r: 4 }}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-slate-600 mt-1 text-right">
        {metricInfo.label} · updates every 3s
      </p>
    </div>
  );
}
