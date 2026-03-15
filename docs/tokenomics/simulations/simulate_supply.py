"""
Monte Carlo simulation of circulating supply over 5 years under 3 adoption scenarios.

Tracks:
  - Staking emissions (yearly decay weights)
  - Creator vesting (10% TGE + 90% daily over 180 days)
  - Genesis distribution (immediate at TGE)
  - Burns from Assistance Fund (90% of ALL protocol revenue → buyback-burn)

Outputs: ../paper/figures/supply_trajectory.pdf
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from config import (
    TOTAL_SUPPLY, ALLOC_CREATOR, ALLOC_LIQUIDITY, ALLOC_STAKING,
    ALLOC_GENESIS, ALLOC_AGENT_POOL, ALLOC_ASSISTANCE_FUND,
    CREATOR_TGE_FRACTION, CREATOR_VEST_DAYS,
    STAKING_YEAR_WEIGHTS, FEE_BASE, FEE_DYNAMIC, SIGMA_MAX,
    AGENT_CREATION_FEE, SCENARIOS, SIMULATION_MONTHS,
    DAYS_PER_MONTH, DAYS_PER_YEAR,
    REVENUE_TO_ASSISTANCE_FUND,
)

# ── Matplotlib style ────────────────────────────────────────────────────
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("default")
plt.rcParams["font.family"] = "serif"

# ── Colours ──────────────────────────────────────────────────────────────
COLORS = {"low": "#90caf9", "medium": "#1e88e5", "high": "#0d47a1"}

N_MONTE_CARLO = 500
RNG = np.random.default_rng(42)


def _creator_vested(day: int) -> float:
    """Cumulative fraction of creator allocation unlocked by *day*."""
    tge = CREATOR_TGE_FRACTION
    if day <= 0:
        return tge
    daily = (1.0 - tge) / CREATOR_VEST_DAYS
    vested_days = min(day, CREATOR_VEST_DAYS)
    return tge + daily * vested_days


def _staking_emitted(day: int) -> float:
    """Cumulative fraction of staking pool emitted by *day*."""
    emitted = 0.0
    remaining_day = day
    for yr_idx, weight in enumerate(STAKING_YEAR_WEIGHTS):
        year_days = DAYS_PER_YEAR
        if remaining_day <= 0:
            break
        active_days = min(remaining_day, year_days)
        emitted += weight * (active_days / year_days)
        remaining_day -= year_days
    return min(emitted, 1.0)


def _genesis_unlocked(day: int) -> float:
    """Genesis distribution is fully unlocked at TGE (day 0)."""
    return 1.0 if day >= 0 else 0.0


def _dynamic_fee(sigma: float) -> float:
    return FEE_BASE + FEE_DYNAMIC * min(sigma / SIGMA_MAX, 1.0)


def run_simulation(scenario_name: str, n_paths: int = N_MONTE_CARLO):
    """Return array of shape (n_paths, total_days) with circulating supply."""
    sc = SCENARIOS[scenario_name]
    total_days = SIMULATION_MONTHS * DAYS_PER_MONTH
    paths = np.zeros((n_paths, total_days))

    creator_pool = TOTAL_SUPPLY * ALLOC_CREATOR
    liquidity_pool = TOTAL_SUPPLY * ALLOC_LIQUIDITY   # fully circulating at TGE
    staking_pool = TOTAL_SUPPLY * ALLOC_STAKING
    genesis_pool = TOTAL_SUPPLY * ALLOC_GENESIS        # airdrop, fully at TGE
    # Agent Incentives + Assistance Fund are NOT circulating until distributed
    agents_per_day = sc["agents_per_month"] / DAYS_PER_MONTH
    daily_volume = sc["avg_daily_volume_cortex"]

    for p in range(n_paths):
        cumulative_burn = 0.0
        for d in range(total_days):
            # Emissions & unlocks
            creator_circ = creator_pool * _creator_vested(d)
            staking_circ = staking_pool * _staking_emitted(d)
            genesis_circ = genesis_pool * _genesis_unlocked(d)

            # Burns: 90% of ALL protocol revenue → Assistance Fund → buyback-burn
            sigma = np.abs(RNG.normal(0.15, 0.10))  # daily vol
            fee_rate = _dynamic_fee(sigma)
            vol_noise = daily_volume * RNG.lognormal(0, 0.3)
            daily_fee_revenue = vol_noise * fee_rate
            # 90% of all fee revenue flows to Assistance Fund for burn
            daily_burn_from_fees = daily_fee_revenue * REVENUE_TO_ASSISTANCE_FUND

            # Agent creation burns (creation fee is 100 CORTEX)
            n_agents_today = RNG.poisson(agents_per_day)
            daily_burn_from_agents = n_agents_today * AGENT_CREATION_FEE / (10 ** 6)

            # No weekly cap — burns are continuous and proportional to revenue
            total_daily_burn = daily_burn_from_fees + daily_burn_from_agents
            cumulative_burn += total_daily_burn

            circ = (liquidity_pool + creator_circ + staking_circ + genesis_circ
                    - cumulative_burn)
            paths[p, d] = max(circ, 0)

    return paths


def find_crossover(paths: np.ndarray, scenario_name: str) -> int | None:
    """Find the first day where median supply starts declining (burns > emissions)."""
    median = np.median(paths, axis=0)
    # Use a 30-day rolling window to smooth noise
    window = 30
    if len(median) < window * 2:
        return None
    rolling = np.convolve(median, np.ones(window) / window, mode="valid")
    diffs = np.diff(rolling)
    # Find first sustained negative stretch (>= 30 consecutive days)
    neg_streak = 0
    for i, d in enumerate(diffs):
        if d < 0:
            neg_streak += 1
            if neg_streak >= 30:
                return i - 29 + window  # adjust for convolution offset
        else:
            neg_streak = 0
    return None


def plot(save: bool = True):
    fig, ax = plt.subplots(figsize=(10, 6))
    total_days = SIMULATION_MONTHS * DAYS_PER_MONTH
    months = np.arange(total_days) / DAYS_PER_MONTH

    crossover_markers = {}

    for name in ["low", "medium", "high"]:
        paths = run_simulation(name)
        # Normalise to fraction of total supply
        paths_frac = paths / TOTAL_SUPPLY

        median = np.median(paths_frac, axis=0)
        p10 = np.percentile(paths_frac, 10, axis=0)
        p90 = np.percentile(paths_frac, 90, axis=0)

        ax.plot(months, median, label=f"{name.capitalize()} adoption", color=COLORS[name],
                linewidth=2)
        ax.fill_between(months, p10, p90, alpha=0.15, color=COLORS[name])

        # Mark crossover
        xday = find_crossover(paths, name)
        if xday is not None and xday < total_days:
            crossover_markers[name] = xday
            ax.axvline(x=xday / DAYS_PER_MONTH, color=COLORS[name],
                       linestyle="--", alpha=0.6, linewidth=1)
            ax.annotate(f"Deflation ({name})",
                        xy=(xday / DAYS_PER_MONTH, median[xday]),
                        xytext=(xday / DAYS_PER_MONTH + 3, median[xday] + 0.02),
                        fontsize=8, color=COLORS[name],
                        arrowprops=dict(arrowstyle="->", color=COLORS[name], lw=0.8))

    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel("Circulating Supply (fraction of total)", fontsize=12)
    ax.set_title("$CORTEX Circulating Supply Trajectory (5-Year Monte Carlo)", fontsize=14)
    ax.legend(fontsize=11)
    ax.set_xlim(0, SIMULATION_MONTHS)
    fig.tight_layout()

    if save:
        out = os.path.join(os.path.dirname(__file__), "..", "paper", "figures",
                           "supply_trajectory.pdf")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"Saved {out}")

    return fig


if __name__ == "__main__":
    plot()
    plt.show()
