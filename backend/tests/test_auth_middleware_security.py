from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from src.api.auth import APIKeyMiddleware


class _FakeAPIKeyManager:
    def __init__(self, *, key_data=None, within_limit: bool = True):
        self._key_data = key_data
        self._within_limit = within_limit

    async def validate_key(self, _api_key: str):
        return self._key_data

    async def check_rate_limit(self, _api_key: str, _tier: str):
        return self._within_limit


def _build_test_app(api_key_manager) -> FastAPI:
    app = FastAPI()
    app.add_middleware(APIKeyMiddleware)
    app.state.api_key_manager = api_key_manager

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/protected")
    async def protected():
        return {"ok": True}

    @app.get("/protected")
    async def protected_get():
        return {"ok": True}

    @app.exception_handler(Exception)
    async def _handler(_, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    return app


def test_protected_route_requires_api_key():
    app = _build_test_app(_FakeAPIKeyManager(key_data={"tier": "free"}))
    with TestClient(app) as client:
        resp = client.post("/protected")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "API key required"


def test_protected_route_fails_closed_when_auth_unavailable():
    app = _build_test_app(None)
    with TestClient(app) as client:
        resp = client.post("/protected")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Authentication service unavailable"


def test_invalid_api_key_rejected():
    app = _build_test_app(_FakeAPIKeyManager(key_data=None))
    with TestClient(app) as client:
        resp = client.post("/protected", headers={"X-API-Key": "ctx_bad"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid or revoked API key"


def test_ip_allowlist_enforced():
    app = _build_test_app(
        _FakeAPIKeyManager(
            key_data={
                "tier": "free",
                "ip_allowlists": [{"cidr": "10.0.0.0/8"}],
                "override_no_ip_allowlist": False,
            },
        )
    )
    with TestClient(app) as client:
        resp = client.post("/protected", headers={"X-API-Key": "ctx_ok"})
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Request IP is not allowed for this API key"


def test_rate_limit_enforced():
    app = _build_test_app(
        _FakeAPIKeyManager(
            key_data={"tier": "free", "override_no_ip_allowlist": True},
            within_limit=False,
        )
    )
    with TestClient(app) as client:
        resp = client.post("/protected", headers={"X-API-Key": "ctx_ok"})
        assert resp.status_code == 429
        assert resp.json()["detail"] == "Rate limit exceeded"


def test_public_health_path_is_always_accessible():
    app = _build_test_app(None)
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
