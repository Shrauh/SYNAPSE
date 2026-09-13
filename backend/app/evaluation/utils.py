"""
SYNAPSE Evaluation Utilities
----------------------------

Utility helpers used by the evaluation framework.

Features:
- Execution timer
- Timestamp generation
- JSON report saving
- Markdown report saving
- Random incident generation
- Input validation

"""

from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class Timer:
    """
    Simple execution timer.
    """

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        self.end_time = time.perf_counter()
        return self.elapsed()

    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0

        end = self.end_time if self.end_time else time.perf_counter()
        return round(end - self.start_time, 6)


def current_timestamp() -> str:
    """
    Returns UTC timestamp.
    """

    return datetime.now(timezone.utc).isoformat()


def save_json_report(report: Dict[str, Any], filepath: str) -> None:
    """
    Save report as JSON.
    """

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


def save_markdown_report(text: str, filepath: str) -> None:
    """
    Save report as Markdown.
    """

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def validate_probability(value: float) -> bool:
    """
    Validate probability.
    """

    return 0.0 <= value <= 1.0


def generate_dummy_incident() -> Dict[str, Any]:
    """
    Generate a random incident.
    """

    services = [
        "payment-service",
        "user-service",
        "notification-service",
        "inventory-service",
        "gateway-service",
    ]

    faults = [
        "cpu_spike",
        "memory_leak",
        "network_latency",
        "database_timeout",
        "pod_crash",
    ]

    severities = [
        "low",
        "medium",
        "high",
        "critical",
    ]

    return {
        "incident_id": random.randint(1000, 9999),
        "service": random.choice(services),
        "fault": random.choice(faults),
        "severity": random.choice(severities),
        "timestamp": current_timestamp(),
    }


def pretty_print(title: str) -> None:
    """
    Console heading.
    """

    print("\n" + "=" * 60)
    print(title.center(60))
    print("=" * 60)


if __name__ == "__main__":

    pretty_print("SYNAPSE Utility Test")

    timer = Timer()

    timer.start()

    incident = generate_dummy_incident()

    elapsed = timer.stop()

    print("Generated Incident")
    print(incident)

    print(f"\nExecution Time : {elapsed:.6f} sec")

    report = {
        "status": "success",
        "incident": incident,
        "latency": elapsed,
    }

    save_json_report(report, "evaluation_reports/sample_report.json")

    save_markdown_report(
        "# SYNAPSE Report\n\nUtility module working successfully.",
        "evaluation_reports/sample_report.md",
    )

    print("\nReports saved successfully.")