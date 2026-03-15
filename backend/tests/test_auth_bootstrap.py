from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import redis.asyncio as redis
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def reset_redis(url: str) -> None:
    async def _reset() -> None:
        client = redis.from_url(url, decode_responses=True)
        await client.flushdb()
        await client.aclose()

    asyncio.run(_reset())


def load_app(monkeypatch, *, redis_url: str, bootstrap_token: str | None = None):
    monkeypatch.setenv("ENABLE_AGENTS", "0")
    monkeypatch.setenv("REDIS_URL", redis_url)
    if bootstrap_token is not None:
        monkeypatch.setenv("PURECORTEX_BOOTSTRAP_TOKEN", bootstrap_token)
    else:
        monkeypatch.delenv("PURECORTEX_BOOTSTRAP_TOKEN", raising=False)
    monkeypatch.delenv("PURECORTEX_ADMIN_SECRET", raising=False)

    for module_name in ["main", "src.api.admin"]:
        sys.modules.pop(module_name, None)

    main = importlib.import_module("main")
    return main.app


def test_bootstrap_creates_first_admin_key(monkeypatch):
    redis_url = "redis://localhost:6379/14"
    reset_redis(redis_url)
    app = load_app(monkeypatch, redis_url=redis_url, bootstrap_token="pytest-bootstrap")

    with TestClient(app) as client:
        bootstrap = client.post(
            "/api/admin/bootstrap",
            headers={"X-Bootstrap-Token": "pytest-bootstrap"},
            json={"owner": "pytest-admin"},
        )
        assert bootstrap.status_code == 201
        payload = bootstrap.json()
        assert payload["owner"] == "pytest-admin"
        assert payload["tier"] == "admin"
        assert payload["api_key"].startswith("ctx_")

        admin_key = payload["api_key"]
        child_key = client.post(
            "/api/admin/keys",
            headers={"X-API-Key": admin_key},
            json={"owner": "child-user", "tier": "free"},
        )
        assert child_key.status_code == 200
        assert child_key.json()["tier"] == "free"

        repeat_bootstrap = client.post(
            "/api/admin/bootstrap",
            headers={"X-Bootstrap-Token": "pytest-bootstrap"},
            json={"owner": "pytest-admin-2"},
        )
        assert repeat_bootstrap.status_code == 409


def test_protected_routes_fail_closed_when_auth_is_unavailable(monkeypatch):
    app = load_app(monkeypatch, redis_url="redis://127.0.0.1:6399/0")

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200

        proposals = client.get("/api/governance/proposals")
        assert proposals.status_code == 200

        protected = client.post("/api/chat/session")
        assert protected.status_code == 503
        assert protected.json()["detail"] == "Authentication service unavailable"
