"""
SYNAPSE Kafka Producer — Publishes events to Kafka topics.

Publishes:
  - Remediation actions to remediation-topic
  - RCA results to alerts-topic
  - Anomaly detections to alerts-topic

Falls back gracefully when Kafka is not available.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.config import settings

logger = logging.getLogger(__name__)


class KafkaProducerService:
    """Async Kafka producer for SYNAPSE events."""

    def __init__(self) -> None:
        self._producer = None
        self._available = False

    async def start(self) -> None:
        """Initialize the Kafka producer."""
        if not settings.kafka_enabled:
            logger.info("[Kafka Producer] Disabled (KAFKA_ENABLED=false)")
            return
        try:
            from aiokafka import AIOKafkaProducer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self._producer.start()
            self._available = True
            logger.info("[Kafka Producer] Started")
        except Exception as e:
            logger.warning(f"[Kafka Producer] Failed to start: {e}")

    async def stop(self) -> None:
        """Stop the producer."""
        if self._producer:
            try:
                await self._producer.stop()
            except Exception:
                pass

    async def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a Kafka topic.

        Args:
            topic: Target topic name.
            message: JSON-serializable dict.

        Returns:
            True if published, False if unavailable (silently drops).
        """
        if not self._available or not self._producer:
            return False
        try:
            message["_published_at"] = datetime.now(timezone.utc).isoformat()
            await self._producer.send_and_wait(topic, message)
            return True
        except Exception as e:
            logger.error(f"[Kafka Producer] Failed to publish to {topic}: {e}")
            return False

    async def publish_remediation_action(
        self, action_id: str, service: str, status: str, incident_id: str
    ) -> None:
        """Publish a remediation action result."""
        await self.publish(settings.kafka_remediation_topic, {
            "action_id": action_id,
            "service": service,
            "status": status,
            "incident_id": incident_id,
        })

    async def publish_rca_result(
        self, incident_id: str, root_cause: str, confidence: float, fault_type: str
    ) -> None:
        """Publish an RCA result to alerts-topic."""
        await self.publish(settings.kafka_alerts_topic, {
            "alert_name": "RCAComplete",
            "incident_id": incident_id,
            "root_cause": root_cause,
            "confidence": confidence,
            "fault_type": fault_type,
            "severity": "high" if confidence > 0.8 else "medium",
        })

    async def publish_anomaly(
        self, service: str, anomaly_score: float
    ) -> None:
        """Publish an anomaly detection event."""
        await self.publish(settings.kafka_alerts_topic, {
            "alert_name": "AnomalyDetected",
            "service": service,
            "value": anomaly_score,
            "threshold": settings.anomaly_threshold,
            "severity": "critical" if anomaly_score > 0.9 else "warning",
        })


# Module-level singleton
kafka_producer = KafkaProducerService()
