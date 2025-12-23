from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as redis
import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import Settings, get_settings
from .logging_config import setup_logging
from .db.graph_client import GraphClient  # NEW

# LangGraph compiled graph type; orchestrator.workflow.build_workflow will come later.
try:
    from langgraph.graph import CompiledGraph  # type: ignore
except Exception:  # pragma: no cover
    CompiledGraph = Any  # type: ignore


# Global singletons initialized at startup
_engine: AsyncEngine | None = None
_SessionLocal: async_sessionmaker[AsyncSession] | None = None
_redis_client: redis.Redis | None = None
_graph_app: CompiledGraph | None = None # LangGraph compiled graph
_graph_client: GraphClient | None = None  # NEW; Graph DB client

async def init_resources() -> None:
    """
    Initialize shared resources:

    - structlog logging
    - async DB engine + sessionmaker
    - Redis client (optional)
    - LangGraph compiled graph_app
    """
    global _engine, _SessionLocal, _redis_client, _graph_app

    # Logging first so everything after can log nicely
    setup_logging()
    log = structlog.get_logger("startup")
    settings = get_settings()

    log.info("initializing_resources", env=settings.env)

    # Database
    _engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
    )
    _SessionLocal = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    log.info("database_initialized")

    # Redis (optional)
    if settings.redis_url:
        _redis_client = redis.from_url(settings.redis_url)
        log.info("redis_initialized", redis_url=settings.redis_url)
    else:
        _redis_client = None
        log.info("redis_disabled")

    # Graph DB client (optional)
    global _graph_client
    if settings.graph_db_uri and settings.graph_db_user and settings.graph_db_password:
        try:
            _graph_client = await GraphClient.from_neo4j(
                uri=settings.graph_db_uri,
                user=settings.graph_db_user,
                password=settings.graph_db_password,
                encrypted=settings.graph_db_encrypted,
            )
            log.info("graph_client_initialized", uri=settings.graph_db_uri)
        except Exception as exc:  # pragma: no cover
            _graph_client = None
            log.warning(
                "graph_client_init_failed",
                uri=settings.graph_db_uri,
                error=str(exc),
            )
    else:
        _graph_client = None
        log.info("graph_client_disabled")

   
    # LangGraph graph: import lazily to avoid circular imports
    try:
        from .orchestrator.workflow import build_workflow  # type: ignore

        _graph_app = build_workflow()
        log.info("graph_app_initialized")
    except Exception as exc:  # pragma: no cover - orchestrator may not exist yet
        _graph_app = None
        log.warning(
            "graph_app_not_initialized",
            reason="build_workflow import or execution failed",
            error=str(exc),
        )


async def close_resources() -> None:
    """
    Clean up global resources gracefully at shutdown.
    """
    log = structlog.get_logger("shutdown")

    # DB
    if _engine is not None:
        await _engine.dispose()
        log.info("database_disposed")

    # Redis
    if _redis_client is not None:
        await _redis_client.close()
        log.info("redis_closed")

    # Graph client
    global _graph_client
    if _graph_client is not None:
        await _graph_client.close()
        log.info("graph_client_closed")
        _graph_client = None

    # graph_app typically doesn't require explicit cleanup.


def get_settings_dep() -> Settings:
    """
    FastAPI dependency wrapper for Settings.
    """
    return get_settings()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession.
    """
    if _SessionLocal is None:
        raise RuntimeError("Database session factory not initialized. Did you call init_resources()?")

    async with _SessionLocal() as session:
        yield session


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Expose the AsyncSession factory so orchestrator tools can open
    their own sessions outside of FastAPI dependency injection.
    """
    if _SessionLocal is None:
        raise RuntimeError("Database session factory not initialized. Did you call init_resources()?")

    return _SessionLocal


def get_redis_client() -> redis.Redis | None:
    """
    FastAPI dependency for Redis client (can be None if disabled).
    """
    return _redis_client


def get_graph_app() -> CompiledGraph:
    """
    FastAPI dependency that returns the compiled LangGraph graph.

    Raises RuntimeError if it was not initialized.
    """
    if _graph_app is None:
        raise RuntimeError("graph_app not initialized. Did you call init_resources()?")

    return _graph_app


def get_logger() -> structlog.BoundLogger:
    """
    FastAPI dependency returning a structlog logger.

    Request-specific context (like request_id) can be bound via middleware later.
    """
    return structlog.get_logger("service")


def get_context_logger(settings: Settings = Depends(get_settings_dep)) -> structlog.BoundLogger:
    """
    Logger bound with basic contextual info (env, app_name).
    """
    logger = structlog.get_logger("service")
    return logger.bind(env=settings.env, app=settings.app_name)

def get_graph_client() -> GraphClient | None:
    """
    Accessor for the global GraphClient.

    Can return None if graph DB is not configured or failed at startup.
    Orchestrator tools should handle the None case gracefully (e.g., mark
    responses as partial).
    """
    return _graph_client
