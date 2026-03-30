"""Airdrop registration API."""

from __future__ import annotations

from algosdk.encoding import is_valid_address
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.db import get_database_manager
from src.services.airdrop import airdrop_service


router = APIRouter(prefix="/api/airdrop", tags=["airdrop"])


class AirdropRegistrationRequest(BaseModel):
    wallet_address: str = Field(..., min_length=32, max_length=64)


class AirdropRegistrationResponse(BaseModel):
    id: str
    wallet_address: str
    created_at: str
    already_registered: bool
    message: str


@router.post("/register", response_model=AirdropRegistrationResponse)
async def register_airdrop_wallet(
    body: AirdropRegistrationRequest,
    request: Request,
):
    wallet_address = body.wallet_address.strip().upper()
    if not is_valid_address(wallet_address):
        raise HTTPException(status_code=400, detail="Invalid Algorand wallet address.")

    manager = get_database_manager()
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Airdrop registration service unavailable",
        )

    async with manager.session() as session:
        result = await airdrop_service.register_wallet(
            session,
            wallet_address=wallet_address,
            source_ip=getattr(request.state, "client_ip", None),
        )

    return AirdropRegistrationResponse(
        **result,
        message=(
            "Wallet already registered for the genesis airdrop."
            if result["already_registered"]
            else "Wallet registered for the genesis airdrop."
        ),
    )
