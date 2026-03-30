"""Airdrop registration persistence service."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AirdropRegistration


def _to_dict(record: AirdropRegistration, *, already_registered: bool) -> dict[str, Any]:
    return {
        "id": record.id,
        "wallet_address": record.wallet_address,
        "created_at": record.created_at.isoformat(),
        "already_registered": already_registered,
    }


class AirdropService:
    async def register_wallet(
        self,
        session: AsyncSession,
        *,
        wallet_address: str,
        source_ip: str | None,
    ) -> dict[str, Any]:
        existing = await session.scalar(
            select(AirdropRegistration).where(
                AirdropRegistration.wallet_address == wallet_address
            )
        )
        if existing is not None:
            return _to_dict(existing, already_registered=True)

        record = AirdropRegistration(
            wallet_address=wallet_address,
            source_ip=source_ip,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return _to_dict(record, already_registered=False)


airdrop_service = AirdropService()
