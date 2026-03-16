"""Public staking and delegation read API."""

from __future__ import annotations

from math import ceil

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.algorand import get_algorand_service


router = APIRouter(prefix="/api/staking", tags=["staking"])

ROUNDS_PER_DAY = 17280


class StakingOverviewResponse(BaseModel):
    app_id: int
    cortex_asset_id: int
    total_staked: int
    reward_pool: int
    min_lock_days: int
    max_lock_days: int
    max_boost_bps: int
    current_round: int


class StakingAccountResponse(BaseModel):
    address: str
    has_active_stake: bool
    amount: int
    unlock_round: int | None
    current_round: int
    lock_days_remaining: int
    ve_power: int
    boost_bps: int
    delegate: str | None
    delegated_power_received: int
    delegated_amount_received: int
    delegator_count: int


class DelegateSummaryResponse(BaseModel):
    delegate: str
    delegator_count: int
    delegated_power: int
    delegated_amount: int
    delegators: list[str]
    self_stake: dict | None = None


@router.get("/overview", response_model=StakingOverviewResponse)
async def get_staking_overview():
    algo = get_algorand_service()
    return StakingOverviewResponse(**await algo.get_staking_overview())


@router.get("/account/{address}", response_model=StakingAccountResponse)
async def get_staking_account(address: str):
    algo = get_algorand_service()
    try:
        overview = await algo.get_staking_overview()
        snapshot = await algo.get_stake_snapshot(address)
        delegate_summary = await algo.get_delegate_summary(address)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to query staking state: {exc}") from exc

    current_round = int(overview["current_round"])
    if not snapshot:
        return StakingAccountResponse(
            address=address,
            has_active_stake=False,
            amount=0,
            unlock_round=None,
            current_round=current_round,
            lock_days_remaining=0,
            ve_power=0,
            boost_bps=0,
            delegate=None,
            delegated_power_received=int(delegate_summary["delegated_power"]),
            delegated_amount_received=int(delegate_summary["delegated_amount"]),
            delegator_count=int(delegate_summary["delegator_count"]),
        )

    rounds_remaining = max(int(snapshot["unlock_round"]) - current_round, 0)
    lock_days_remaining = ceil(rounds_remaining / ROUNDS_PER_DAY) if rounds_remaining else 0

    return StakingAccountResponse(
        address=address,
        has_active_stake=True,
        amount=int(snapshot["amount"]),
        unlock_round=int(snapshot["unlock_round"]),
        current_round=current_round,
        lock_days_remaining=lock_days_remaining,
        ve_power=int(snapshot["ve_power"]),
        boost_bps=int(snapshot["boost_bps"]),
        delegate=snapshot.get("delegate"),
        delegated_power_received=int(delegate_summary["delegated_power"]),
        delegated_amount_received=int(delegate_summary["delegated_amount"]),
        delegator_count=int(delegate_summary["delegator_count"]),
    )


@router.get("/delegate/{address}", response_model=DelegateSummaryResponse)
async def get_delegate_summary(address: str):
    algo = get_algorand_service()
    try:
        summary = await algo.get_delegate_summary(address)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to query delegate summary: {exc}") from exc

    return DelegateSummaryResponse(**summary)
