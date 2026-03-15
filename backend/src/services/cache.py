"""
Redis Cache Service for PURECORTEX.

Provides a centralized caching layer with TTL-based expiration
for API endpoint responses.
"""

import asyncio
import json
import logging
import os
import functools
from typing import Any, Callable, Optional

import redis.asyncio as aioredis

logger = logging.getLogger("purecortex.cache")

# Redis command timeout (seconds)
REDIS_CMD_TIMEOUT = 5

# Default TTLs for different data categories (seconds)
TTL_SUPPLY = 60
TTL_TREASURY = 30
TTL_BURNS = 300
TTL_AGENTS = 120
TTL_GOVERNANCE = 600


class CacheService:
    """Async Redis cache client for PURECORTEX."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Establish connection to Redis."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=REDIS_CMD_TIMEOUT,
            )
            # Test connectivity — swallow errors so the app starts without Redis
            try:
                await asyncio.wait_for(self._redis.ping(), timeout=REDIS_CMD_TIMEOUT)
            except Exception as e:
                logger.warning("Redis not available at %s: %s", self.redis_url, e)
                self._redis = None

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def ping(self) -> bool:
        """Check Redis connectivity. Returns True if reachable."""
        if not self._redis:
            return False
        try:
            return await asyncio.wait_for(self._redis.ping(), timeout=REDIS_CMD_TIMEOUT)
        except Exception:
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a cached value, returns None if not found or Redis unavailable."""
        if not self._redis:
            return None
        try:
            raw = await asyncio.wait_for(self._redis.get(key), timeout=REDIS_CMD_TIMEOUT)
            if raw is not None:
                return json.loads(raw)
        except asyncio.TimeoutError:
            logger.warning("Redis GET timed out for key: %s", key)
        except Exception as exc:
            logger.warning("Redis GET failed for key %s: %s", key, exc)
        return None

    async def set(self, key: str, value: Any, ttl: int = 60):
        """Set a cached value with TTL in seconds."""
        if not self._redis:
            return
        try:
            await asyncio.wait_for(
                self._redis.setex(key, ttl, json.dumps(value, default=str)),
                timeout=REDIS_CMD_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("Redis SET timed out for key: %s", key)
        except Exception as exc:
            logger.warning("Redis SET failed for key %s: %s", key, exc)

    async def delete(self, key: str):
        """Delete a cached key."""
        if not self._redis:
            return
        try:
            await asyncio.wait_for(self._redis.delete(key), timeout=REDIS_CMD_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning("Redis DELETE timed out for key: %s", key)
        except Exception as exc:
            logger.warning("Redis DELETE failed for key %s: %s", key, exc)

    @property
    def available(self) -> bool:
        return self._redis is not None


def cache_with_ttl(key: str, ttl_seconds: int):
    """
    Decorator that caches the return value of an async endpoint function.

    The decorated function must be an async function returning a dict
    (or Pydantic-serializable object).

    Usage:
        @cache_with_ttl("transparency:supply", TTL_SUPPLY)
        async def get_supply():
            ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_service()
            # Try cache first
            cached = await cache.get(key)
            if cached is not None:
                return cached

            # Call the underlying function
            result = await func(*args, **kwargs)

            # Store in cache
            result_dict = result
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            elif hasattr(result, "dict"):
                result_dict = result.dict()

            await cache.set(key, result_dict, ttl_seconds)
            return result

        return wrapper

    return decorator


# Module-level singleton
_cache: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create the singleton CacheService instance."""
    global _cache
    if _cache is None:
        _cache = CacheService()
    return _cache
