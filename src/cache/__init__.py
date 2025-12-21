from __future__ import annotations

"""
Cache utilities for the topology agent.

This package provides:
- A thin async Redis client factory
- A RedisCache helper with convenience methods for string/JSON caching

The global Redis client is managed in src/dependencies.py and can be
passed into RedisCache where needed.
"""

from .redis_client import RedisCache, create_redis_client

__all__ = [
    "RedisCache",
    "create_redis_client",
]
