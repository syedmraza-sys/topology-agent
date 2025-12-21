from __future__ import annotations

from fastapi import APIRouter

from . import chat, metrics, system, topology

__all__ = ["router", "topology", "chat", "system", "metrics"]

# Optional aggregate router if you ever want to mount everything under one router.
router = APIRouter()
router.include_router(system.router)
router.include_router(metrics.router)
router.include_router(chat.router)
router.include_router(topology.router)
