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

    # Graph DB (topology)
    graph_db_uri: str | None = Field(
        default=None,
        description="Graph DB URI (e.g. neo4j://host:7687). If not set, topology graph calls are disabled.",
    )
    graph_db_user: str | None = Field(
        default=None,
        description="Graph DB username (Neo4j or similar).",
    )
    graph_db_password: str | None = Field(
        default=None,
        description="Graph DB password.",
    )
    graph_db_encrypted: bool = Field(
        default=False,
        description="Whether to use encrypted connection to graph DB.",
    )

    # RAG / comment search
    comment_rag_top_k: int = Field(
        5,
        description="Number of top similar comments to retrieve from pgvector.",
    )

    # Cache / Redis
    redis_url: str | None = Field(
        default=None,
        description="Redis URL for caching; if omitted, cache is disabled.",
    )

    # LLM backend selection
    # llm_backend: Literal["bedrock", "vertex", "openai", "vllm"] = Field(
    #    "bedrock",
    #    description="Default LLM backend to use for Chat models.",
    #)

    llm_backend: Literal["bedrock", "vertex", "openai", "vllm", "llamacpp"] = Field(
        default="openai",
        description="Which LLM backend to use for planner/response/validator.",
    )

    embedding_backend: Literal["bedrock", "vertex", "openai", "vllm", "huggingface"] | None = Field(
        default=None,
        description="Backend for embeddings. If None, uses llm_backend.",
    )

    # llama.cpp / local GGUF models (e.g. mistral-7b-instruct-v0.2.Q4_K_M.gguf)
    llama_model_path: str | None = Field(
        default=None,
        description=(
            "Path to local GGUF model file for llama.cpp, e.g. "
            "/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        ),
    )
    llama_n_ctx: int = Field(
        default=4096,
        description="Context window (n_ctx) for llama.cpp models.",
    )
    llama_n_gpu_layers: int = Field(
        default=0,
        description="Number of layers to offload to GPU (-1 = all, 0 = CPU only).",
    )
    llama_n_threads: int = Field(
        default=4,
        description="Number of CPU threads to use for llama.cpp.",
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
