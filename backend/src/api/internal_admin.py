"""Internal-only admin API surface for the owner control plane."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, Query

from src.core.settings import get_settings
from src.db import get_database_manager
from src.services.developer_access import developer_access_service


router = APIRouter(prefix="/internal/admin", tags=["internal-admin"])


def _require_internal_admin(x_internal_admin_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    expected = settings.internal_admin_token
    if not expected:
        raise HTTPException(status_code=503, detail="Internal admin token not configured")
    if not x_internal_admin_token or not hmac.compare_digest(x_internal_admin_token, expected):
        raise HTTPException(status_code=403, detail="Internal admin credentials required")


def _require_database():
    manager = get_database_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="Enterprise database not configured")
    return manager


@router.get("/health")
async def internal_admin_health(
    x_internal_admin_token: str | None = Header(default=None),
):
    """Readiness probe for the internal admin control plane."""
    _require_internal_admin(x_internal_admin_token)
    settings = get_settings()
    return {
        "status": "ok",
        "surface": "internal-admin",
        "owner_emails": list(settings.admin_allowed_emails),
        "database_configured": bool(
            settings.database_url or settings.cloud_sql_connection_name
        ),
        "oauth_configured": bool(
            settings.google_oauth_client_id
            and settings.google_oauth_client_secret
            and settings.oauth2_proxy_cookie_secret
        ),
        "ip_trust_configured": settings.trust_proxy_headers,
    }


@router.get("/access-requests")
async def list_access_requests(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(x_internal_admin_token)
    manager = _require_database()
    async with manager.session() as session:
        requests = await developer_access_service.list_requests(
            session,
            status=status,
            limit=limit,
        )
    return {"total": len(requests), "requests": requests}


@router.get("/access-requests/{request_id}")
async def get_access_request(
    request_id: str,
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(x_internal_admin_token)
    manager = _require_database()
    async with manager.session() as session:
        record = await developer_access_service.get_request(session, request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Developer access request not found")
    return record


@router.get("/api-keys")
async def list_api_keys(
    limit: int = Query(default=50, ge=1, le=200),
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(x_internal_admin_token)
    manager = _require_database()
    async with manager.session() as session:
        keys = await developer_access_service.list_api_keys(session, limit=limit)
    return {"total": len(keys), "api_keys": keys}
