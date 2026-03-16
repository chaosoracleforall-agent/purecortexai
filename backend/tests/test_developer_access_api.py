from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_app(monkeypatch, *, keep_internal_admin_token: bool = False):
    monkeypatch.setenv("ENABLE_AGENTS", "0")
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
