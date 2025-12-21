from __future__ import annotations

import json
from typing import Any, Callable, Optional

import redis.asyncio as redis


def create_redis_client(
    redis_url: str,
    *,
    decode_responses: bool = False,
) -> redis.Redis:
    """
    Create an async Redis client from a URL.

    This is a thin wrapper over `redis.asyncio.from_url` so that callers
    outside of src/dependencies.py can also create their own clients if
    they want to (e.g., for background workers, tests, etc.).

    Example:
        client = create_redis_client("redis://localhost:6379/0")
    """
    return redis.from_url(redis_url, decode_responses=decode_responses)


class RedisCache:
    """
    Convenience wrapper around an async Redis client for simple caching
    patterns (string + JSON + TTL + namespaced keys).

    This class does NOT manage the underlying connection lifecycle.
    The caller is responsible for:
      - passing in a client (e.g., from dependencies.get_redis_client())
      - closing it at shutdown (which you already do in dependencies.close_resources()).
    """

    def __init__(self, client: redis.Redis, *, prefix: str = "topology-agent:"):
        self._client = client
        # Ensure prefix always ends with a colon
        self._prefix = prefix if prefix.endswith(":") else f"{prefix}:"

    def _key(self, key: str) -> str:
        """Build a namespaced key."""
        return f"{self._prefix}{key}"

    # --------------------------------------------------------------------- #
    # Basic string caching
    # --------------------------------------------------------------------- #

    async def get_str(self, key: str) -> Optional[str]:
        """
        Get a simple string value from the cache.

        Returns None if the key is not present or the client is missing.
        """
        if self._client is None:
            return None
        value = await self._client.get(self._key(key))
        return value  # type: ignore[return-value]

    async def set_str(
        self,
        key: str,
        value: str,
        *,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Set a simple string value in the cache with an optional TTL.
        """
        if self._client is None:
            return

        namespaced = self._key(key)
        if ttl_seconds is not None:
            await self._client.set(namespaced, value, ex=ttl_seconds)
        else:
            await self._client.set(namespaced, value)

    # --------------------------------------------------------------------- #
    # JSON caching
    # --------------------------------------------------------------------- #

    async def get_json(self, key: str) -> Optional[Any]:
        """
        Get a JSON-serialized value from the cache and decode it.

        Returns None if the key is missing or decoding fails.
        """
        raw = await self.get_str(key)
        if raw is None:
            return None

        try:
            return json.loads(raw)
        except Exception:
            # If deserialization fails, you may want to log this later.
            return None

    async def set_json(
        self,
        key: str,
        value: Any,
        *,
        ttl_seconds: Optional[int] = None,
        encoder: Callable[[Any], str] | None = None,
    ) -> None:
        """
        Serialize a value as JSON and store it in the cache.

        Optionally accepts a custom encoder if you want special handling
        for non-JSON-native objects.
        """
        if encoder is not None:
            raw = encoder(value)
        else:
            raw = json.dumps(value, separators=(",", ":"))

        await self.set_str(key, raw, ttl_seconds=ttl_seconds)

    # --------------------------------------------------------------------- #
    # Invalidation helpers
    # --------------------------------------------------------------------- #

    async def delete(self, key: str) -> None:
        """
        Delete a single key from the cache.
        """
        if self._client is None:
            return
        await self._client.delete(self._key(key))

    async def invalidate_pattern(self, pattern: str) -> None:
        """
        Delete keys matching a pattern in this cache's namespace.

        Pattern applies only after the prefix.

        Example:
            cache.invalidate_pattern("topology:paths:*")
        """
        if self._client is None:
            return

        # Construct namespaced pattern
        namespaced_pattern = self._key(pattern)

        # Use SCAN to avoid blocking Redis for large keyspaces.
        async for key in self._client.scan_iter(match=namespaced_pattern):
            await self._client.delete(key)
