"""ORM model for genesis airdrop wallet registrations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AirdropRegistration(Base):
    __tablename__ = "airdrop_registrations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    wallet_address: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
