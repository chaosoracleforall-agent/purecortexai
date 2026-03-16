"""Internal-only admin API surface for the owner control plane."""

from __future__ import annotations

import hmac
from ipaddress import ip_address, ip_network

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from src.core.settings import get_settings
from src.db import get_database_manager
from src.services.developer_access import developer_access_service


router = APIRouter(prefix="/internal/admin", tags=["internal-admin"])


def _set_no_store_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, private, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


def _internal_admin_ip_allowed(request: Request) -> bool:
    settings = get_settings()
    client_ip = getattr(request.state, "client_ip", None)
    if not settings.internal_admin_allowed_cidrs:
        return True
    if not client_ip:
        return False
    try:
        parsed_ip = ip_address(client_ip)
    except ValueError:
        return False
    for cidr in settings.internal_admin_allowed_cidrs:
        try:
            if parsed_ip in ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _require_internal_admin(
    request: Request,
    x_internal_admin_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    expected = settings.internal_admin_token
    if not expected:
        raise HTTPException(status_code=503, detail="Internal admin token not configured")
    if not x_internal_admin_token or not hmac.compare_digest(x_internal_admin_token, expected):
        raise HTTPException(status_code=403, detail="Internal admin credentials required")
    if not _internal_admin_ip_allowed(request):
        raise HTTPException(status_code=403, detail="Internal admin access is not allowed from this IP")


def _require_database():
    manager = get_database_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="Enterprise database not configured")
    return manager


class IPAllowlistEntry(BaseModel):
    cidr: str = Field(..., min_length=3, max_length=64)
    label: str | None = Field(default=None, max_length=255)


class ApproveAccessRequest(BaseModel):
    actor_email: str = Field(..., min_length=3, max_length=320)
    review_notes: str | None = Field(default=None, max_length=5000)
    label: str | None = Field(default=None, max_length=255)
    access_level: str | None = Field(default=None, max_length=32)
    scopes: list[str] | None = None
    intended_surfaces: list[str] | None = None
    rate_limit_profile: str | None = Field(default=None, max_length=64)
    ip_allowlists: list[IPAllowlistEntry] | None = None
    override_no_ip_allowlist: bool = False
    override_reason: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=5000)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


class RejectAccessRequest(BaseModel):
    actor_email: str = Field(..., min_length=3, max_length=320)
    review_notes: str = Field(..., min_length=3, max_length=5000)


class UpdateAPIKeyRequest(BaseModel):
    actor_email: str = Field(..., min_length=3, max_length=320)
    label: str | None = Field(default=None, max_length=255)
    access_level: str | None = Field(default=None, max_length=32)
    scopes: list[str] | None = None
    intended_surfaces: list[str] | None = None
    rate_limit_profile: str | None = Field(default=None, max_length=64)
    ip_allowlists: list[IPAllowlistEntry] | None = None
    override_no_ip_allowlist: bool | None = None
    override_reason: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=5000)
    expires_in_days: int | None = Field(default=None, ge=0, le=3650)


class RevokeAPIKeyRequest(BaseModel):
    actor_email: str = Field(..., min_length=3, max_length=320)
    reason: str = Field(..., min_length=3, max_length=2000)


class RotateAPIKeyRequest(BaseModel):
    actor_email: str = Field(..., min_length=3, max_length=320)
    reason: str = Field(..., min_length=3, max_length=2000)


