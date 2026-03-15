"""Authentication middleware for PURECORTEX API."""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("purecortex.auth")

# Public paths that don't require authentication (any method)
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/admin/bootstrap",
}

# Public prefixes that don't require authentication (any method)
PUBLIC_PREFIXES = (
    "/api/transparency",
    "/api/governance/onchain",
)

# GET endpoints that are explicitly public (PEN-019: no blanket GET passthrough)
PUBLIC_GET_PREFIXES = (
    "/api/governance/constitution",
    "/api/governance/overview",
    "/api/governance/proposals",
    "/api/agents/registry",
    "/api/agents/senator/activity",
    "/api/agents/curator/reviews",
)


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        api_key_manager = getattr(request.app.state, "api_key_manager", None)

        # Allow public paths (any method)
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # Allow specific public GET endpoints
        if request.method == "GET" and any(path.startswith(p) for p in PUBLIC_GET_PREFIXES):
            return await call_next(request)

        # Allow OPTIONS for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Allow WebSocket upgrade (auth handled separately)
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # If auth is unavailable, fail closed for every protected route.
        if api_key_manager is None:
            return JSONResponse(
                status_code=503,
                content={"detail": "Authentication service unavailable"},
            )

        # Require API key for all other requests
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(status_code=401, content={"detail": "API key required"})

        key_data = await api_key_manager.validate_key(api_key)
        if not key_data:
            return JSONResponse(status_code=401, content={"detail": "Invalid or revoked API key"})

        # Rate limit check
        tier = key_data.get("tier", "free")
        within_limit = await api_key_manager.check_rate_limit(api_key, tier)
        if not within_limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        # Attach key data to request state
        request.state.api_key_data = key_data
        return await call_next(request)
