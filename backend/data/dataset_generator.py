"""
SYNAPSE Dataset Generator — 500+ Labeled Incident Dataset.

Generates a comprehensive labeled dataset for:
  - Offline evaluation of the full RCA pipeline
  - Training the CQL agent on historical incidents
  - Benchmarking AC@1 and AC@3 accuracy targets

Dataset covers:
  - All 10 Google Online Boutique services
  - All 10 fault types from the project spec
  - 3 severity levels (low, medium, high)
  - Both simple (1 service) and cascade (multi-service) failures

Output: data/labeled_incidents.json with ground-truth root causes

Usage:
    python -m data.dataset_generator
    # → writes backend/data/labeled_incidents.json
"""

from __future__ import annotations

import json
import logging
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Services from Google Online Boutique ────────────────────────────────
ALL_SERVICES = [
    "frontend", "checkout", "cart", "payment",
    "order", "catalog", "ad", "redis", "email", "orderdb",
]

# ── Fault types from project spec ────────────────────────────────────────
ALL_FAULT_TYPES = [
    "cpu_stress", "db_exhaustion", "dns_failure", "oom_kill",
    "network_latency", "pod_crash", "cascade_failure", "retry_storm",
    "memory_leak", "config_error",
]

SEVERITIES = ["low", "medium", "high"]
SEVERITY_NUMS = {"low": 3.0, "medium": 5.5, "high": 8.0}


