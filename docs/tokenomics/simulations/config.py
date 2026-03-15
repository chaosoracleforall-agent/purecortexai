"""
PURECORTEX ($CORTEX) Tokenomics — Shared Simulation Constants
"""

from dataclasses import dataclass
from decimal import Decimal

# ── Token Supply ──────────────────────────────────────────────────────
TOTAL_SUPPLY = 10_000_000_000_000_000  # 10 quadrillion (6 decimals)
DECIMALS = 6

# ── Allocation (fractions of total supply) ────────────────────────────
ALLOC_CREATOR           = 0.10   # 10% — Creator (10% TGE, 90% daily 180d)
ALLOC_GENESIS           = 0.31   # 31% — Genesis Distribution (airdrop)
ALLOC_STAKING           = 0.24   # 24% — Future Emissions & Staking (veCORTEX)
ALLOC_LIQUIDITY         = 0.15   # 15% — Liquidity (DEX LP, 10yr lock)
ALLOC_AGENT_POOL        = 0.15   # 15% — Agent Incentives (graduation, composability)
ALLOC_ASSISTANCE_FUND   = 0.05   # 5%  — Assistance Fund (seed for buyback engine)

# ── Creator Vesting ───────────────────────────────────────────────────
CREATOR_TGE_FRACTION = 0.10       # 10% released at TGE
CREATOR_VEST_DAYS    = 180        # remaining 90% vests daily over 180 days

# ── Staking Emission Decay (year weights) ─────────────────────────────
STAKING_YEAR_WEIGHTS = [0.40, 0.30, 0.20, 0.10]  # 4-year halving decay

# ── Bonding Curve Parameters ──────────────────────────────────────────
BASE_PRICE = 10_000     # base price per token (micro-ALGO)
SLOPE      = 1_000      # curve steepness

# ── Agent Parameters ──────────────────────────────────────────────────
AGENT_TOKEN_SUPPLY     = 1_000_000_000   # 1B per agent
AGENT_CREATION_FEE     = 100_000_000     # 100 CORTEX (in micro-units)
GRADUATION_THRESHOLD   = 50_000_000_000  # 50,000 CORTEX (in micro-units)

# ── Dynamic Fee Parameters ────────────────────────────────────────────
FEE_BASE     = 0.005    # 0.5% floor
FEE_DYNAMIC  = 0.015    # up to 1.5% additional
SIGMA_MAX    = 0.50     # 50% daily volatility ceiling

# ── Protocol Revenue Split ────────────────────────────────────────────
REVENUE_TO_ASSISTANCE_FUND = 0.90   # 90% of ALL protocol revenue → buyback-burn
REVENUE_TO_OPERATIONS      = 0.10   # 10% of ALL protocol revenue → operations/dev

# ── veCORTEX Staking ─────────────────────────────────────────────────
VE_MAX_LOCK_DAYS  = 1461   # ~4 years
VE_BOOST_MAX      = 2.5    # max emission multiplier

# ── Buyback & Burn (Assistance Fund) ─────────────────────────────────
# No weekly caps — burns are continuous and proportional to revenue.
# The Assistance Fund buys CORTEX from the open market and burns it.

# ── Governance ────────────────────────────────────────────────────────
@dataclass
class ProposalType:
    name: str
    quorum: float
    threshold: float
    timelock_hours: int

PROPOSAL_TYPES = [
    ProposalType("Parameter Change",       0.10, 0.50, 24),
    ProposalType("Treasury Action",        0.15, 0.60, 48),
    ProposalType("Constitution Amendment", 0.25, 0.67, 168),
    ProposalType("Emergency Action",       0.05, 0.75, 1),
]

# ── Simulation Scenarios ──────────────────────────────────────────────
SCENARIOS = {
    "low":    {"agents_per_month": 10, "avg_daily_volume_cortex": 500_000},
    "medium": {"agents_per_month": 30, "avg_daily_volume_cortex": 2_000_000},
    "high":   {"agents_per_month": 50, "avg_daily_volume_cortex": 5_000_000},
}

# ── Time Horizons ─────────────────────────────────────────────────────
SIMULATION_MONTHS = 60   # 5 years
DAYS_PER_MONTH    = 30
DAYS_PER_YEAR     = 365
