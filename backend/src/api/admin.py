"""Admin endpoints for API key management."""
import hmac
import logging
import os

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

logger = logging.getLogger("purecortex.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_SECRET = os.getenv("PURECORTEX_ADMIN_SECRET", "")
BOOTSTRAP_TOKEN = os.getenv("PURECORTEX_BOOTSTRAP_TOKEN", "")


def _has_valid_secret(secret: str | None) -> bool:
    return bool(ADMIN_SECRET and secret and hmac.compare_digest(secret, ADMIN_SECRET))


def _require_admin(request: Request, x_admin_secret: str | None = None):
    api_key_data = getattr(request.state, "api_key_data", None)
    if api_key_data and api_key_data.get("tier") == "admin":
        return
    if _has_valid_secret(x_admin_secret):
        return
    raise HTTPException(status_code=403, detail="Admin credentials required")


class CreateKeyRequest(BaseModel):
    owner: str
    tier: str = "free"


class CreateKeyResponse(BaseModel):
    api_key: str
    owner: str
    tier: str


class BootstrapAdminRequest(BaseModel):
    owner: str = "bootstrap-admin"


class RevokeKeyRequest(BaseModel):
    api_key: str


# The router will be configured with the api_key_manager in main.py
_api_key_manager = None


def set_api_key_manager(manager):
    global _api_key_manager
    _api_key_manager = manager


@router.post("/bootstrap", response_model=CreateKeyResponse, status_code=201)
async def bootstrap_admin_key(
    req: BootstrapAdminRequest,
    x_bootstrap_token: str | None = Header(default=None),
):
    if _api_key_manager is None:
        raise HTTPException(status_code=503, detail="API key manager not initialized")
    if not BOOTSTRAP_TOKEN:
        raise HTTPException(status_code=503, detail="Bootstrap token not configured")
    if not x_bootstrap_token or not hmac.compare_digest(x_bootstrap_token, BOOTSTRAP_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid bootstrap token")
    if await _api_key_manager.has_active_keys(tier="admin"):
        raise HTTPException(status_code=409, detail="An active admin API key already exists")

    api_key = await _api_key_manager.create_key(req.owner, "admin")
    logger.warning("Bootstrapped first admin API key for owner=%s", req.owner)
    return CreateKeyResponse(api_key=api_key, owner=req.owner, tier="admin")


@router.post("/keys", response_model=CreateKeyResponse)
async def create_api_key(
    req: CreateKeyRequest,
    request: Request,
    x_admin_secret: str | None = Header(default=None),
):
    _require_admin(request, x_admin_secret)
    if _api_key_manager is None:
        raise HTTPException(status_code=503, detail="API key manager not initialized")
    api_key = await _api_key_manager.create_key(req.owner, req.tier)
    return CreateKeyResponse(api_key=api_key, owner=req.owner, tier=req.tier)


@router.post("/keys/revoke")
async def revoke_api_key(
    req: RevokeKeyRequest,
    request: Request,
    x_admin_secret: str | None = Header(default=None),
):
    _require_admin(request, x_admin_secret)
    if _api_key_manager is None:
        raise HTTPException(status_code=503, detail="API key manager not initialized")
    await _api_key_manager.revoke_key(req.api_key)
    return {"status": "revoked"}
