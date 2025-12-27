from __future__ import annotations

"""
Prometheus HTTP metrics for the FastAPI layer.

These are generic per-route metrics with labels:
- path (e.g. /api/topology/query)
- method (GET/POST/...)
- status (HTTP status code as string)

From these, you can derive things like:
- topology_requests_total:
    sum by(status)(topology_api_requests_total{path="/api/topology/query"})
"""

from prometheus_client import Counter, Histogram

API_REQUESTS = Counter(
    "topology_api_requests_total",
    "Total number of HTTP requests received by the API",
    labelnames=("path", "method", "status"),
)

API_REQUEST_DURATION = Histogram(
    "topology_api_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=("path", "method"),
)
