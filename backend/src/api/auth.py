"""Authentication middleware for PURECORTEX API."""
from ipaddress import ip_address, ip_network
import logging
import re
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.settings import get_settings
from src.db import get_database_manager
from src.services.developer_access import developer_access_service
from src.services.request_ip import resolve_client_ip

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
    "/api/developer-access",
    "/internal/admin",
)

# GET endpoints that are explicitly public (PEN-019: no blanket GET passthrough)
PUBLIC_GET_PREFIXES = (
    "/api/governance/constitution",
    "/api/governance/overview",
    "/api/governance/proposals",
    "/api/staking/",
    "/api/agents/registry",
    "/api/agents/senator/activity",
    "/api/agents/curator/activity",
    "/api/agents/social/activity",
)

PUBLIC_POST_PATTERNS = (
    re.compile(r"^/api/governance/proposals/\d+/vote-signed$"),
)


def _ip_allowed(
    request_ip: str | None,
    allowlists: list[dict] | None,
    *,
    override_no_ip_allowlist: bool,
) -> bool:
    if override_no_ip_allowlist or not allowlists:
        return True
    if not request_ip:
        return False
    try:
        parsed_ip = ip_address(request_ip)
    except ValueError:
        return False
    for entry in allowlists:
        cidr = entry.get("cidr")
        if not cidr:
            continue
        try:
            if parsed_ip in ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        api_key_manager = getattr(request.app.state, "api_key_manager", None)
        settings = get_settings()

        request.state.client_ip = resolve_client_ip(
            request.headers,
            request.client.host if request.client else None,
            trust_proxy_headers=settings.trust_proxy_headers,
            trusted_proxy_cidrs=settings.trusted_proxy_cidrs,
        )

        # Allow public paths (any method)
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # Allow specific public GET endpoints
        if request.method == "GET" and any(path.startswith(p) for p in PUBLIC_GET_PREFIXES):
            return await call_next(request)

        if request.method == "POST" and any(pattern.match(path) for pattern in PUBLIC_POST_PATTERNS):
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
        db_key_id: str | None = None
        if not key_data:
            db_manager = get_database_manager()
            if db_manager and settings.key_hmac_secret:
                async with db_manager.session() as session:
                    key_data = await developer_access_service.validate_api_key(
                        session,
                        api_key,
                        key_hmac_secret=settings.key_hmac_secret,
                    )
                    if key_data:
                        db_key_id = key_data["key_id"]
        if not key_data:
            return JSONResponse(status_code=401, content={"detail": "Invalid or revoked API key"})

        if not _ip_allowed(
            getattr(request.state, "client_ip", None),
            key_data.get("ip_allowlists"),
            override_no_ip_allowlist=bool(key_data.get("override_no_ip_allowlist")),
        ):
            return JSONResponse(status_code=403, content={"detail": "Request IP is not allowed for this API key"})

        # Rate limit check
        tier = key_data.get("tier") or key_data.get("runtime_tier") or "free"
        within_limit = await api_key_manager.check_rate_limit(api_key, tier)
        if not within_limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        if db_key_id:
            db_manager = get_database_manager()
            if db_manager:
                async with db_manager.session() as session:
                    await developer_access_service.record_api_key_use(
                        session,
                        key_id=db_key_id,
                        request_ip=request.state.client_ip,
                    )

        # Attach key data to request state
        request.state.api_key_data = key_data
        return await call_next(request)
