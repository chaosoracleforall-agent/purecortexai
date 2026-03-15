"""
Transparency API for PURECORTEX.

Provides real-time on-chain data about CORTEX token supply,
treasury balances, burn history, governance stats, and agent registry.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.algorand import get_algorand_service, FACTORY_APP_ID
from src.services.cache import cache_with_ttl, TTL_SUPPLY, TTL_TREASURY, TTL_BURNS, TTL_AGENTS, TTL_GOVERNANCE
from src.services.protocol_config import (
    ASSISTANCE_FUND_ADDRESS,
    CORTEX_ASSET_ID,
    OPERATIONS_ADDRESS,
    TGE_DATE_ISO,
    TOTAL_SUPPLY as PROTOCOL_TOTAL_SUPPLY,
)

logger = logging.getLogger("purecortex.api.transparency")

router = APIRouter(prefix="/api/transparency", tags=["transparency"])

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
TOTAL_SUPPLY = PROTOCOL_TOTAL_SUPPLY
TGE_DATE = datetime.fromisoformat(TGE_DATE_ISO.replace("Z", "+00:00"))
CREATOR_ALLOCATION = TOTAL_SUPPLY * 10 // 100  # 10% = 1Q
CREATOR_TGE_UNLOCK_PCT = 10  # 10% at TGE
CREATOR_VEST_DAYS = 180

SUPPLY_ALLOCATION = [
    {"label": "Genesis Airdrop", "pct": 31, "amount": TOTAL_SUPPLY * 31 // 100},
    {"label": "Staking Rewards", "pct": 24, "amount": TOTAL_SUPPLY * 24 // 100},
    {"label": "Liquidity", "pct": 15, "amount": TOTAL_SUPPLY * 15 // 100},
    {"label": "Agent Incentives", "pct": 15, "amount": TOTAL_SUPPLY * 15 // 100},
    {"label": "Creator", "pct": 10, "amount": TOTAL_SUPPLY * 10 // 100},
    {"label": "Assistance Fund", "pct": 5, "amount": TOTAL_SUPPLY * 5 // 100},
]


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────
class AllocationItem(BaseModel):
    label: str
    pct: int
    amount: int


class VestingInfo(BaseModel):
    released: int
    remaining: int
    pct_released: float
    tge_date: str = TGE_DATE.isoformat()
    vest_days: int = CREATOR_VEST_DAYS


class SupplyResponse(BaseModel):
    total_supply: int
    circulating: int
    burned: int
    vesting: VestingInfo
    allocation: list[AllocationItem]


class WalletInfo(BaseModel):
    address: str
    balance_algo: float
    balance_cortex: int


class TreasuryResponse(BaseModel):
    assistance_fund: WalletInfo
    operations: WalletInfo
    total_revenue_collected: int
    revenue_split: dict


class BurnRecord(BaseModel):
    txn_id: str
    amount: int
    round: int
    timestamp: str


class BurnsResponse(BaseModel):
    total_burned: int
    burn_history: list[BurnRecord]
    note: Optional[str] = None


class GovernanceTransparencyResponse(BaseModel):
    total_proposals: int
    active_proposals: list
    participation_rate: float
    total_vecortex: int
    note: Optional[str] = None


class AgentInfo(BaseModel):
    asset_id: int
    name: str
    unit_name: str
    total: int
    decimals: int
    creator_txn: str


class AgentsResponse(BaseModel):
    factory_app_id: int
    total_agents: int
    agents: list[AgentInfo]
    note: Optional[str] = None


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _compute_vesting() -> VestingInfo:
    """
    Calculate creator vesting based on current date relative to TGE.
    - 10% unlocks at TGE
    - Remaining 90% vests daily over 180 days
    """
    now = datetime.now(timezone.utc)

    if now < TGE_DATE:
        # Pre-TGE: nothing released
        return VestingInfo(released=0, remaining=CREATOR_ALLOCATION, pct_released=0.0)

    tge_unlock = CREATOR_ALLOCATION * CREATOR_TGE_UNLOCK_PCT // 100
    vesting_pool = CREATOR_ALLOCATION - tge_unlock  # 90% of creator allocation

    days_since_tge = (now - TGE_DATE).days
    if days_since_tge >= CREATOR_VEST_DAYS:
        # Fully vested
        return VestingInfo(
            released=CREATOR_ALLOCATION,
            remaining=0,
            pct_released=100.0,
        )

    daily_vest = vesting_pool // CREATOR_VEST_DAYS
    vested_so_far = tge_unlock + (daily_vest * days_since_tge)
    remaining = CREATOR_ALLOCATION - vested_so_far
    pct = round((vested_so_far / CREATOR_ALLOCATION) * 100, 2)

    return VestingInfo(released=vested_so_far, remaining=remaining, pct_released=pct)


def _compute_circulating(burned: int, vesting: VestingInfo) -> int:
    """
    Circulating = Genesis Airdrop allocation (unlocked at TGE).
    Pre-TGE: circulating = Genesis Airdrop amount (airdrop already distributed).
    Post-TGE: would add vested creator tokens, staking emissions, etc.
    For now, return the genesis airdrop amount as the initial circulating supply.
    """
    genesis_airdrop = TOTAL_SUPPLY * 31 // 100
    return genesis_airdrop


def _wallet_label(address: Optional[str], label: str) -> str:
    return address or f"{label} not assigned on testnet yet"


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────
@router.get("/supply", response_model=SupplyResponse)
@cache_with_ttl("transparency:supply", TTL_SUPPLY)
async def get_supply():
    """CORTEX token supply breakdown with vesting schedule."""
    vesting = _compute_vesting()
    burned = 0  # Will query on-chain post-TGE
    circulating = _compute_circulating(burned, vesting)

    return SupplyResponse(
        total_supply=TOTAL_SUPPLY,
        circulating=circulating,
        burned=burned,
        vesting=vesting,
        allocation=[AllocationItem(**a) for a in SUPPLY_ALLOCATION],
    )


@router.get("/treasury", response_model=TreasuryResponse)
@cache_with_ttl("transparency:treasury", TTL_TREASURY)
async def get_treasury():
    """Treasury wallet balances and revenue split."""
    return TreasuryResponse(
        assistance_fund=WalletInfo(
            address=_wallet_label(ASSISTANCE_FUND_ADDRESS, "Assistance Fund"),
            balance_algo=0,
            balance_cortex=0,
        ),
        operations=WalletInfo(
            address=_wallet_label(OPERATIONS_ADDRESS, "Operations"),
            balance_algo=0,
            balance_cortex=0,
        ),
        total_revenue_collected=0,
        revenue_split={"buyback_burn_pct": 90, "operations_pct": 10},
    )


@router.get("/burns", response_model=BurnsResponse)
@cache_with_ttl("transparency:burns", TTL_BURNS)
async def get_burns():
    """Burn history and total burned CORTEX."""
    return BurnsResponse(
        total_burned=0,
        burn_history=[],
        note="Burns begin after TGE (March 31, 2026)",
    )


@router.get("/governance", response_model=GovernanceTransparencyResponse)
@cache_with_ttl("transparency:governance", TTL_GOVERNANCE)
async def get_governance_transparency():
    """Governance overview — proposals, participation, and veCORTEX totals."""
    return GovernanceTransparencyResponse(
        total_proposals=0,
        active_proposals=[],
        participation_rate=0,
        total_vecortex=0,
        note="Governance launches at TGE (March 31, 2026)",
    )


@router.get("/agents", response_model=AgentsResponse)
@cache_with_ttl("transparency:agents", TTL_AGENTS)
async def get_agents():
    """Query live agent data from the Algorand indexer via the factory app."""
    algo_service = get_algorand_service()
    try:
        agents_raw = await algo_service.get_agent_tokens(FACTORY_APP_ID)
        agents = [AgentInfo(**a) for a in agents_raw]
        return AgentsResponse(
            factory_app_id=FACTORY_APP_ID,
            total_agents=len(agents),
            agents=agents,
            note="Live data from Algorand indexer",
        )
    except Exception as e:
        logger.error("Failed to query agents from indexer: %s", e)
        return AgentsResponse(
            factory_app_id=FACTORY_APP_ID,
            total_agents=0,
            agents=[],
            note="Agent data temporarily unavailable",
        )
