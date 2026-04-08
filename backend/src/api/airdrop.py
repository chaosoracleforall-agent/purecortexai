"""Airdrop registration, eligibility, and proof API."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from algosdk.encoding import is_valid_address
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.db import get_database_manager
from src.services.airdrop import airdrop_service

logger = logging.getLogger("purecortex.api.airdrop")

router = APIRouter(prefix="/api/airdrop", tags=["airdrop"])

# Snapshot data is loaded lazily from the most recent snapshot file
_snapshot_cache: dict[str, Any] | None = None
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "snapshots"


def _load_snapshot() -> dict[str, Any] | None:
    """Load and verify the most recent airdrop snapshot file.

    Verifies SHA-256 integrity against the companion .sha256 file to
    detect tampering (BE-001).
    """
    global _snapshot_cache
    if _snapshot_cache is not None:
        return _snapshot_cache

    if not SNAPSHOT_DIR.exists():
        return None

    snapshot_files = sorted(SNAPSHOT_DIR.glob("airdrop_snapshot_*.json"), reverse=True)
    if not snapshot_files:
        return None

    snapshot_path = snapshot_files[0]
    try:
        raw = snapshot_path.read_text()

        # Verify integrity hash if companion file exists
        hash_path = snapshot_path.with_suffix(".sha256")
        if hash_path.exists():
            expected_hash = hash_path.read_text().strip()
            actual_hash = hashlib.sha256(raw.encode()).hexdigest()
            if actual_hash != expected_hash:
                logger.critical(
                    "Airdrop snapshot INTEGRITY CHECK FAILED: %s "
                    "(expected %s, got %s). Refusing to load.",
                    snapshot_path.name,
                    expected_hash[:16],
                    actual_hash[:16],
                )
                return None
            logger.info("Snapshot integrity verified: %s", snapshot_path.name)
        else:
            logger.warning(
                "No .sha256 companion file for %s — loading without integrity check",
                snapshot_path.name,
            )

        _snapshot_cache = json.loads(raw)
        logger.info("Loaded airdrop snapshot: %s", snapshot_path.name)
        return _snapshot_cache
    except Exception as exc:
        logger.error("Failed to load airdrop snapshot: %s", exc)
        return None


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


@router.get("/eligibility/{address}")
async def check_eligibility(address: str):
    """Check airdrop eligibility for a wallet address."""
    wallet_address = address.strip().upper()
    if not is_valid_address(wallet_address):
        raise HTTPException(status_code=400, detail="Invalid Algorand wallet address.")

    snapshot = _load_snapshot()
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Airdrop snapshot not yet available. Snapshot window: Apr 1-7, 2026.",
        )

    proofs = snapshot.get("proofs", {})
    wallet_data = proofs.get(wallet_address)

    if wallet_data is None:
        # Check wallets list for tier info even without proof
        for w in snapshot.get("wallets", []):
            if w.get("address") == wallet_address:
                return {
                    "address": wallet_address,
                    "eligible": True,
                    "tiers": w.get("tiers", []),
                    "allocation": w.get("total_allocation", 0),
                    "merkle_root": snapshot.get("merkle_root"),
                }

        return {
            "address": wallet_address,
            "eligible": False,
            "tiers": [],
            "allocation": 0,
            "message": "Wallet not found in snapshot. Check eligibility criteria.",
        }

    return {
        "address": wallet_address,
        "eligible": True,
        "allocation": wallet_data.get("amount", 0),
        "merkle_root": snapshot.get("merkle_root"),
        "snapshot_time": snapshot.get("snapshot_time"),
    }


@router.get("/proof/{address}")
async def get_merkle_proof(address: str):
    """Return the Merkle proof for a wallet's airdrop claim.

    The proof can be submitted directly to the AirdropClaim smart contract.
    """
    wallet_address = address.strip().upper()
    if not is_valid_address(wallet_address):
        raise HTTPException(status_code=400, detail="Invalid Algorand wallet address.")

    snapshot = _load_snapshot()
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Airdrop snapshot not yet available.",
        )

    proofs = snapshot.get("proofs", {})
    wallet_data = proofs.get(wallet_address)

    if wallet_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No airdrop allocation found for this address.",
        )

    return {
        "address": wallet_address,
        "amount": wallet_data["amount"],
        "proof": wallet_data["proof"],
        "proof_packed_hex": wallet_data["proof_packed_hex"],
        "merkle_root": snapshot.get("merkle_root"),
    }
