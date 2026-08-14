"""
SYNAPSE Kafka Consumer — Async streaming consumer for all telemetry topics.

Consumes from 5 topics:
  - metrics-topic    → per-service CPU, latency, error_rate, memory
  - logs-topic       → structured log events (level, service, message)
  - traces-topic     → distributed trace spans
  - alerts-topic     → pre-computed alert conditions
  - remediation-topic → remediation action results

Each topic has its own consumer group for independent offset tracking.
Runs as background asyncio tasks on application startup.

Falls back gracefully when Kafka is not available (local dev mode).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """Manages async Kafka consumers for all SYNAPSE telemetry topics.

    In local development (KAFKA_ENABLED=false), this class becomes a no-op
    and the system uses the data simulator instead.
    """

    def __init__(self) -> None:
        self._consumers: Dict[str, Any] = {}
        self._tasks: list = []
        self._running = False
        self._metrics_buffer: list = []  # Rolling buffer for last 60 metrics

    async def start(self) -> None:
        """Start all Kafka consumer background tasks."""
        if not settings.kafka_enabled:
            logger.info("[Kafka] KAFKA_ENABLED=false — consumers not started (simulation mode)")
            return

        try:
            from aiokafka import AIOKafkaConsumer
        except ImportError:
            logger.warning("[Kafka] aiokafka not installed. Consumers disabled.")
            return

        self._running = True
        bootstrap = settings.kafka_bootstrap_servers

        topic_handlers = {
            settings.kafka_metrics_topic: self._handle_metrics,
            settings.kafka_logs_topic: self._handle_logs,
            settings.kafka_traces_topic: self._handle_traces,
            settings.kafka_alerts_topic: self._handle_alerts,
            settings.kafka_remediation_topic: self._handle_remediation,
        }

        for topic, handler in topic_handlers.items():
            group_id = f"synapse-{topic.replace('-topic', '')}-group"
            task = asyncio.create_task(
                self._consume_loop(topic, group_id, handler, bootstrap)
            )
            self._tasks.append(task)
            logger.info(f"[Kafka] Consumer started: {topic} (group: {group_id})")

    async def stop(self) -> None:
        """Stop all consumer tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        logger.info("[Kafka] All consumers stopped")

    async def _consume_loop(
        self,
        topic: str,
        group_id: str,
        handler: Callable,
        bootstrap: str,
    ) -> None:
        """Main consumer loop for a single topic."""
        from aiokafka import AIOKafkaConsumer

        while self._running:
            consumer = None
            try:
                consumer = AIOKafkaConsumer(
                    topic,
                    bootstrap_servers=bootstrap,
                    group_id=group_id,
                    auto_offset_reset="latest",
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=10000,
                )
                await consumer.start()
                logger.info(f"[Kafka] Connected to {topic}")

                async for msg in consumer:
                    if not self._running:
                        break
                    try:
                        await handler(msg.value)
                    except Exception as e:
                        logger.error(f"[Kafka] Handler error on {topic}: {e}")

            except Exception as e:
                logger.warning(f"[Kafka] {topic} consumer error: {e}. Retrying in 5s...")
                await asyncio.sleep(5)
            finally:
                if consumer:
                    try:
                        await consumer.stop()
                    except Exception:
                        pass

    async def _handle_metrics(self, data: Dict[str, Any]) -> None:
        """Process incoming metric events from metrics-topic.

        Expected schema:
            {
                "service": "checkout",
                "timestamp": "2024-01-01T00:00:00Z",
                "cpu_pct": 45.2,
                "mem_pct": 67.1,
                "error_rate": 0.02,
                "latency_ms": 120.5,
                "throughput_rps": 50.0
            }
        """
        service = data.get("service", "unknown")
        ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Normalize to internal feature names
        normalized = {
            "service": service,
            "timestamp": ts,
            "latency": data.get("latency_ms", 0) / 1000.0,  # ms → s
            "error_rate": data.get("error_rate", 0),
            "cpu": data.get("cpu_pct", 0) / 100.0,          # pct → 0-1
            "memory": data.get("mem_pct", 0) / 100.0,
            "request_rate": data.get("throughput_rps", 0),
        }

        self._metrics_buffer.append(normalized)
        if len(self._metrics_buffer) > 600:  # 10min at 1/s
            self._metrics_buffer = self._metrics_buffer[-600:]

        # Update graph builder with live metrics
        try:
            from app.services.graph_builder import graph_builder
            graph_builder.update_metrics(service, {
                "latency": normalized["latency"],
                "error_rate": normalized["error_rate"],
                "cpu": normalized["cpu"],
                "memory": normalized["memory"],
                "request_rate": normalized["request_rate"],
            })
        except Exception:
            pass

    async def _handle_logs(self, data: Dict[str, Any]) -> None:
        """Process structured log events from logs-topic.

        Expected schema:
            {
                "service": "checkout",
                "level": "ERROR",
                "message": "Connection timeout to orderdb",
                "timestamp": "...",
                "trace_id": "abc123"
            }
        """
        level = data.get("level", "INFO")
        service = data.get("service", "unknown")
        message = data.get("message", "")

        if level in ("ERROR", "CRITICAL"):
            logger.info(f"[Kafka/logs] {service} [{level}] {message[:100]}")

            # Broadcast error log to WebSocket clients
            try:
                from app.api.ws import manager
                await manager.broadcast({
                    "type": "log_event",
                    "data": {
                        "service": service,
                        "level": level,
                        "message": message,
                        "timestamp": data.get("timestamp"),
                    }
                })
            except Exception:
                pass

    async def _handle_traces(self, data: Dict[str, Any]) -> None:
        """Process distributed trace spans from traces-topic.

        Expected schema:
            {
                "trace_id": "abc123",
                "span_id": "def456",
                "parent_span_id": "xyz789",
                "service": "frontend",
                "operation": "GET /checkout",
                "duration_ms": 245.0,
                "status": "error"
            }
        """
        if data.get("status") == "error":
            logger.debug(
                f"[Kafka/traces] Error span: {data.get('service')} → "
                f"{data.get('operation')} ({data.get('duration_ms')}ms)"
            )

    async def _handle_alerts(self, data: Dict[str, Any]) -> None:
        """Process pre-computed alert events from alerts-topic.

        Expected schema:
            {
                "alert_name": "HighErrorRate",
                "service": "payment",
                "severity": "critical",
                "value": 0.95,
                "threshold": 0.05,
                "timestamp": "..."
            }
        """
        service = data.get("service", "unknown")
        severity = data.get("severity", "warning")
        alert_name = data.get("alert_name", "Unknown")

        logger.warning(f"[Kafka/alerts] {severity.upper()}: {alert_name} on {service}")

        # Broadcast alert to dashboard
        try:
            from app.api.ws import manager
            await manager.broadcast({
                "type": "alert",
                "data": data,
            })
        except Exception:
            pass

    async def _handle_remediation(self, data: Dict[str, Any]) -> None:
        """Process remediation action results from remediation-topic."""
        logger.info(f"[Kafka/remediation] Result: {data.get('action_id')} → {data.get('status')}")

    def get_metrics_buffer(self) -> list:
        """Return recent metrics buffer (for anomaly detection)."""
        return list(self._metrics_buffer)

    def get_status(self) -> Dict[str, Any]:
        """Return consumer status."""
        return {
            "enabled": settings.kafka_enabled,
            "running": self._running,
            "active_consumers": len(self._tasks),
            "metrics_buffer_size": len(self._metrics_buffer),
            "bootstrap_servers": settings.kafka_bootstrap_servers,
        }


# Module-level singleton
kafka_consumer = KafkaConsumerService()
