"""
SYNAPSE ORM Models — SQLAlchemy table definitions.

Stores incidents, RCA results, service metrics, and model metadata.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _gen_id() -> str:
    return f"inc_{uuid.uuid4().hex[:8]}"


class Incident(Base):
    """A detected or manually created incident."""

    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_gen_id)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="analyzing"
    )  # analyzing | detected | resolved
    severity: Mapped[str] = mapped_column(
        String(16), default="medium"
    )  # critical | high | medium | low
    root_cause_service: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    fault_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    affected_services: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    anomaly_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeline: Mapped[list | None] = mapped_column(JSON, nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RCAResult(Base):
    """Stored RCA report for an incident."""

    __tablename__ = "rca_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    root_cause_service: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    fault_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    propagation_chain: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metric_deltas: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommended_actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    causal_graph: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class ServiceMetric(Base):
    """Time-series service metric snapshot."""

    __tablename__ = "service_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latency: Mapped[float] = mapped_column(Float, default=0.0)
    error_rate: Mapped[float] = mapped_column(Float, default=0.0)
    cpu: Mapped[float] = mapped_column(Float, default=0.0)
    memory: Mapped[float] = mapped_column(Float, default=0.0)
    request_rate: Mapped[float] = mapped_column(Float, default=0.0)
