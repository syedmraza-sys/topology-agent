from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, HttpUrl
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
    cors_allow_origins: list[str] = Field(
        default=["*"],
        description="List of allowed CORS origins.",
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

    llm_backend: Literal["bedrock", "vertex", "openai", "vllm", "ollama"] = Field(
        default="openai",
        description="Which LLM backend to use for planner/response/validator.",
    )

    embedding_backend: Literal["bedrock", "vertex", "openai", "vllm", "huggingface"] | None = Field(
        default=None,
        description="Backend for embeddings. If None, uses llm_backend.",
    )

    # Budgets
    global_llm_budget: float = Field(
        100.0,
        description="Global budget for LLM API costs.",
    )
    user_llm_budget: float = Field(
        10.0,
        description="Per-user budget for LLM API costs.",
    )
    fallback_backend: Literal["bedrock", "vertex", "openai", "vllm", "ollama"] = Field(
        "ollama",
        description="Backend to use when budget is exceeded.",
    )

    # Ollama models (e.g. mistral)
    ollama_model: str = Field(
        default="mistral",
        description="Ollama model to use.",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for the Ollama service.",
    )

    # Optional tuning parameters for Ollama
    ollama_num_ctx: int | None = Field(
        default=None,
        description="Context window size (num_ctx).",
    )
    ollama_num_predict: int | None = Field(
        default=None,
        description="Maximum number of tokens to predict (num_predict).",
    )
    ollama_num_gpu: int | None = Field(
        default=None,
        description="Number of layers to offload to GPU.",
    )
    ollama_num_thread: int | None = Field(
        default=None,
        description="Number of CPU threads to use for Ollama.",
    )
    ollama_temperature: float | None = Field(
        default=None,
        description="Temperature for Ollama (overrides agent defaults).",
    )
    ollama_top_k: int | None = Field(
        default=None,
        description="Top-K sampling for Ollama.",
    )
    ollama_top_p: float | None = Field(
        default=None,
        description="Top-P sampling for Ollama.",
    )
    ollama_repeat_penalty: float | None = Field(
        default=None,
        description="Repeat penalty for Ollama.",
    )
    ollama_keep_alive: str | int | None = Field(
        default=None,
        description="Keep alive time for Ollama models (e.g. '5m', or -1).",
    )

    # Resilience
    tool_retry_max_attempts: int = Field(
        3,
        description="Maximum number of retry attempts for tools.",
    )
    tool_retry_min_wait: float = Field(
        1.0,
        description="Minimum wait time between tool retries (seconds).",
    )
    tool_retry_max_wait: float = Field(
        10.0,
        description="Maximum wait time between tool retries (seconds).",
    )

    # LLM Retries
    llm_retry_max_attempts: int = Field(
        3,
        description="Maximum number of retry attempts for LLM calls.",
    )

    # Circuit Breaker
    tool_circuit_failure_threshold: int = Field(
        5,
        description="Number of failures before tripping tool circuit breaker.",
    )
    tool_circuit_recovery_timeout: int = Field(
        60,
        description="Timeout (seconds) before trying a tripped tool again.",
    )


    # Optional: LangSmith
    langsmith_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TOPOLOGY_AGENT_LANGSMITH_API_KEY", "LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"),
        description="LangSmith API key (optional).",
    )
    langsmith_project: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TOPOLOGY_AGENT_LANGSMITH_PROJECT", "LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"),
        description="LangSmith project name (optional).",
    )
    langsmith_endpoint: HttpUrl | None = Field(
        default=None,
        validation_alias=AliasChoices("TOPOLOGY_AGENT_LANGSMITH_ENDPOINT", "LANGSMITH_ENDPOINT", "LANGCHAIN_ENDPOINT"),
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
