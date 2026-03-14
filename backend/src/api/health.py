"""
Health check endpoint for PureCortex API.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic health check for load balancers and monitoring."""
    return {
        "status": "ok",
        "version": "0.7.0",
    }
