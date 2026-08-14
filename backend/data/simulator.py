"""
SYNAPSE Data Simulator — Synthetic Microservice Metrics Generator.

Generates realistic time-series metrics (latency, error_rate, cpu, memory,
request_rate) for a 10-service microservice topology. Supports fault injection
with cascading failure propagation to simulate real incidents.

Usage:
    from data.simulator import MicroserviceSimulator
    sim = MicroserviceSimulator()
    data = sim.simulate_incident(root_cause="database", fault_type="latency_spike")
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ──────────────────────────────────────────────
# Topology Definition
# ──────────────────────────────────────────────

SERVICE_NAMES = [
    "frontend",
    "checkout",
    "cart",
    "payment",
    "order",
    "catalog",
    "ad",
    "redis",
    "email",
    "orderdb",
]

# Directed edges: caller → callee (Google Online Boutique topology)
DEPENDENCY_EDGES: List[Tuple[str, str]] = [
    ("frontend",  "checkout"),
    ("frontend",  "cart"),
    ("frontend",  "catalog"),
    ("frontend",  "ad"),
    ("checkout",  "payment"),
    ("checkout",  "order"),
    ("checkout",  "cart"),
    ("cart",      "redis"),
    ("payment",   "orderdb"),
    ("order",     "orderdb"),
    ("order",     "email"),
]

# Normal-state baselines per service (latency_ms, error_rate%, cpu%, mem%, req/s)
BASELINES: Dict[str, Dict[str, float]] = {
    "frontend":  {"latency": 120.0, "error_rate": 0.5, "cpu": 35.0, "memory": 45.0, "request_rate": 500.0},
    "checkout":  {"latency":  95.0, "error_rate": 0.4, "cpu": 28.0, "memory": 38.0, "request_rate": 300.0},
    "cart":      {"latency":  40.0, "error_rate": 0.3, "cpu": 20.0, "memory": 30.0, "request_rate": 250.0},
    "payment":   {"latency": 200.0, "error_rate": 0.8, "cpu": 40.0, "memory": 50.0, "request_rate": 200.0},
    "order":     {"latency": 150.0, "error_rate": 0.6, "cpu": 35.0, "memory": 42.0, "request_rate": 180.0},
    "catalog":   {"latency":  30.0, "error_rate": 0.2, "cpu": 15.0, "memory": 25.0, "request_rate": 400.0},
    "ad":        {"latency":  25.0, "error_rate": 0.3, "cpu": 12.0, "memory": 20.0, "request_rate": 350.0},
    "redis":     {"latency":   2.0, "error_rate": 0.1, "cpu": 10.0, "memory": 60.0, "request_rate": 800.0},
    "email":     {"latency":  80.0, "error_rate": 0.4, "cpu": 18.0, "memory": 28.0, "request_rate": 120.0},
    "orderdb":   {"latency":  50.0, "error_rate": 0.2, "cpu": 30.0, "memory": 55.0, "request_rate": 600.0},
}

# ── Fault type → metric impact configuration ──────────────────────────────
# Each fault type maps to multipliers applied to the root cause service.
FAULT_IMPACT: Dict[str, Dict[str, float]] = {
    "cpu_stress":       {"cpu": 9.0, "latency": 5.0, "error_rate": 2.0, "memory": 1.1},
    "db_exhaustion":    {"error_rate": 50.0, "latency": 25.0, "cpu": 3.0, "memory": 2.0},
    "dns_failure":      {"error_rate": 100.0, "latency": 0.1, "cpu": 1.0, "memory": 1.0},
    "oom_kill":         {"memory": 12.0, "cpu": 4.0, "error_rate": 10.0, "latency": 6.0},
    "network_latency":  {"latency": 20.0, "error_rate": 3.0, "cpu": 1.5, "memory": 1.0},
    "pod_crash":        {"error_rate": 100.0, "latency": 0.0, "cpu": 0.0, "memory": 0.0},
    "cascade_failure":  {"error_rate": 15.0, "latency": 8.0, "cpu": 3.0, "memory": 2.0},
    "retry_storm":      {"request_rate": 10.0, "cpu": 9.5, "latency": 4.0, "error_rate": 5.0},
    "memory_leak":      {"memory": 8.0, "latency": 3.0, "cpu": 2.0, "error_rate": 2.0},
    "config_error":     {"error_rate": 100.0, "latency": 2.0, "cpu": 1.2, "memory": 1.0},
    # legacy aliases
    "latency_spike":    {"latency": 8.0, "error_rate": 2.5, "cpu": 2.0, "memory": 1.2},
    "error_burst":      {"error_rate": 20.0, "latency": 3.0, "cpu": 2.5, "memory": 1.3},
    "resource_exhaustion": {"cpu": 7.0, "memory": 6.0, "latency": 5.0, "error_rate": 4.0},
}

# Noise standard deviation as fraction of baseline
NOISE_FRACTION = 0.08


@dataclass
class FaultConfig:
    """Configuration for a fault injection scenario."""
    root_cause_service: str
    fault_type: str = "latency_spike"           # latency_spike | error_burst | resource_exhaustion
    severity_multiplier: float = 5.0            # how much the root cause metric spikes
    cascade_attenuation: float = 0.55           # signal loss per hop in the dependency chain
    cascade_delay_steps: int = 2                # time steps before downstream sees impact
    fault_start_fraction: float = 0.3           # fraction through the window when fault begins
    fault_duration_fraction: float = 0.5        # fraction of window the fault lasts


@dataclass
class SimulationResult:
    """Container for simulation output."""
    metrics_df: pd.DataFrame                    # time-series metrics for all services
    adjacency: List[Tuple[str, str]]            # dependency edges
    fault_config: FaultConfig
    ground_truth_root: str                      # which service was the actual root cause
    affected_services: List[str]                 # services that were impacted downstream
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    window_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "ground_truth_root": self.ground_truth_root,
            "affected_services": self.affected_services,
            "fault_type": self.fault_config.fault_type,
            "num_timesteps": len(self.metrics_df["timestamp"].unique()),
            "num_services": len(SERVICE_NAMES),
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
        }


class MicroserviceSimulator:
    """Generates synthetic microservice metrics with injectable faults."""

    def __init__(self, seed: Optional[int] = None):
        self.services = SERVICE_NAMES.copy()
        self.edges = DEPENDENCY_EDGES.copy()
        self.baselines = {k: dict(v) for k, v in BASELINES.items()}
        self.rng = np.random.default_rng(seed)

        # Build reverse adjacency (who depends on me = my upstream callers)
        # If A→B (A calls B), then B failing affects A (upstream propagation)
        self._upstream: Dict[str, List[str]] = {s: [] for s in self.services}
        for src, tgt in self.edges:
            self._upstream[tgt].append(src)

    def _get_downstream(self, service: str) -> List[str]:
        """Get services that this service calls (direct dependents)."""
        return [tgt for src, tgt in self.edges if src == service]

    def _compute_cascade_order(self, root: str) -> List[Tuple[str, int]]:
        """BFS from root through REVERSE edges (upstream propagation).

        When a downstream service (e.g. database) fails, its callers
        (auth-service, user-service, etc.) are affected, and their
        callers (api-gateway) are affected next.

        Returns list of (service, hop_distance) sorted by distance.
        """
        visited = {root: 0}
        queue = [root]
        result = []

        while queue:
            current = queue.pop(0)
            hop = visited[current]
            if current != root:
                result.append((current, hop))

            # Propagate to upstream callers
            for upstream_svc in self._upstream.get(current, []):
                if upstream_svc not in visited:
                    visited[upstream_svc] = hop + 1
                    queue.append(upstream_svc)

        return sorted(result, key=lambda x: x[1])

    def _generate_normal_metrics(
        self, num_steps: int, interval_sec: int = 30
    ) -> pd.DataFrame:
        """Generate normal-behavior time-series for all services."""
        now = datetime.now(timezone.utc)
        timestamps = [now + timedelta(seconds=i * interval_sec) for i in range(num_steps)]

        rows = []
        for ts in timestamps:
            for svc in self.services:
                base = self.baselines[svc]
                row = {
                    "service": svc,
                    "timestamp": ts,
                    "latency": max(0.1, base["latency"] * (1 + self.rng.normal(0, NOISE_FRACTION))),
                    "error_rate": max(0.0, base["error_rate"] * (1 + self.rng.normal(0, NOISE_FRACTION))),
                    "cpu": np.clip(base["cpu"] * (1 + self.rng.normal(0, NOISE_FRACTION)), 0, 100),
                    "memory": np.clip(base["memory"] * (1 + self.rng.normal(0, NOISE_FRACTION)), 0, 100),
                    "request_rate": max(1.0, base["request_rate"] * (1 + self.rng.normal(0, NOISE_FRACTION))),
                }
                rows.append(row)

        return pd.DataFrame(rows)

    def _inject_fault(
        self, df: pd.DataFrame, config: FaultConfig
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Inject a fault into the time-series and propagate to upstream callers."""
        df = df.copy()
        timestamps = sorted(df["timestamp"].unique())
        num_steps = len(timestamps)

        fault_start = int(num_steps * config.fault_start_fraction)
        fault_end = min(num_steps, fault_start + int(num_steps * config.fault_duration_fraction))

        root = config.root_cause_service
        affected = []

        # Get impact multipliers for this fault type
        impact = FAULT_IMPACT.get(
            config.fault_type,
            FAULT_IMPACT["latency_spike"]  # default
        )

        # --- Fault the root cause service ---
        root_mask = df["service"] == root
        for i in range(fault_start, fault_end):
            ts_mask = df["timestamp"] == timestamps[i]
            mask = root_mask & ts_mask

            for metric, mult in impact.items():
                if metric in df.columns:
                    if metric == "cpu":
                        df.loc[mask, metric] = np.clip(
                            df.loc[mask, metric] * mult, 0, 100
                        )
                    elif metric == "memory":
                        df.loc[mask, metric] = np.clip(
                            df.loc[mask, metric] * mult, 0, 100
                        )
                    elif metric == "error_rate":
                        df.loc[mask, metric] = np.clip(
                            df.loc[mask, metric] * mult, 0, 100
                        )
                    else:
                        df.loc[mask, metric] *= max(0, mult)

        # Apply noise scaling for severity
        severity_scale = config.severity_multiplier / 5.0  # normalize to 1.0 at severity=5

        # --- Cascade to upstream callers ---
        cascade_order = self._compute_cascade_order(root)
        for svc, hop in cascade_order:
            affected.append(svc)
            attenuation = (config.cascade_attenuation ** hop) * severity_scale
            delay = config.cascade_delay_steps * hop

            svc_mask = df["service"] == svc
            cascade_start = min(fault_start + delay, num_steps - 1)

            for i in range(cascade_start, fault_end):
                ts_mask = df["timestamp"] == timestamps[i]
                mask = svc_mask & ts_mask

                # Attenuated impact on latency and error_rate
                df.loc[mask, "latency"] *= (1 + (impact.get("latency", 1.0) - 1) * attenuation)
                df.loc[mask, "error_rate"] = np.clip(
                    df.loc[mask, "error_rate"] * (1 + (impact.get("error_rate", 1.0) - 1) * attenuation),
                    0, 100
                )
                df.loc[mask, "cpu"] = np.clip(
                    df.loc[mask, "cpu"] * (1 + 0.3 * attenuation), 0, 100
                )

        return df, affected

    def simulate_normal(
        self, num_steps: int = 60, interval_sec: int = 30
    ) -> SimulationResult:
        """Generate normal (no-fault) metrics window."""
        df = self._generate_normal_metrics(num_steps, interval_sec)
        timestamps = sorted(df["timestamp"].unique())

        return SimulationResult(
            metrics_df=df,
            adjacency=self.edges,
            fault_config=FaultConfig(root_cause_service="none", fault_type="none"),
            ground_truth_root="none",
            affected_services=[],
            window_start=timestamps[0],
            window_end=timestamps[-1],
        )

    def simulate_incident(
        self,
        root_cause: str = "database",
        fault_type: str = "latency_spike",
        severity: float = 5.0,
        num_steps: int = 60,
        interval_sec: int = 30,
        seed: Optional[int] = None,
    ) -> SimulationResult:
        """Generate a fault-injected incident scenario.

        Args:
            root_cause: Service to inject the fault into.
            fault_type: One of 'latency_spike', 'error_burst', 'resource_exhaustion'.
            severity: Multiplier for the fault magnitude (1.0 = no change, 5.0 = 5x).
            num_steps: Number of time steps to generate.
            interval_sec: Seconds between each time step.
            seed: Optional RNG seed for reproducibility.

        Returns:
            SimulationResult with metrics, topology, and ground truth.
        """
        if seed is not None:
            self.rng = np.random.default_rng(seed)

        if root_cause not in self.services:
            raise ValueError(f"Unknown service: {root_cause}. Must be one of {self.services}")

        config = FaultConfig(
            root_cause_service=root_cause,
            fault_type=fault_type,
            severity_multiplier=severity,
        )

        df = self._generate_normal_metrics(num_steps, interval_sec)
        df, affected = self._inject_fault(df, config)
        timestamps = sorted(df["timestamp"].unique())

        return SimulationResult(
            metrics_df=df,
            adjacency=self.edges,
            fault_config=config,
            ground_truth_root=root_cause,
            affected_services=affected,
            window_start=timestamps[0],
            window_end=timestamps[-1],
        )

    def generate_training_set(
        self,
        num_normal: int = 20,
        num_faults: int = 30,
        num_steps: int = 60,
    ) -> List[SimulationResult]:
        """Generate a mixed training set of normal + fault scenarios."""
        results = []

        for _ in range(num_normal):
            results.append(self.simulate_normal(num_steps=num_steps))

        # All 10 fault types from project spec
        fault_types = list(FAULT_IMPACT.keys())[:10]
        faultable_services = list(self.services)

        for i in range(num_faults):
            root = faultable_services[i % len(faultable_services)]
            ft = fault_types[i % len(fault_types)]
            severity = self.rng.uniform(3.0, 8.0)
            results.append(
                self.simulate_incident(
                    root_cause=root,
                    fault_type=ft,
                    severity=severity,
                    num_steps=num_steps,
                )
            )

        return results


# ──────────────────────────────────────────────
# Convenience functions
# ──────────────────────────────────────────────

def quick_simulate(
    root_cause: str = "orderdb",
    fault_type: str = "db_exhaustion",
    severity: float = 5.0,
    seed: int = 42,
) -> SimulationResult:
    """One-liner to generate a simulation result for testing."""
    sim = MicroserviceSimulator(seed=seed)
    return sim.simulate_incident(
        root_cause=root_cause,
        fault_type=fault_type,
        severity=severity,
        seed=seed,
    )
