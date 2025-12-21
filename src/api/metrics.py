from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics() -> Response:
    """
    Expose Prometheus metrics for this service.

    This assumes you're using prometheus-client and registering metrics in
    your code (e.g. in orchestrator nodes, db clients, etc.).
    """
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
