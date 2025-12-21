from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .dependencies import close_resources, init_resources


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context:

    - Initialize global resources at startup
    - Dispose/close them at shutdown
    """
    await init_resources()
    try:
        yield
    finally:
        await close_resources()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version=__version__,
        lifespan=lifespan,
    )

    # CORS (adjust allowed origins for prod)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers from src/api/*
    # These modules will be implemented separately.
    from .api import chat, metrics, system, topology  # type: ignore

    api_prefix = settings.api_prefix.rstrip("/")

    app.include_router(system.router, prefix=api_prefix)
    app.include_router(metrics.router, prefix=api_prefix)
    app.include_router(chat.router, prefix=api_prefix)
    app.include_router(topology.router, prefix=api_prefix)

    return app


# ASGI entrypoint for uvicorn / hypercorn, etc.
# e.g. uvicorn src.main:app --reload
app = create_app()
