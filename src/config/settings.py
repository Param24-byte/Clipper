"""
Application configuration — loaded once at startup from environment / .env.
All other modules should import `get_settings()` rather than os.environ directly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_log_level: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://clipper:clipper@localhost:5432/clipper"
    database_sync_url: str = "postgresql+psycopg2://clipper:clipper@localhost:5432/clipper"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Artifact storage ──────────────────────────────────────────────────────
    artifact_storage_backend: Literal["local", "s3"] = "local"
    artifact_local_root: str = "./artifacts"

    # ── Security ──────────────────────────────────────────────────────────────
    secret_key: str = "changeme-replace-in-production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
