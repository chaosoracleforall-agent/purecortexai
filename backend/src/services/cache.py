"""
Redis Cache Service for PureCortex.

Provides a centralized caching layer with TTL-based expiration
for API endpoint responses.
"""

import json
import os
import functools
from typing import Any, Callable, Optional

import redis.asyncio as aioredis


# Default TTLs for different data categories (seconds)
TTL_SUPPLY = 60
TTL_TREASURY = 30
TTL_BURNS = 300
TTL_AGENTS = 120
TTL_GOVERNANCE = 600


class CacheService:
    """Async Redis cache client for PureCortex."""

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
            )
            # Test connectivity — swallow errors so the app starts without Redis
            try:
                await self._redis.ping()
            except Exception as e:
                print(f"Warning: Redis not available at {self.redis_url}: {e}")
                self._redis = None

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        """Get a cached value, returns None if not found or Redis unavailable."""
        if not self._redis:
            return None
        try:
            raw = await self._redis.get(key)
            if raw is not None:
                return json.loads(raw)
        except Exception:
            pass
        return None

    async def set(self, key: str, value: Any, ttl: int = 60):
        """Set a cached value with TTL in seconds."""
        if not self._redis:
            return
        try:
            await self._redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            pass

    async def delete(self, key: str):
        """Delete a cached key."""
        if not self._redis:
            return
        try:
            await self._redis.delete(key)
        except Exception:
            pass

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
