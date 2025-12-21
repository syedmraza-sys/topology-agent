from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .. import __version__
from ..config import Settings, get_settings
from ..dependencies import get_db_session, get_logger, get_redis_client

router = APIRouter(tags=["system"])


@router.get("/health", summary="Liveness check")
async def health() -> Dict[str, str]:
    """
    Simple liveness check to verify the process is running.
    """
    return {"status": "ok"}


@router.get("/ready", summary="Readiness check")
async def ready(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    logger=Depends(get_logger),
) -> Dict[str, Any]:
    """
    Readiness probe: check DB (and optionally Redis) connectivity.

    This is what Kubernetes / a load balancer should use to decide if this instance
    is ready to receive traffic.
    """
    log = logger
    status: Dict[str, Any] = {
        "status": "ok",
        "db": "unknown",
        "redis": "unknown",
    }

    # DB check
    try:
        await db.execute(text("SELECT 1"))
        status["db"] = "ok"
    except Exception as exc:  # pragma: no cover - network/db issues
        log.error("ready_db_check_failed", error=str(exc))
        status["db"] = f"error: {exc}"
        status["status"] = "degraded"

    # Redis check
    redis_client = get_redis_client()
    if redis_client is None:
        status["redis"] = "disabled"
    else:
        try:
            await redis_client.ping()
            status["redis"] = "ok"
        except Exception as exc:  # pragma: no cover
            log.error("ready_redis_check_failed", error=str(exc))
            status["redis"] = f"error: {exc}"
            status["status"] = "degraded"

    return status


@router.get("/version", summary="Service version")
async def version(settings: Settings = Depends(get_settings)) -> Dict[str, str]:
    """
    Report application version and environment.
    """
    return {
        "app_name": settings.app_name,
        "version": __version__,
        "env": settings.env,
    }
