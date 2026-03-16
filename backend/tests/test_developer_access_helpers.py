from __future__ import annotations

from datetime import datetime, timezone

from src.models import APIKeyRecord
from src.services.developer_access import (
    _compute_secret_hash,
    _default_scopes,
    _generate_api_key,
    _key_to_dict,
    _normalize_cidr,
)


def test_normalize_cidr_adds_host_masks():
    assert _normalize_cidr("203.0.113.10") == "203.0.113.10/32"
    assert _normalize_cidr("2001:db8::10") == "2001:db8::10/128"


def test_default_scopes_expand_with_surface_and_access_level():
    assert _default_scopes("read", ["api", "cli"]) == ["agent.chat", "read.public"]
    assert _default_scopes("write", ["api", "mcp"]) == [
        "agent.chat",
        "governance.write",
        "mcp.read",
        "mcp.write",
        "read.public",
    ]


def test_generated_api_keys_include_embedded_key_id_and_hash():
    key_id, key_prefix, secret_hash, raw_key = _generate_api_key("pytest-secret")

    assert raw_key.startswith(f"{key_prefix}_")
    assert key_prefix.startswith("ctx_")
    assert key_id in raw_key
    assert secret_hash == _compute_secret_hash("pytest-secret", raw_key)


def test_database_key_payload_preserves_legacy_owner_and_tier_fields():
    record = APIKeyRecord(
        key_id="b7314aa7ff81a465",
        key_prefix="ctx_b7314aa7ff81a465",
        secret_hash="hash",
        label="Local Admin Smoke primary key",
        owner_name="Local Admin Smoke",
        owner_email="chaosoracleforall@gmail.com",
        status="active",
        access_level="custom",
        scopes=["agent.chat", "governance.write"],
        intended_surfaces=["api", "cli"],
        rate_limit_profile="write-default",
        created_at=datetime.now(timezone.utc),
        override_no_ip_allowlist=False,
    )

    payload = _key_to_dict(record)

    assert payload["owner"] == "Local Admin Smoke"
    assert payload["tier"] == "admin"
    assert payload["runtime_tier"] == "admin"
