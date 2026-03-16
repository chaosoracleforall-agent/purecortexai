"""ORM models for developer-access requests, keys, and audit events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeveloperAccessRequest(Base):
    __tablename__ = "developer_access_requests"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    requester_name: Mapped[str] = mapped_column(String(255))
    requester_email: Mapped[str] = mapped_column(String(320), index=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    use_case: Mapped[str] = mapped_column(Text())
    requested_surfaces: Mapped[list[str]] = mapped_column(JSON, default=list)
    requested_access_level: Mapped[str] = mapped_column(String(32), default="read")
    requested_ips: Mapped[list[str]] = mapped_column(JSON, default=list)
    expected_rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    review_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    issued_key_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )

    issued_key: Mapped["APIKeyRecord | None"] = relationship(
        "APIKeyRecord",
        foreign_keys=[issued_key_id],
    )


class APIKeyRecord(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    key_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(64))
    secret_hash: Mapped[str] = mapped_column(String(255))
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_name: Mapped[str] = mapped_column(String(255))
    owner_email: Mapped[str] = mapped_column(String(320), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    access_level: Mapped[str] = mapped_column(String(32), default="read")
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    intended_surfaces: Mapped[list[str]] = mapped_column(JSON, default=list)
    rate_limit_profile: Mapped[str] = mapped_column(String(64), default="read-default")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    override_no_ip_allowlist: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    request_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("developer_access_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    source_request: Mapped["DeveloperAccessRequest | None"] = relationship(
        "DeveloperAccessRequest",
        foreign_keys=[request_id],
    )
    ip_allowlists: Mapped[list["APIKeyIPAllowlist"]] = relationship(
        "APIKeyIPAllowlist",
        back_populates="api_key",
        cascade="all, delete-orphan",
    )


class APIKeyIPAllowlist(Base):
    __tablename__ = "api_key_ip_allowlists"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    api_key_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        index=True,
    )
    cidr: Mapped[str] = mapped_column(String(64))
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_by: Mapped[str | None] = mapped_column(String(320), nullable=True)

    api_key: Mapped["APIKeyRecord"] = relationship("APIKeyRecord", back_populates="ip_allowlists")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    actor_type: Mapped[str] = mapped_column(String(64))
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    request_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
