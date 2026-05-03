"""
Redis client for RAGEve caching.

Provides async-compatible interface for FastAPI.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from backend.config_loader import get_settings

_log = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client with connection pooling."""

    def __init__(self) -> None:
        settings = get_settings()
        self.host = settings.redis.host
        self.port = int(settings.redis.port)
        self.db = int(settings.redis.db)
        self.password = settings.redis.password or None

        # Create connection pool
        self.pool = ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True,
            max_connections=50,
        )

        self._client: redis.Redis | None = None

    async def get_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if self._client is None:
            self._client = redis.Redis(connection_pool=self.pool)
        return self._client

    async def ping(self) -> bool:
        """Test Redis connection."""
        try:
            client = await self.get_client()
            return await client.ping()
        except Exception as e:
            _log.error("Redis ping failed: %s", e)
            return False

    async def get(self, key: str) -> Any:
        """Get value from Redis with automatic JSON deserialization."""
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            _log.warning("Redis get error for key '%s': %s", key, e)
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in Redis with optional TTL (seconds)."""
        try:
            client = await self.get_client()
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return await client.set(key, value, ex=ttl)
        except Exception as e:
            _log.warning("Redis set error for key '%s': %s", key, e)
            return False

    async def delete(self, key: str) -> int:
        """Delete key from Redis. Returns number of deleted keys."""
        try:
            client = await self.get_client()
            return await client.delete(key)
        except Exception as e:
            _log.warning("Redis delete error for key '%s': %s", key, e)
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            client = await self.get_client()
            return bool(await client.exists(key))
        except Exception as e:
            _log.warning("Redis exists error for key '%s': %s", key, e)
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern. Returns count of deleted keys."""
        try:
            client = await self.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            _log.warning("Redis clear_pattern error for pattern '%s': %s", pattern, e)
            return 0

    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.close()
        await self.pool.disconnect()
        _log.info("Redis connection pool closed")


# Singleton instance
_redis_client: RedisClient | None = None


def get_redis_client() -> RedisClient:
    """Get or create Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


async def init_redis() -> None:
    """Initialize Redis connection (call on startup)."""
    client = get_redis_client()
    if await client.ping():
        _log.info("Redis connection established")
    else:
        _log.warning("Redis ping failed - caching disabled")


async def close_redis() -> None:
    """Close Redis connection (call on shutdown)."""
    client = get_redis_client()
    await client.close()
