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
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./synapse.db"

    # --- AI Module ---
    gnn_model_path: str = "./models/deci_gnn.pt"
    anomaly_threshold: float = 0.6
    maml_inner_lr: float = 0.01
    maml_outer_lr: float = 0.001
    maml_inner_steps: int = 3
    ewc_lambda: float = 5000.0

    # --- LLM ---
    llm_provider: str = "mock"  # "mock" | "openai" | "ollama"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # --- Infrastructure ---
    prometheus_url: str = "http://localhost:9090"
    k8s_namespace: str = "default"
    recovery_dry_run: bool = True

    # --- CORS ---
    cors_origins: str = '["http://localhost:3000","http://localhost:5173"]'

    # --- Notifications ---
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""
    notify_on_complete: bool = True
    dashboard_url: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.cors_origins)
        except (json.JSONDecodeError, TypeError):
            return ["*"]


settings = Settings()


