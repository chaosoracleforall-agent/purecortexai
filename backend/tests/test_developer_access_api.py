from __future__ import annotations

import importlib
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_app(monkeypatch, *, keep_internal_admin_token: bool = False):
    monkeypatch.setenv("ENABLE_AGENTS", "0")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6399/0")
    monkeypatch.delenv("PURECORTEX_DATABASE_URL", raising=False)
    if not keep_internal_admin_token:
        monkeypatch.delenv("PURECORTEX_INTERNAL_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("PURECORTEX_ADMIN_SECRET", raising=False)
    monkeypatch.delenv("PURECORTEX_BOOTSTRAP_TOKEN", raising=False)

    for module_name in [
        "main",
        "src.api.developer_access",
        "src.api.internal_admin",
        "src.core.settings",
        "src.db.session",
    ]:
        sys.modules.pop(module_name, None)

    main = importlib.import_module("main")
    return main.app


def test_public_access_request_fails_closed_without_database(monkeypatch):
    app = load_app(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/api/developer-access/requests",
            json={
                "requester_name": "Developer Example",
                "requester_email": "dev@example.com",
                "organization": "Example Org",
                "use_case": "We need read access for CLI and SDK based observability workflows.",
                "requested_surfaces": ["api", "cli"],
                "requested_access_level": "read",
                "requested_ips": ["203.0.113.10"],
                "expected_rpm": 120,
            },
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "Developer access service unavailable"


def test_internal_admin_surface_requires_internal_token(monkeypatch):
    app = load_app(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/internal/admin/health")
        assert response.status_code == 503
        assert response.json()["detail"] == "Internal admin token not configured"


def test_internal_admin_health_sets_no_store_headers(monkeypatch):
    monkeypatch.setenv("PURECORTEX_INTERNAL_ADMIN_TOKEN", "pytest-internal-token")
    monkeypatch.setenv("PURECORTEX_INTERNAL_ADMIN_ALLOWED_CIDRS", "")
    app = load_app(monkeypatch, keep_internal_admin_token=True)

    with TestClient(app) as client:
        response = client.get(
            "/internal/admin/health",
            headers={"X-Internal-Admin-Token": "pytest-internal-token"},
        )
        assert response.status_code == 200
        assert "no-store" in response.headers["cache-control"]
        assert response.headers["pragma"] == "no-cache"
        assert response.headers["expires"] == "0"


def test_public_access_request_rejects_honeypot_submission(monkeypatch):
    app = load_app(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/api/developer-access/requests",
            json={
                "requester_name": "Developer Example",
                "requester_email": "dev@example.com",
                "organization": "Example Org",
                "use_case": "We need read access for CLI and SDK based observability workflows.",
                "requested_surfaces": ["api", "cli"],
                "requested_access_level": "read",
                "requested_ips": ["203.0.113.10"],
                "expected_rpm": 120,
                "website": "https://spam.invalid",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Request rejected"


def test_public_access_request_requires_turnstile_when_enabled(monkeypatch):
    monkeypatch.setenv("PURECORTEX_TURNSTILE_SITE_KEY", "site-key")
    monkeypatch.setenv("PURECORTEX_TURNSTILE_SECRET_KEY", "secret-key")
    app = load_app(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/api/developer-access/requests",
            json={
                "requester_name": "Developer Example",
                "requester_email": "dev@example.com",
                "organization": "Example Org",
                "use_case": "We need read access for CLI and SDK based observability workflows.",
                "requested_surfaces": ["api", "cli"],
                "requested_access_level": "read",
                "requested_ips": ["203.0.113.10"],
                "expected_rpm": 120,
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Bot verification required"


def test_public_access_request_cooldown_blocks_repeat_submission(monkeypatch):
    app = load_app(monkeypatch)
    api = importlib.import_module("src.api.developer_access")

    class FakeRedis:
        def __init__(self):
            self._store: dict[str, str] = {}
            self._counts: dict[str, int] = {}

        async def incr(self, key: str):
            self._counts[key] = self._counts.get(key, 0) + 1
            return self._counts[key]

        async def expire(self, key: str, ttl: int):
            return True

        async def exists(self, key: str):
            return 1 if key in self._store else 0

        async def setex(self, key: str, ttl: int, value: str):
            self._store[key] = value
            return True

        async def aclose(self):
            return None

    class FakeManager:
        @asynccontextmanager
        async def session(self):
            yield object()

    async def fake_create_request(session, **kwargs):
        return {
            "id": "req-test",
            "status": "pending",
            "requester_name": kwargs["requester_name"],
            "requester_email": kwargs["requester_email"],
            "requested_access_level": kwargs["requested_access_level"],
            "requested_surfaces": kwargs["requested_surfaces"],
            "requested_ips": kwargs["requested_ips"],
            "expected_rpm": kwargs["expected_rpm"],
            "created_at": "2026-03-16T00:00:00+00:00",
        }

    monkeypatch.setattr(api, "get_database_manager", lambda: FakeManager())
    monkeypatch.setattr(api.developer_access_service, "create_request", fake_create_request)

    payload = {
        "requester_name": "Developer Example",
        "requester_email": "dev@example.com",
        "organization": "Example Org",
        "use_case": "We need read access for CLI and SDK based observability workflows.",
        "requested_surfaces": ["api", "cli"],
        "requested_access_level": "read",
        "requested_ips": ["203.0.113.10"],
        "expected_rpm": 120,
    }

    with TestClient(app) as client:
        app.state.redis_rate_limit = FakeRedis()
        first = client.post("/api/developer-access/requests", json=payload)
        assert first.status_code == 201

        second = client.post("/api/developer-access/requests", json=payload)
        assert second.status_code == 429
        assert "already submitted" in second.json()["detail"]
