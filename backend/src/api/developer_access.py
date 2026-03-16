"""Public developer access-request API."""

from __future__ import annotations

import hashlib
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.core.settings import get_settings
from src.db import get_database_manager
from src.services.developer_access import developer_access_service


router = APIRouter(prefix="/api/developer-access", tags=["developer-access"])
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

AllowedSurface = Literal["api", "cli", "python_sdk", "typescript_sdk", "mcp"]
AccessLevel = Literal["read", "write", "custom"]


class DeveloperAccessRequestCreate(BaseModel):
    requester_name: str = Field(..., min_length=2, max_length=255)
    requester_email: str = Field(..., min_length=5, max_length=320)
    organization: str | None = Field(default=None, max_length=255)
    use_case: str = Field(..., min_length=20, max_length=5000)
    requested_surfaces: list[AllowedSurface] = Field(..., min_length=1)
    requested_access_level: AccessLevel = "read"
    requested_ips: list[str] = Field(default_factory=list, max_length=20)
    expected_rpm: int | None = Field(default=None, ge=1, le=100000)
    turnstile_token: str | None = Field(default=None, max_length=4096)
    website: str | None = Field(default=None, max_length=255)


class DeveloperAccessConfigResponse(BaseModel):
    turnstile_site_key: str | None = None
    turnstile_required: bool = False


def _turnstile_enabled() -> bool:
    settings = get_settings()
    return bool(settings.turnstile_site_key and settings.turnstile_secret_key)


def _developer_access_email_key(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()


async def _verify_turnstile_token(token: str, request_ip: str | None) -> None:
    settings = get_settings()
    if not settings.turnstile_secret_key:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data={
                    "secret": settings.turnstile_secret_key,
                    "response": token,
                    "remoteip": request_ip or "",
                },
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Bot verification unavailable") from exc

    payload = response.json()
    if not payload.get("success"):
        raise HTTPException(status_code=400, detail="Bot verification failed")


async def _developer_access_cooldown_active(
    request: Request,
    *,
    requester_email: str,
    request_ip: str | None,
) -> bool:
    redis_rl = getattr(request.app.state, "redis_rate_limit", None)
    cooldown_seconds = get_settings().developer_access_cooldown_seconds
    if redis_rl is None or cooldown_seconds <= 0:
        return False

    keys = [
        f"developer_access:cooldown:email:{_developer_access_email_key(requester_email)}",
    ]
    if request_ip:
        keys.append(f"developer_access:cooldown:ip:{request_ip}")

    try:
        for key in keys:
            if await redis_rl.exists(key):
                return True
    except Exception:
        return False
    return False


async def _set_developer_access_cooldown(
    request: Request,
    *,
    requester_email: str,
    request_ip: str | None,
) -> None:
    redis_rl = getattr(request.app.state, "redis_rate_limit", None)
    cooldown_seconds = get_settings().developer_access_cooldown_seconds
    if redis_rl is None or cooldown_seconds <= 0:
        return

    keys = [
        f"developer_access:cooldown:email:{_developer_access_email_key(requester_email)}",
    ]
    if request_ip:
        keys.append(f"developer_access:cooldown:ip:{request_ip}")

    try:
        for key in keys:
            await redis_rl.setex(key, cooldown_seconds, "1")
    except Exception:
        return


@router.get("/config", response_model=DeveloperAccessConfigResponse)
async def get_developer_access_config():
    settings = get_settings()
    enabled = _turnstile_enabled()
    return DeveloperAccessConfigResponse(
        turnstile_site_key=settings.turnstile_site_key if enabled else None,
        turnstile_required=enabled,
    )


class DeveloperAccessRequestResponse(BaseModel):
    id: str
    status: str
    requester_name: str
    requester_email: str
    requested_access_level: str
    requested_surfaces: list[str]
    requested_ips: list[str]
    expected_rpm: int | None = None
    created_at: str
    message: str


@router.post("/requests", response_model=DeveloperAccessRequestResponse, status_code=201)
async def create_developer_access_request(
    body: DeveloperAccessRequestCreate,
    request: Request,
):
    requester_email = body.requester_email.strip().lower()
    request_ip = getattr(request.state, "client_ip", None)

    if body.website and body.website.strip():
        raise HTTPException(status_code=400, detail="Request rejected")

    if _turnstile_enabled():
        if not body.turnstile_token or not body.turnstile_token.strip():
            raise HTTPException(status_code=400, detail="Bot verification required")
        await _verify_turnstile_token(body.turnstile_token.strip(), request_ip)

    if await _developer_access_cooldown_active(
        request,
        requester_email=requester_email,
        request_ip=request_ip,
    ):
        raise HTTPException(
            status_code=429,
            detail="A recent developer access request was already submitted. Please wait before retrying.",
        )

    manager = get_database_manager()
    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Developer access service unavailable",
        )

    async with manager.session() as session:
        record = await developer_access_service.create_request(
            session,
            requester_name=body.requester_name.strip(),
            requester_email=requester_email,
            organization=body.organization.strip() if body.organization else None,
            use_case=body.use_case.strip(),
            requested_surfaces=list(body.requested_surfaces),
            requested_access_level=body.requested_access_level,
            requested_ips=[item.strip() for item in body.requested_ips if item.strip()],
            expected_rpm=body.expected_rpm,
            request_ip=request_ip,
        )

    await _set_developer_access_cooldown(
        request,
        requester_email=requester_email,
        request_ip=request_ip,
    )

    return DeveloperAccessRequestResponse(
        **{
            key: record[key]
            for key in (
                "id",
                "status",
                "requester_name",
                "requester_email",
                "requested_access_level",
                "requested_surfaces",
                "requested_ips",
                "expected_rpm",
                "created_at",
            )
        },
        message=(
            "Developer access request submitted. Approval is manual and the owner "
            "will review the requested access level and IP allowlist."
        ),
    )
