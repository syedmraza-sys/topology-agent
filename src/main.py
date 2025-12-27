from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .dependencies import close_resources, init_resources
from .api import chat, metrics, system, topology
from .api.http_metrics import API_REQUESTS, API_REQUEST_DURATION


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context:
    - Initialize shared resources (DB engine, Redis, LangGraph graph, etc.)
    - Clean them up on shutdown
    """
    await init_resources()
    try:
        yield
    finally:
        await close_resources()


def create_app() -> FastAPI:
    """
    Application factory for the topology agent API.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url=f"{settings.api_prefix.rstrip('/')}/docs",
        openapi_url=f"{settings.api_prefix.rstrip('/')}/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def http_metrics_middleware(request: Request, call_next):
        """
        Middleware to record per-route HTTP metrics for Prometheus.

        Exposes:
          - topology_api_requests_total{path,method,status}
          - topology_api_request_duration_seconds{path,method}
        """
        start = time.perf_counter()
        path = request.url.path
        method = request.method.upper()
        status_code: int | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            # Treat unhandled exceptions as HTTP 500 for metrics purposes.
            status_code = 500
            raise
        finally:
            status_str = str(status_code) if status_code is not None else "unknown"
            duration = time.perf_counter() - start

            # Increment request counter
            API_REQUESTS.labels(
                path=path,
                method=method,
                status=status_str,
            ).inc()

            # Observe latency
            API_REQUEST_DURATION.labels(
                path=path,
                method=method,
            ).observe(duration)

    # Router registration
    api_prefix = settings.api_prefix.rstrip("/")

    app.include_router(system.router, prefix=api_prefix)
    app.include_router(metrics.router, prefix=api_prefix)
    app.include_router(chat.router, prefix=api_prefix)
    app.include_router(topology.router, prefix=api_prefix)

    return app


# ASGI entrypoint for uvicorn / hypercorn, etc.
# e.g. uvicorn src.main:app --reload
app = create_app()
