"""Developer-access services backed by the managed database foundation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import APIKeyRecord, AuditEvent, DeveloperAccessRequest


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
    return {
        "id": model.id,
        "key_id": model.key_id,
        "key_prefix": model.key_prefix,
        "label": model.label,
        "owner_name": model.owner_name,
        "owner_email": model.owner_email,
        "status": model.status,
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
        "request_id": model.request_id,
        "notes": model.notes,
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


developer_access_service = DeveloperAccessService()