class DatasetGenerator:
    """Generates labeled incident datasets for SYNAPSE evaluation."""

    def __init__(self, seed: int = 42) -> None:
        random.seed(seed)
        self._incidents: List[Dict[str, Any]] = []

    def generate(self, n_incidents: int = 500) -> List[Dict[str, Any]]:
        """Generate n labeled incidents.

        Distribution:
          - Each service appears as root cause ~equally
          - Each fault type appears ~equally
          - 80% simple (1 service), 20% cascade (2-3 services)

        Args:
            n_incidents: Total incidents to generate.

        Returns:
            List of labeled incident dicts.
        """
        print(f"[DatasetGen] Generating {n_incidents} labeled incidents...")

        try:
            from data.simulator import MicroserviceSimulator
        except ImportError as e:
            print(f"[DatasetGen] Error importing simulator: {e}")
            return self._generate_mock_dataset(n_incidents)

        sim = MicroserviceSimulator(seed=42)
        incidents = []
        success = 0
        failed = 0

        for i in range(n_incidents):
            # Sample parameters
            service = random.choice(ALL_SERVICES)
            fault = random.choice(ALL_FAULT_TYPES)
            severity = random.choice(SEVERITIES)
            severity_num = SEVERITY_NUMS[severity]
            is_cascade = random.random() < 0.2

            try:
                # Generate simulated incident
                result = sim.simulate_incident(
                    root_cause=service,
                    fault_type=fault,
                    severity=severity_num,
                    num_steps=40,
                )

                # Extract features for evaluation
                metrics_df = result.metrics_df
                anomaly_scores = {}
                if not metrics_df.empty:
                    for svc in ALL_SERVICES:
                        svc_data = metrics_df[metrics_df["service"] == svc]
                        if not svc_data.empty:
                            # Simple anomaly score from error_rate + latency deviation
                            err = svc_data["error_rate"].mean()
                            lat = svc_data["latency"].mean()
                            base_lat = 0.1  # 100ms baseline
                            lat_score = min(1.0, (lat - base_lat) / (base_lat * 10))
                            anomaly_scores[svc] = min(1.0, err * 0.7 + max(0, lat_score) * 0.3)

                # Compute ground truth: service with highest anomaly + is root
                affected = [s for s, sc in anomaly_scores.items() if sc > 0.3]

                incident = {
                    "id": f"inc_{i:05d}",
                    "fault_type": fault,
                    "root_cause_service": service,  # Ground truth
                    "severity": severity,
                    "is_cascade": is_cascade,
                    "affected_services": affected,
                    "anomaly_scores": {k: round(v, 4) for k, v in anomaly_scores.items()},
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "label_confidence": 1.0,  # Synthetic = perfect label
                }
                incidents.append(incident)
                success += 1

                if (i + 1) % 50 == 0:
                    print(f"  [{i+1}/{n_incidents}] {success} success, {failed} failed")

            except Exception as e:
                logger.warning(f"[DatasetGen] Incident {i} failed: {e}")
                failed += 1
                # Add mock entry to maintain count
                incidents.append(self._mock_incident(i, service, fault, severity))

        self._incidents = incidents
        print(f"[DatasetGen] Done: {success} real + {failed} mock = {len(incidents)} total")
        return incidents

    def _mock_incident(
        self, idx: int, service: str, fault: str, severity: str
    ) -> Dict[str, Any]:
        """Generate a mock incident when simulation fails."""
        # Heuristic anomaly scores: root service gets high score
        scores = {}
        for svc in ALL_SERVICES:
            if svc == service:
                scores[svc] = 0.85 + random.uniform(0, 0.14)
            elif svc in self._get_downstream(service):
                scores[svc] = 0.4 + random.uniform(0, 0.3)
            else:
                scores[svc] = random.uniform(0, 0.15)

        return {
            "id": f"inc_{idx:05d}_mock",
            "fault_type": fault,
            "root_cause_service": service,
            "severity": severity,
            "is_cascade": False,
            "affected_services": [k for k, v in scores.items() if v > 0.3],
            "anomaly_scores": {k: round(v, 4) for k, v in scores.items()},
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "label_confidence": 0.9,
        }

    def _generate_mock_dataset(self, n: int) -> List[Dict[str, Any]]:
        """Generate fully synthetic dataset when simulator not available."""
        incidents = []
        for i in range(n):
            service = random.choice(ALL_SERVICES)
            fault = random.choice(ALL_FAULT_TYPES)
            severity = random.choice(SEVERITIES)
            incidents.append(self._mock_incident(i, service, fault, severity))
        return incidents

    def _get_downstream(self, service: str) -> List[str]:
        """Get services that depend on the given service (downstream)."""
        topology = {
            "frontend": [], "checkout": ["frontend"], "cart": ["frontend", "checkout"],
            "payment": ["checkout"], "order": ["checkout"], "catalog": ["frontend"],
            "ad": ["frontend"], "redis": ["cart"], "email": ["order"],
            "orderdb": ["payment", "order"],
        }
        downstream = []
        for svc, deps in topology.items():
            if service in deps:
                downstream.append(svc)
        return downstream

    def save(self, path: Optional[str] = None) -> str:
        """Save generated dataset to JSON file.

        Args:
            path: Output path (default: data/labeled_incidents.json).

        Returns:
            Path of saved file.
        """
        output_path = Path(path or __file__).parent / "labeled_incidents.json"
        with open(output_path, "w") as f:
            json.dump(
                {
                    "metadata": {
                        "total": len(self._incidents),
                        "services": ALL_SERVICES,
                        "fault_types": ALL_FAULT_TYPES,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "version": "1.0",
                    },
                    "incidents": self._incidents,
                },
                f,
                indent=2,
            )
        print(f"[DatasetGen] Saved {len(self._incidents)} incidents to {output_path}")
        return str(output_path)

    def compute_baseline_accuracy(self) -> Dict[str, float]:
        """Compute AC@1, AC@3 for a naive highest-anomaly-score baseline.

        This measures what accuracy a trivial baseline achieves,
        providing a lower bound for the full SYNAPSE pipeline.
        """
        if not self._incidents:
            return {}

        ac1 = 0
        ac3 = 0

        for inc in self._incidents:
            scores = inc["anomaly_scores"]
            true_root = inc["root_cause_service"]

            if not scores:
                continue

            # Sort by anomaly score
            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top1 = ranked[0][0] if ranked else None
            top3 = [s for s, _ in ranked[:3]]

            if top1 == true_root:
                ac1 += 1
            if true_root in top3:
                ac3 += 1

        n = len(self._incidents)
        return {
            "ac_at_1": round(ac1 / n, 4),
            "ac_at_3": round(ac3 / n, 4),
            "n_incidents": n,
        }


# Module-level singleton
dataset_generator = DatasetGenerator()


if __name__ == "__main__":
    """CLI entry point: python -m data.dataset_generator"""
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500

    gen = DatasetGenerator(seed=42)
    incidents = gen.generate(n_incidents=n)
    gen.save()

    baseline = gen.compute_baseline_accuracy()
    print(f"\nBaseline accuracy (naive highest-score):")
    print(f"  AC@1 = {baseline.get('ac_at_1', 0):.3f} (target > 0.80)")
    print(f"  AC@3 = {baseline.get('ac_at_3', 0):.3f} (target > 0.90)")
