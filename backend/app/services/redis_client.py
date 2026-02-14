"""
Redis client for caching and job queue operations.
Provides async interface for Redis operations.
"""
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """
    Async Redis client wrapper.
    Provides high-level operations for caching and rate limiting.
    """

    def __init__(self, redis_client: redis.Redis):
        """Initialize Redis client."""
        self.client = redis_client

    async def get(self, key: str) -> str | None:
        """
        Get value by key.

        Args:
            key: Redis key

        Returns:
            Value if exists, None otherwise
        """
        value = await self.client.get(key)
        return value.decode("utf-8") if value else None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None
    ) -> bool:
        """
        Set key-value pair with optional TTL.

        Args:
            key: Redis key
            value: Value to store
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        if ttl:
            return await self.client.setex(key, ttl, value)
        return await self.client.set(key, value)

    async def delete(self, key: str) -> bool:
        """
        Delete key.

        Args:
            key: Redis key to delete

        Returns:
            True if key was deleted
        """
        result = await self.client.delete(key)
        return result > 0

    async def incr(self, key: str) -> int:
        """
        Increment counter.

        Args:
            key: Counter key

        Returns:
            New counter value
        """
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration on key.

        Args:
            key: Redis key
            seconds: Expiration time in seconds

        Returns:
            True if expiration was set
        """
        return await self.client.expire(key, seconds)

    async def ping(self) -> bool:
        """
        Check Redis connectivity.

        Returns:
            True if Redis is reachable
        """
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        await self.client.close()


# Global Redis client instance
_redis_client: RedisClient | None = None


async def get_redis_client() -> RedisClient:
    """
    Get Redis client instance.
    Creates connection pool on first call.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        settings = get_settings()
        pool = redis.ConnectionPool.from_url(
            str(settings.redis_dsn),
            decode_responses=False,
            max_connections=10,
        )
        client = redis.Redis(connection_pool=pool)
        _redis_client = RedisClient(client)
        logger.info("Redis client initialized")

    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")
