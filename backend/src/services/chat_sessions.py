"""Ephemeral chat session tokens backed by Redis."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis.asyncio as redis


SESSION_PREFIX = "cxs_"
REDIS_SESSION_PREFIX = "chat_session:"
DEFAULT_TTL_SECONDS = int(os.getenv("CHAT_SESSION_TTL_SECONDS", "900"))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class ChatSessionManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def create_session(
        self,
        *,
        owner: str,
        tier: str,
        api_key: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> dict:
        ttl = ttl_seconds or DEFAULT_TTL_SECONDS
        raw_token = SESSION_PREFIX + secrets.token_urlsafe(32)
        hashed = _hash_token(raw_token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)

        mapping = {
            "owner": owner,
            "tier": tier,
            "active": "1",
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        if api_key:
            mapping["api_key_hash"] = _hash_token(api_key)

        redis_key = f"{REDIS_SESSION_PREFIX}{hashed}"
        await self.redis.hset(redis_key, mapping=mapping)
        await self.redis.expire(redis_key, ttl)

        return {
            "session_token": raw_token,
            "expires_at": expires_at.isoformat(),
            "ttl_seconds": ttl,
            "owner": owner,
            "tier": tier,
        }

    async def validate_session(self, session_token: str) -> Optional[dict]:
        if not session_token or not session_token.startswith(SESSION_PREFIX):
            return None

        hashed = _hash_token(session_token)
        data = await self.redis.hgetall(f"{REDIS_SESSION_PREFIX}{hashed}")
        if not data:
            return None

        decoded = {
            key.decode() if isinstance(key, bytes) else key:
            value.decode() if isinstance(value, bytes) else value
            for key, value in data.items()
        }
        if decoded.get("active") != "1":
            return None
        return decoded

    async def revoke_session(self, session_token: str) -> bool:
        hashed = _hash_token(session_token)
        return await self.redis.hset(f"{REDIS_SESSION_PREFIX}{hashed}", "active", "0") >= 0