@router.get("/health")
async def internal_admin_health(
    request: Request,
    response: Response,
    x_internal_admin_token: str | None = Header(default=None),
):
    """Readiness probe for the internal admin control plane."""
    _require_internal_admin(request, x_internal_admin_token)
    _set_no_store_headers(response)
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
    request: Request,
    response: Response,
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(request, x_internal_admin_token)
    _set_no_store_headers(response)
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
    request: Request,
    response: Response,
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(request, x_internal_admin_token)
    _set_no_store_headers(response)
    manager = _require_database()
    async with manager.session() as session:
        record = await developer_access_service.get_request(session, request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Developer access request not found")
    return record


@router.get("/api-keys")
async def list_api_keys(
    request: Request,
    response: Response,
    limit: int = Query(default=50, ge=1, le=200),
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(request, x_internal_admin_token)
    _set_no_store_headers(response)
    manager = _require_database()
    async with manager.session() as session:
        keys = await developer_access_service.list_api_keys(session, limit=limit)
    return {"total": len(keys), "api_keys": keys}


@router.post("/access-requests/{request_id}/approve")
async def approve_access_request(
    request_id: str,
    body: ApproveAccessRequest,
    request: Request,
    response: Response,
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(request, x_internal_admin_token)
    _set_no_store_headers(response)
    manager = _require_database()
    settings = get_settings()
    if not settings.key_hmac_secret:
        raise HTTPException(status_code=503, detail="Key HMAC secret not configured")

    try:
        async with manager.session() as session:
            request_payload, api_key_payload, raw_key = await developer_access_service.approve_request_and_issue_key(
                session,
                request_id=request_id,
                reviewed_by=body.actor_email,
                key_hmac_secret=settings.key_hmac_secret,
                review_notes=body.review_notes,
                label=body.label,
                access_level=body.access_level,
                scopes=body.scopes,
                intended_surfaces=body.intended_surfaces,
                rate_limit_profile=body.rate_limit_profile,
                ip_allowlists=[entry.model_dump() for entry in body.ip_allowlists] if body.ip_allowlists is not None else None,
                override_no_ip_allowlist=body.override_no_ip_allowlist,
                override_reason=body.override_reason,
                notes=body.notes,
                expires_in_days=body.expires_in_days,
                request_ip=getattr(request.state, "client_ip", None),
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"request": request_payload, "api_key": api_key_payload, "secret": raw_key}


@router.post("/access-requests/{request_id}/reject")
async def reject_access_request(
    request_id: str,
    body: RejectAccessRequest,
    request: Request,
    response: Response,
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(request, x_internal_admin_token)
    _set_no_store_headers(response)
    manager = _require_database()
    try:
        async with manager.session() as session:
            record = await developer_access_service.reject_request(
                session,
                request_id=request_id,
                reviewed_by=body.actor_email,
                review_notes=body.review_notes,
                request_ip=getattr(request.state, "client_ip", None),
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"request": record}


@router.patch("/api-keys/{key_id}")
async def update_api_key(
    key_id: str,
    body: UpdateAPIKeyRequest,
    request: Request,
    response: Response,
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(request, x_internal_admin_token)
    _set_no_store_headers(response)
    manager = _require_database()
    try:
        async with manager.session() as session:
            record = await developer_access_service.update_api_key_policy(
                session,
                key_id=key_id,
                actor_email=body.actor_email,
                request_ip=getattr(request.state, "client_ip", None),
                label=body.label,
                access_level=body.access_level,
                scopes=body.scopes,
                intended_surfaces=body.intended_surfaces,
                rate_limit_profile=body.rate_limit_profile,
                ip_allowlists=[entry.model_dump() for entry in body.ip_allowlists] if body.ip_allowlists is not None else None,
                override_no_ip_allowlist=body.override_no_ip_allowlist,
                override_reason=body.override_reason,
                notes=body.notes,
                expires_in_days=body.expires_in_days,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"api_key": record}


@router.post("/api-keys/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    body: RevokeAPIKeyRequest,
    request: Request,
    response: Response,
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(request, x_internal_admin_token)
    _set_no_store_headers(response)
    manager = _require_database()
    try:
        async with manager.session() as session:
            record = await developer_access_service.revoke_api_key(
                session,
                key_id=key_id,
                actor_email=body.actor_email,
                reason=body.reason,
                request_ip=getattr(request.state, "client_ip", None),
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"api_key": record}


@router.post("/api-keys/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    body: RotateAPIKeyRequest,
    request: Request,
    response: Response,
    x_internal_admin_token: str | None = Header(default=None),
):
    _require_internal_admin(request, x_internal_admin_token)
    _set_no_store_headers(response)
    manager = _require_database()
    settings = get_settings()
    if not settings.key_hmac_secret:
        raise HTTPException(status_code=503, detail="Key HMAC secret not configured")

    try:
        async with manager.session() as session:
            record, raw_key = await developer_access_service.rotate_api_key(
                session,
                key_id=key_id,
                actor_email=body.actor_email,
                key_hmac_secret=settings.key_hmac_secret,
                reason=body.reason,
                request_ip=getattr(request.state, "client_ip", None),
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"api_key": record, "secret": raw_key}
