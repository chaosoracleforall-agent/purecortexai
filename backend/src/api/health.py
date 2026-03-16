"""
Health check endpoint for PURECORTEX API.
"""

import logging

from fastapi import APIRouter

from src import APP_VERSION
from src.services.cache import get_cache_service

router = APIRouter(tags=["health"])
logger = logging.getLogger("purecortex.health")


@router.get("/health")
async def health():
    """Health check with dependency status for load balancers and monitoring."""
    cache = get_cache_service()
    redis_ok = False
    if cache.available:
        try:
            redis_ok = await cache.ping()
        except Exception:
            redis_ok = False

    # Import here to avoid circular import at module level
    from main import get_agent_loop, orchestrator

    agent_loop = get_agent_loop()

    status = "ok" if redis_ok else "degraded"

    return {
        "status": status,
        "version": APP_VERSION,
        "dependencies": {
            "redis": "connected" if redis_ok else "unavailable",
            "orchestrator": "initialized" if orchestrator else "unavailable",
            "agent_loop": "running" if agent_loop else "stopped",
        },
    }
