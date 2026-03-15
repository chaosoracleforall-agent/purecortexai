"""API key management for PURECORTEX."""
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger("purecortex.api_keys")

# Key format: ctx_<32 hex chars>
KEY_PREFIX = "ctx_"
REDIS_KEY_PREFIX = "apikey:"

# Rate limit tiers
TIERS = {
    "free": {"rpm": 30, "label": "Free"},
    "paid": {"rpm": 300, "label": "Paid"},
    "admin": {"rpm": 1000, "label": "Admin"},
}


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def _decode_hash(data: dict) -> dict:
    return {
        key.decode() if isinstance(key, bytes) else key:
        value.decode() if isinstance(value, bytes) else value
        for key, value in data.items()
    }


class APIKeyManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def create_key(self, owner: str, tier: str = "free") -> str:
        raw_key = KEY_PREFIX + secrets.token_hex(32)
        hashed = _hash_key(raw_key)
        await self.redis.hset(
            f"{REDIS_KEY_PREFIX}{hashed}",
            mapping={
                "owner": owner,
                "tier": tier,
                "active": "1",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return raw_key

    async def validate_key(self, api_key: str) -> Optional[dict]:
        if not api_key or not api_key.startswith(KEY_PREFIX):
            return None
        hashed = _hash_key(api_key)
        data = await self.redis.hgetall(f"{REDIS_KEY_PREFIX}{hashed}")
        if not data:
            return None
        decoded = _decode_hash(data)
        if decoded.get("active") != "1":
            return None
        return decoded

    async def revoke_key(self, api_key: str) -> bool:
        hashed = _hash_key(api_key)
        return await self.redis.hset(f"{REDIS_KEY_PREFIX}{hashed}", "active", "0") >= 0

    async def has_active_keys(self, tier: Optional[str] = None) -> bool:
        async for redis_key in self.redis.scan_iter(f"{REDIS_KEY_PREFIX}*"):
            data = await self.redis.hgetall(redis_key)
            if not data:
                continue
            decoded = _decode_hash(data)
            if decoded.get("active") != "1":
                continue
            if tier and decoded.get("tier") != tier:
                continue
            return True
        return False

    async def check_rate_limit(self, api_key: str, tier: str) -> bool:
        hashed = _hash_key(api_key)
        rl_key = f"ratelimit:{hashed}"
        count = await self.redis.incr(rl_key)
        if count == 1:
            await self.redis.expire(rl_key, 60)
        max_rpm = TIERS.get(tier, TIERS["free"])["rpm"]
        return count <= max_rpm
