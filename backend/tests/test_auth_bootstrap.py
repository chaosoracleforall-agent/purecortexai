from __future__ import annotations

import asyncio
import importlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import redis.asyncio as redis
from algosdk import account
from algosdk.util import sign_bytes
from fastapi.testclient import TestClient

from src.services.governance_voting import build_signed_vote_message


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


def test_governance_writes_require_admin_or_scoped_key(monkeypatch):
    redis_url = "redis://localhost:6379/13"
    reset_redis(redis_url)
    app = load_app(monkeypatch, redis_url=redis_url, bootstrap_token="pytest-bootstrap")

    with TestClient(app) as client:
        bootstrap = client.post(
            "/api/admin/bootstrap",
            headers={"X-Bootstrap-Token": "pytest-bootstrap"},
            json={"owner": "pytest-admin"},
        )
        assert bootstrap.status_code == 201
        admin_key = bootstrap.json()["api_key"]

        free_key_response = client.post(
            "/api/admin/keys",
            headers={"X-API-Key": admin_key},
            json={"owner": "reader-user", "tier": "free"},
        )
        assert free_key_response.status_code == 200
        free_key = free_key_response.json()["api_key"]

        denied_create = client.post(
            "/api/governance/proposals",
            headers={"X-API-Key": free_key},
            json={
                "title": "Unauthorized smoke-test path",
                "description": "Read-only keys must not be able to create governance proposals.",
                "type": "general",
                "proposer": "reader-user",
            },
        )
        assert denied_create.status_code == 403
        assert denied_create.json()["detail"] == "API key lacks governance.write scope"

        proposal = client.post(
            "/api/governance/proposals",
            headers={"X-API-Key": admin_key},
            json={
                "title": "Authorize smoke-test path",
                "description": "Ensure internal governance voting remains restricted.",
                "type": "general",
                "proposer": "pytest-admin",
            },
        )
        assert proposal.status_code == 201
        proposal_id = proposal.json()["id"]

        denied_review = client.post(
            f"/api/governance/proposals/{proposal_id}/review",
            headers={"X-API-Key": free_key},
            json={
                "compliant": True,
                "analysis": "Read-only keys must not be able to review proposals.",
                "recommendation": "Approve for voting",
                "curator_name": "reader-user",
            },
        )
        assert denied_review.status_code == 403
        assert denied_review.json()["detail"] == "API key lacks governance.write scope"

        review = client.post(
            f"/api/governance/proposals/{proposal_id}/review",
            headers={"X-API-Key": admin_key},
            json={
                "compliant": True,
                "analysis": "Looks good for controlled testing.",
                "recommendation": "Approve for voting",
                "curator_name": "pytest-curator",
            },
        )
        assert review.status_code == 200

        denied_vote = client.post(
            f"/api/governance/proposals/{proposal_id}/vote",
            headers={"X-API-Key": free_key},
            json={"voter": "reader-user", "vote": "for", "weight": 1},
        )
        assert denied_vote.status_code == 403
        assert denied_vote.json()["detail"] == "API key lacks governance.write scope"

        admin_vote = client.post(
            f"/api/governance/proposals/{proposal_id}/vote",
            headers={"X-API-Key": admin_key},
            json={"voter": "pytest-admin", "vote": "for", "weight": 1},
        )
        assert admin_vote.status_code == 200
        assert admin_vote.json()["auth_method"] == "api_key"


def test_signed_governance_vote_path_records_live_weight(monkeypatch):
    redis_url = "redis://localhost:6379/12"
    reset_redis(redis_url)
    app = load_app(monkeypatch, redis_url=redis_url, bootstrap_token="pytest-bootstrap")

    class FakeAlgorandService:
        async def list_stake_snapshots(self):
            return [
                {
                    "address": voter,
                    "ve_power": 2_500_000,
                    "delegate": None,
                }
            ]

    private_key, voter = account.generate_account()

    governance = importlib.import_module("src.api.governance")
    monkeypatch.setattr(governance, "get_algorand_service", lambda: FakeAlgorandService())

    with TestClient(app) as client:
        bootstrap = client.post(
            "/api/admin/bootstrap",
            headers={"X-Bootstrap-Token": "pytest-bootstrap"},
            json={"owner": "pytest-admin"},
        )
        assert bootstrap.status_code == 201
        admin_key = bootstrap.json()["api_key"]

        proposal = client.post(
            "/api/governance/proposals",
            headers={"X-API-Key": admin_key},
            json={
                "title": "Signed voting regression",
                "description": "Exercise the signed wallet voting path end-to-end.",
                "type": "general",
                "proposer": "pytest-admin",
            },
        )
        assert proposal.status_code == 201
        proposal_id = proposal.json()["id"]

        review = client.post(
            f"/api/governance/proposals/{proposal_id}/review",
            headers={"X-API-Key": admin_key},
            json={
                "compliant": True,
                "analysis": "Ready for signed voting validation.",
                "recommendation": "Approve",
                "curator_name": "pytest-curator",
            },
        )
        assert review.status_code == 200

        power = client.get(f"/api/governance/proposals/{proposal_id}/power/{voter}")
        assert power.status_code == 200
        assert power.json()["effective_weight"] == 2_500_000

        issued_at = datetime.now(timezone.utc).isoformat()
        nonce = "signed-vote-regression"
        signature = sign_bytes(
            build_signed_vote_message(
                proposal_id=proposal_id,
                voter=voter,
                vote="for",
                issued_at=issued_at,
                nonce=nonce,
            ).encode("utf-8"),
            private_key,
        )

        vote = client.post(
            f"/api/governance/proposals/{proposal_id}/vote-signed",
            json={
                "voter": voter,
                "vote": "for",
                "issued_at": issued_at,
                "nonce": nonce,
                "signature": signature,
            },
        )
        assert vote.status_code == 200
        payload = vote.json()
        assert payload["auth_method"] == "wallet_signature"
        assert payload["weight"] == 2_500_000
        assert payload["direct_weight"] == 2_500_000
        assert payload["delegated_weight"] == 0
        assert payload["votes_for"] == 2_500_000
        assert payload["votes_against"] == 0

        proposal_detail = client.get(f"/api/governance/proposals/{proposal_id}")
        assert proposal_detail.status_code == 200
        assert proposal_detail.json()["votes_for"] == 2_500_000
        assert proposal_detail.json()["votes_against"] == 0
        assert voter in proposal_detail.json()["voters"]
