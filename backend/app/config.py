"""
SYNAPSE Configuration — Pydantic Settings with .env support.

All configuration is centralized here and loaded from environment
variables or a .env file. Import `settings` anywhere in the app.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "SYNAPSE"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./synapse.db"

    # --- AI Module ---
    gnn_model_path: str = "./models/deic_gnn.pt"
    anomaly_threshold: float = 0.6
    maml_inner_lr: float = 0.01
    maml_outer_lr: float = 0.001
    maml_inner_steps: int = 3
    ewc_lambda: float = 5000.0

    # --- LLM (Groq primary, OpenAI fallback, mock last resort) ---
    llm_provider: str = "groq"          # "groq" | "openai" | "mock"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- Remediation ---
    remediation_confidence_threshold: float = 0.85
    rollback_confidence_threshold: float = 0.90   # Higher bar for rollback
    k8s_namespace: str = "default"
    k8s_enabled: bool = False          # False = simulation mode
    remediation_auto_execute: bool = True

    # --- Kafka ---
    kafka_enabled: bool = False         # False = no Kafka needed in local dev
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_metrics_topic: str = "metrics-topic"
    kafka_logs_topic: str = "logs-topic"
    kafka_traces_topic: str = "traces-topic"
    kafka_alerts_topic: str = "alerts-topic"
    kafka_remediation_topic: str = "remediation-topic"

    # --- RAG / ChromaDB ---
    chroma_persist_directory: str = "./chroma_db"
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- CORS ---
    cors_origins: str = '["http://localhost:3000","http://localhost:5173","http://127.0.0.1:5173"]'

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.cors_origins)
        except (json.JSONDecodeError, TypeError):
            return ["*"]


settings = Settings()
