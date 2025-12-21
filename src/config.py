from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    Prefix: TOPOLOGY_AGENT_

    Examples:
      TOPOLOGY_AGENT_ENV=dev
      TOPOLOGY_AGENT_DATABASE_URL=postgresql+asyncpg://user:pass@host/db
    """

    model_config = SettingsConfigDict(
        env_prefix="TOPOLOGY_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    env: Literal["dev", "staging", "prod"] = Field(
        "dev",
        description="Deployment environment name.",
    )
    app_name: str = Field(
        "Topology Agent Service",
        description="Human-friendly app name.",
    )
    debug: bool = Field(
        False,
        description="Enable debug mode for FastAPI & logging.",
    )
    log_level: str = Field(
        "INFO",
        description="Base log level (DEBUG, INFO, WARNING, ERROR).",
    )

    # HTTP
    host: str = Field(
        "0.0.0.0",
        description="Bind host.",
    )
    port: int = Field(
        8000,
        description="Bind port.",
    )
    api_prefix: str = Field(
        "/api",
        description="Base prefix for API routes.",
    )

    # Database (inventory + chat + evals)
    database_url: str = Field(
        ...,
        description="Async SQLAlchemy URL, e.g. postgresql+asyncpg://user:pass@host/db",
    )

    # Cache / Redis
    redis_url: str | None = Field(
        default=None,
        description="Redis URL for caching; if omitted, cache is disabled.",
    )

    # LLM backend selection
    llm_backend: Literal["bedrock", "vertex", "openai", "vllm"] = Field(
        "bedrock",
        description="Default LLM backend to use.",
    )

    # Optional: LangSmith
    langsmith_api_key: str | None = Field(
        default=None,
        description="LangSmith API key (optional).",
    )
    langsmith_project: str | None = Field(
        default=None,
        description="LangSmith project name (optional).",
    )
    langsmith_endpoint: HttpUrl | None = Field(
        default=None,
        description="Custom LangSmith endpoint (optional).",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached singleton settings object.

    Usage:
        from src.config import get_settings
        settings = get_settings()
    """
    return Settings()
