"""
veCORTEX staker yield simulation by lock duration.

Models:
  - Base staking emissions (yearly decay)
  - Fee revenue share (40% to stakers)
  - Boost multiplier: boost(v) = min(1 + 1.5 * v / v_max, 2.5)
  - Three fee revenue scenarios (low / medium / high trading volume)

Outputs: ../paper/figures/staker_yield.pdf
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from config import (
    TOTAL_SUPPLY, ALLOC_STAKING, STAKING_YEAR_WEIGHTS,
    VE_MAX_LOCK_DAYS, VE_BOOST_MAX, REVENUE_TO_ASSISTANCE_FUND,
    FEE_BASE, FEE_DYNAMIC, SCENARIOS, DAYS_PER_YEAR,
)

# ── Matplotlib style ────────────────────────────────────────────────────
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("default")
plt.rcParams["font.family"] = "serif"

# ── Colours ──────────────────────────────────────────────────────────────
COLORS = {"low": "#90caf9", "medium": "#1e88e5", "high": "#0d47a1"}


def ve_boost(lock_days: float) -> float:
    """Compute veCORTEX boost multiplier for a given lock duration."""
    v = lock_days / VE_MAX_LOCK_DAYS  # normalised voting power
    return min(1.0 + 1.5 * v, VE_BOOST_MAX)


def base_staking_apr_year1() -> float:
    """Annualised base staking APR in year 1 (before boost).

    Year-1 emission = 40% of staking pool.
    Assume 30% of total supply is staked (reasonable equilibrium).
    """
    staking_pool = TOTAL_SUPPLY * ALLOC_STAKING
    year1_emission = staking_pool * STAKING_YEAR_WEIGHTS[0]
    assumed_staked = TOTAL_SUPPLY * 0.30  # 30% staked
    return year1_emission / assumed_staked  # fractional APR


def buyback_apr(scenario_name: str) -> float:
    """Annualised indirect yield from Assistance Fund buyback-burn.

    90% of all fee revenue buys back and burns CORTEX, reducing supply.
    This models the effective APR equivalent for stakers from supply reduction.
    Buyback APR = (annual_burn_value / circulating_supply)
    """
    sc = SCENARIOS[scenario_name]
    daily_volume = sc["avg_daily_volume_cortex"]
    avg_sigma = 0.15  # typical daily vol
    avg_fee = FEE_BASE + FEE_DYNAMIC * min(avg_sigma / 0.50, 1.0)
    annual_burn = daily_volume * avg_fee * REVENUE_TO_ASSISTANCE_FUND * DAYS_PER_YEAR
    assumed_circulating = TOTAL_SUPPLY * 0.50  # ~50% circulating at steady state
    return annual_burn / assumed_circulating


def compute_yield(lock_days: float, scenario_name: str) -> float:
    """Total annualised yield (%) for a staker with given lock duration."""
    boost = ve_boost(lock_days)
    base = base_staking_apr_year1() * boost
    fees = buyback_apr(scenario_name) * boost
    return (base + fees) * 100  # percentage


def plot(save: bool = True):
    fig, ax = plt.subplots(figsize=(10, 6))

    lock_durations = np.linspace(7, VE_MAX_LOCK_DAYS, 500)  # 1 week to 4 years

    for name in ["low", "medium", "high"]:
        yields = [compute_yield(d, name) for d in lock_durations]
        ax.plot(lock_durations / DAYS_PER_YEAR, yields,
                label=f"{name.capitalize()} volume", color=COLORS[name], linewidth=2)

    # Add boost multiplier on secondary y-axis
    ax2 = ax.twinx()
    boosts = [ve_boost(d) for d in lock_durations]
    ax2.plot(lock_durations / DAYS_PER_YEAR, boosts,
             color="#bdbdbd", linestyle=":", linewidth=1.5, label="Boost multiplier")
    ax2.set_ylabel("Boost multiplier", fontsize=11, color="#757575")
    ax2.set_ylim(0.9, VE_BOOST_MAX + 0.3)
    ax2.tick_params(axis="y", labelcolor="#757575")

    # Reference lines
    ax.axhline(y=0, color="black", linewidth=0.5)

    ax.set_xlabel("Lock duration (years)", fontsize=12)
    ax.set_ylabel("Annualised yield (%)", fontsize=12)
    ax.set_title("veCORTEX Staker Yield by Lock Duration", fontsize=14)

    # Combine legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=10, loc="upper left")

    fig.tight_layout()

    if save:
        out = os.path.join(os.path.dirname(__file__), "..", "paper", "figures",
                           "staker_yield.pdf")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"Saved {out}")

    return fig


if __name__ == "__main__":
    plot()
    plt.show()
