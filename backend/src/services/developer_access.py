"""Developer-access services backed by the managed database foundation."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, ip_network
from typing import Any

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import APIKeyIPAllowlist, APIKeyRecord, AuditEvent, DeveloperAccessRequest

KEY_PREFIX = "ctx"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_cidr(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("IP allowlist entries cannot be empty.")
    if "/" not in candidate:
        parsed = ip_address(candidate)
        candidate = f"{parsed}/{32 if parsed.version == 4 else 128}"
    return str(ip_network(candidate, strict=False))


def _default_rate_limit_profile(access_level: str) -> str:
    return {
        "read": "read-default",
        "write": "write-default",
        "custom": "custom-default",
    }.get(access_level, "read-default")


def _default_scopes(access_level: str, surfaces: list[str]) -> list[str]:
    scopes = {"read.public"}
    if any(surface in surfaces for surface in ("api", "cli", "python_sdk", "typescript_sdk")):
        scopes.add("agent.chat")
    if "mcp" in surfaces:
        scopes.add("mcp.read")
    if access_level in {"write", "custom"}:
        scopes.add("governance.write")
        if "mcp" in surfaces:
            scopes.add("mcp.write")
    return sorted(scopes)


def _runtime_tier(model: APIKeyRecord) -> str:
    if model.owner_email == "chaosoracleforall@gmail.com":
        return "admin"
    if model.access_level in {"write", "custom"}:
        return "paid"
    return "free"


def _compute_secret_hash(key_hmac_secret: str, raw_key: str) -> str:
    return hmac.new(
        key_hmac_secret.encode("utf-8"),
        raw_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _generate_api_key(key_hmac_secret: str) -> tuple[str, str, str, str]:
    key_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(32)
    raw_key = f"{KEY_PREFIX}_{key_id}_{secret}"
    key_prefix = f"{KEY_PREFIX}_{key_id}"
    return key_id, key_prefix, _compute_secret_hash(key_hmac_secret, raw_key), raw_key


def _request_to_dict(model: DeveloperAccessRequest) -> dict[str, Any]:
    return {
        "id": model.id,
        "requester_name": model.requester_name,
        "requester_email": model.requester_email,
        "organization": model.organization,
        "use_case": model.use_case,
        "requested_surfaces": model.requested_surfaces,
        "requested_access_level": model.requested_access_level,
        "requested_ips": model.requested_ips,
        "expected_rpm": model.expected_rpm,
        "status": model.status,
        "review_notes": model.review_notes,
        "created_at": model.created_at.isoformat(),
        "reviewed_at": model.reviewed_at.isoformat() if model.reviewed_at else None,
        "reviewed_by": model.reviewed_by,
        "issued_key_id": model.issued_key_id,
    }


def _key_to_dict(model: APIKeyRecord) -> dict[str, Any]:
    runtime_tier = _runtime_tier(model)
    return {
        "id": model.id,
        "key_id": model.key_id,
        "key_prefix": model.key_prefix,
        "owner": model.owner_name,
        "label": model.label,
        "owner_name": model.owner_name,
        "owner_email": model.owner_email,
        "status": model.status,
        "tier": runtime_tier,
        "access_level": model.access_level,
        "scopes": model.scopes,
        "intended_surfaces": model.intended_surfaces,
        "rate_limit_profile": model.rate_limit_profile,
        "expires_at": model.expires_at.isoformat() if model.expires_at else None,
        "created_at": model.created_at.isoformat(),
        "created_by": model.created_by,
        "revoked_at": model.revoked_at.isoformat() if model.revoked_at else None,
        "revoked_by": model.revoked_by,
        "last_used_at": model.last_used_at.isoformat() if model.last_used_at else None,
        "last_used_ip": model.last_used_ip,
        "override_no_ip_allowlist": model.override_no_ip_allowlist,
        "override_reason": model.override_reason,
        "request_id": model.request_id,
        "notes": model.notes,
        "runtime_tier": runtime_tier,
        "ip_allowlists": [
            {
                "id": entry.id,
                "cidr": entry.cidr,
                "label": entry.label,
                "created_at": entry.created_at.isoformat(),
                "created_by": entry.created_by,
            }
            for entry in model.ip_allowlists
        ],
    }


class DeveloperAccessService:
    async def _load_request_model(
        self,
        session: AsyncSession,
        request_id: str,
    ) -> DeveloperAccessRequest:
        statement = select(DeveloperAccessRequest).where(DeveloperAccessRequest.id == request_id)
        result = await session.execute(statement)
        record = result.scalar_one_or_none()
        if record is None:
            raise ValueError("Developer access request not found.")
        return record

    async def _load_api_key_model(
        self,
        session: AsyncSession,
        key_id: str,
    ) -> APIKeyRecord:
        statement = (
            select(APIKeyRecord)
            .options(selectinload(APIKeyRecord.ip_allowlists))
            .where(APIKeyRecord.key_id == key_id)
        )
        result = await session.execute(statement)
        record = result.scalar_one_or_none()
        if record is None:
            raise ValueError("API key not found.")
        return record

    async def create_request(
        self,
        session: AsyncSession,
        *,
        requester_name: str,
        requester_email: str,
        organization: str | None,
        use_case: str,
        requested_surfaces: list[str],
        requested_access_level: str,
        requested_ips: list[str],
        expected_rpm: int | None,
        request_ip: str | None,
    ) -> dict[str, Any]:
        record = DeveloperAccessRequest(
            requester_name=requester_name,
            requester_email=requester_email,
            organization=organization,
            use_case=use_case,
            requested_surfaces=requested_surfaces,
            requested_access_level=requested_access_level,
            requested_ips=requested_ips,
            expected_rpm=expected_rpm,
        )
        session.add(record)
        await session.flush()

        session.add(
            AuditEvent(
                actor_type="public-request",
                actor_email=requester_email,
                event_type="developer_access.request_created",
                target_type="developer_access_request",
                target_id=record.id,
                request_ip=request_ip,
                metadata_json={
                    "requested_access_level": requested_access_level,
                    "requested_surfaces": requested_surfaces,
                    "requested_ips": requested_ips,
                },
            )
        )
        await session.commit()
        await session.refresh(record)
        return _request_to_dict(record)

    async def list_requests(
        self,
        session: AsyncSession,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        statement: Select[tuple[DeveloperAccessRequest]] = select(DeveloperAccessRequest)
        if status:
            statement = statement.where(DeveloperAccessRequest.status == status)
        statement = statement.order_by(desc(DeveloperAccessRequest.created_at)).limit(limit)
        result = await session.execute(statement)
        return [_request_to_dict(item) for item in result.scalars().all()]

    async def get_request(
        self,
        session: AsyncSession,
        request_id: str,
    ) -> dict[str, Any] | None:
        statement = select(DeveloperAccessRequest).where(DeveloperAccessRequest.id == request_id)
        result = await session.execute(statement)
        item = result.scalar_one_or_none()
        return _request_to_dict(item) if item else None

    async def list_api_keys(
        self,
        session: AsyncSession,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        statement = (
            select(APIKeyRecord)
            .options(selectinload(APIKeyRecord.ip_allowlists))
            .order_by(desc(APIKeyRecord.created_at))
            .limit(limit)
        )
        result = await session.execute(statement)
        return [_key_to_dict(item) for item in result.scalars().unique().all()]

    async def reject_request(
        self,
        session: AsyncSession,
        *,
        request_id: str,
        reviewed_by: str,
        review_notes: str,
        request_ip: str | None,
    ) -> dict[str, Any]:
        record = await self._load_request_model(session, request_id)
        if record.status == "approved":
            raise ValueError("Approved requests cannot be rejected.")

        record.status = "rejected"
        record.review_notes = review_notes
        record.reviewed_by = reviewed_by
        record.reviewed_at = _utcnow()
        session.add(
            AuditEvent(
                actor_type="owner-admin",
                actor_email=reviewed_by,
                event_type="developer_access.request_rejected",
                target_type="developer_access_request",
                target_id=record.id,
                request_ip=request_ip,
                metadata_json={"review_notes": review_notes},
            )
        )
        await session.commit()
        await session.refresh(record)
        return _request_to_dict(record)

    async def approve_request_and_issue_key(
        self,
        session: AsyncSession,
        *,
        request_id: str,
        reviewed_by: str,
        key_hmac_secret: str,
        review_notes: str | None,
        label: str | None,
        access_level: str | None,
        scopes: list[str] | None,
        intended_surfaces: list[str] | None,
        rate_limit_profile: str | None,
        ip_allowlists: list[dict[str, str | None]] | None,
        override_no_ip_allowlist: bool,
        override_reason: str | None,
        notes: str | None,
        expires_in_days: int | None,
        request_ip: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        request_record = await self._load_request_model(session, request_id)
        if request_record.status == "approved" and request_record.issued_key_id:
            raise ValueError("This request already has an issued key.")

        normalized_surfaces = list(intended_surfaces or request_record.requested_surfaces)
        normalized_access = access_level or request_record.requested_access_level
        normalized_scopes = list(scopes or _default_scopes(normalized_access, normalized_surfaces))
        normalized_rate_limit = rate_limit_profile or _default_rate_limit_profile(normalized_access)
        normalized_ip_allowlists = [
            {
                "cidr": _normalize_cidr(entry["cidr"] or ""),
                "label": (entry.get("label") or "").strip() or None,
            }
            for entry in (
                ip_allowlists
                or [{"cidr": cidr, "label": None} for cidr in request_record.requested_ips]
            )
            if (entry.get("cidr") or "").strip()
        ]

        if (
            not override_no_ip_allowlist
            and normalized_access in {"write", "custom"}
            and not normalized_ip_allowlists
        ):
            raise ValueError(
                "Write-enabled keys require at least one IP allowlist entry or an explicit override."
            )

        key_id, key_prefix, secret_hash, raw_key = _generate_api_key(key_hmac_secret)
        expires_at = None
        if expires_in_days:
            expires_at = _utcnow() + timedelta(days=expires_in_days)

        api_key = APIKeyRecord(
            key_id=key_id,
            key_prefix=key_prefix,
            secret_hash=secret_hash,
            label=label or f"{request_record.requester_name} primary key",
            owner_name=request_record.requester_name,
            owner_email=request_record.requester_email,
            status="active",
            access_level=normalized_access,
            scopes=normalized_scopes,
            intended_surfaces=normalized_surfaces,
            rate_limit_profile=normalized_rate_limit,
            expires_at=expires_at,
            created_by=reviewed_by,
            override_no_ip_allowlist=override_no_ip_allowlist,
            override_reason=override_reason,
            request_id=request_record.id,
            notes=notes,
            ip_allowlists=[
                APIKeyIPAllowlist(
                    cidr=entry["cidr"],
                    label=entry["label"],
                    created_by=reviewed_by,
                )
                for entry in normalized_ip_allowlists
            ],
        )
        session.add(api_key)
        await session.flush()

        request_record.status = "approved"
        request_record.review_notes = review_notes
        request_record.reviewed_by = reviewed_by
        request_record.reviewed_at = _utcnow()
        request_record.issued_key_id = api_key.id

        session.add(
            AuditEvent(
                actor_type="owner-admin",
                actor_email=reviewed_by,
                event_type="developer_access.request_approved",
                target_type="developer_access_request",
                target_id=request_record.id,
                request_ip=request_ip,
                metadata_json={
                    "issued_key_id": api_key.key_id,
                    "access_level": normalized_access,
                    "surfaces": normalized_surfaces,
                    "scopes": normalized_scopes,
                },
            )
        )
        session.add(
            AuditEvent(
                actor_type="owner-admin",
                actor_email=reviewed_by,
                event_type="developer_access.api_key_issued",
                target_type="api_key",
                target_id=api_key.key_id,
                request_ip=request_ip,
                metadata_json={
                    "request_id": request_record.id,
                    "access_level": normalized_access,
                    "scopes": normalized_scopes,
                },
            )
        )
        await session.commit()

        refreshed_key = await self._load_api_key_model(session, key_id)
        refreshed_request = await self._load_request_model(session, request_id)
        return _request_to_dict(refreshed_request), _key_to_dict(refreshed_key), raw_key

    async def update_api_key_policy(
        self,
        session: AsyncSession,
        *,
        key_id: str,
        actor_email: str,
        request_ip: str | None,
        label: str | None = None,
        access_level: str | None = None,
        scopes: list[str] | None = None,
        intended_surfaces: list[str] | None = None,
        rate_limit_profile: str | None = None,
        ip_allowlists: list[dict[str, str | None]] | None = None,
        override_no_ip_allowlist: bool | None = None,
        override_reason: str | None = None,
        notes: str | None = None,
        expires_in_days: int | None = None,
    ) -> dict[str, Any]:
        record = await self._load_api_key_model(session, key_id)
        if record.status != "active":
            raise ValueError("Only active keys can be updated.")

        if label is not None:
            record.label = label
        if access_level is not None:
            record.access_level = access_level
        if scopes is not None:
            record.scopes = list(scopes)
        if intended_surfaces is not None:
            record.intended_surfaces = list(intended_surfaces)
        if rate_limit_profile is not None:
            record.rate_limit_profile = rate_limit_profile
        if notes is not None:
            record.notes = notes
        if override_no_ip_allowlist is not None:
            record.override_no_ip_allowlist = override_no_ip_allowlist
        if override_reason is not None:
            record.override_reason = override_reason
        if expires_in_days is not None:
            record.expires_at = _utcnow() + timedelta(days=expires_in_days) if expires_in_days > 0 else None

        if ip_allowlists is not None:
            normalized = [
                {
                    "cidr": _normalize_cidr(entry["cidr"] or ""),
                    "label": (entry.get("label") or "").strip() or None,
                }
                for entry in ip_allowlists
                if (entry.get("cidr") or "").strip()
            ]
            if not record.override_no_ip_allowlist and record.access_level in {"write", "custom"} and not normalized:
                raise ValueError(
                    "Write-enabled keys require at least one IP allowlist entry or an explicit override."
                )
            record.ip_allowlists.clear()
            record.ip_allowlists.extend(
                APIKeyIPAllowlist(
                    cidr=entry["cidr"],
                    label=entry["label"],
                    created_by=actor_email,
                )
                for entry in normalized
            )

        session.add(
            AuditEvent(
                actor_type="owner-admin",
                actor_email=actor_email,
                event_type="developer_access.api_key_updated",
                target_type="api_key",
                target_id=record.key_id,
                request_ip=request_ip,
                metadata_json={
                    "access_level": record.access_level,
                    "scopes": record.scopes,
                    "intended_surfaces": record.intended_surfaces,
                    "override_no_ip_allowlist": record.override_no_ip_allowlist,
                },
            )
        )
        await session.commit()
        refreshed = await self._load_api_key_model(session, key_id)
        return _key_to_dict(refreshed)

    async def revoke_api_key(
        self,
        session: AsyncSession,
        *,
        key_id: str,
        actor_email: str,
        reason: str,
        request_ip: str | None,
    ) -> dict[str, Any]:
        record = await self._load_api_key_model(session, key_id)
        if record.status != "active":
            raise ValueError("Only active keys can be revoked.")

        record.status = "revoked"
        record.revoked_at = _utcnow()
        record.revoked_by = actor_email
        record.revocation_reason = reason
        session.add(
            AuditEvent(
                actor_type="owner-admin",
                actor_email=actor_email,
                event_type="developer_access.api_key_revoked",
                target_type="api_key",
                target_id=record.key_id,
                request_ip=request_ip,
                metadata_json={"reason": reason},
            )
        )
        await session.commit()
        refreshed = await self._load_api_key_model(session, key_id)
        return _key_to_dict(refreshed)

    async def rotate_api_key(
        self,
        session: AsyncSession,
        *,
        key_id: str,
        actor_email: str,
        key_hmac_secret: str,
        reason: str,
        request_ip: str | None,
    ) -> tuple[dict[str, Any], str]:
        record = await self._load_api_key_model(session, key_id)
        if record.status != "active":
            raise ValueError("Only active keys can be rotated.")

        record.status = "revoked"
        record.revoked_at = _utcnow()
        record.revoked_by = actor_email
        record.revocation_reason = reason or "Rotated"

        new_key_id, key_prefix, secret_hash, raw_key = _generate_api_key(key_hmac_secret)
        replacement = APIKeyRecord(
            key_id=new_key_id,
            key_prefix=key_prefix,
            secret_hash=secret_hash,
            label=record.label,
            owner_name=record.owner_name,
            owner_email=record.owner_email,
            status="active",
            access_level=record.access_level,
            scopes=list(record.scopes),
            intended_surfaces=list(record.intended_surfaces),
            rate_limit_profile=record.rate_limit_profile,
            expires_at=record.expires_at,
            created_by=actor_email,
            override_no_ip_allowlist=record.override_no_ip_allowlist,
            override_reason=record.override_reason,
            request_id=record.request_id,
            notes=record.notes,
            ip_allowlists=[
                APIKeyIPAllowlist(
                    cidr=entry.cidr,
                    label=entry.label,
                    created_by=actor_email,
                )
                for entry in record.ip_allowlists
            ],
        )
        session.add(replacement)
        await session.flush()

        if record.request_id:
            source_request = await self._load_request_model(session, record.request_id)
            source_request.issued_key_id = replacement.id

        session.add(
            AuditEvent(
                actor_type="owner-admin",
                actor_email=actor_email,
                event_type="developer_access.api_key_rotated",
                target_type="api_key",
                target_id=record.key_id,
                request_ip=request_ip,
                metadata_json={"replacement_key_id": replacement.key_id, "reason": reason},
            )
        )
        await session.commit()
        refreshed = await self._load_api_key_model(session, replacement.key_id)
        return _key_to_dict(refreshed), raw_key

    async def validate_api_key(
        self,
        session: AsyncSession,
        raw_key: str,
        *,
        key_hmac_secret: str | None,
    ) -> dict[str, Any] | None:
        if not key_hmac_secret or not raw_key.startswith(f"{KEY_PREFIX}_"):
            return None

        parts = raw_key.split("_", 2)
        if len(parts) != 3:
            return None
        key_id = parts[1]

        try:
            record = await self._load_api_key_model(session, key_id)
        except ValueError:
            return None

        if record.status != "active":
            return None
        if record.expires_at and record.expires_at <= _utcnow():
            return None
        if not hmac.compare_digest(record.secret_hash, _compute_secret_hash(key_hmac_secret, raw_key)):
            return None

        return _key_to_dict(record)

    async def record_api_key_use(
        self,
        session: AsyncSession,
        *,
        key_id: str,
        request_ip: str | None,
    ) -> None:
        record = await self._load_api_key_model(session, key_id)
        record.last_used_at = _utcnow()
        record.last_used_ip = request_ip
        await session.commit()


developer_access_service = DeveloperAccessService()
