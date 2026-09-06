"""Typed runtime configuration.

The v2 service has one configuration source. Modules receive ``Settings``
explicitly instead of reading environment variables throughout the codebase.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    """Validated process configuration populated from ``HR_RAG_*`` variables."""

    model_config = SettingsConfigDict(
        env_prefix="HR_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    service_name: str = "hr-policy-rag"
    environment: Environment = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    app_version: str = "0.1.0"
    git_sha: str = "unknown"
    build_id: str = "local"
    corpus_generation: str = "not-loaded"
    index_generation: str = "not-loaded"
    request_id_header: str = "X-Request-ID"
    max_request_id_length: int = Field(default=128, ge=16, le=256)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one immutable settings instance for the process."""

    return Settings()
