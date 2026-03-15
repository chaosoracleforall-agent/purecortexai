"""
Sensitivity heatmap: deflationary crossover month as a function of
base fee rate and graduation threshold.

Outputs: ../paper/figures/sensitivity_heatmap.pdf
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from config import (
    TOTAL_SUPPLY, ALLOC_CREATOR, ALLOC_STAKING, ALLOC_GENESIS,
    STAKING_YEAR_WEIGHTS, CREATOR_TGE_FRACTION, CREATOR_VEST_DAYS,
    DAYS_PER_MONTH, REVENUE_TO_ASSISTANCE_FUND
)

# ── Matplotlib style ────────────────────────────────────────────────────
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("default")
plt.rcParams["font.family"] = "serif"


def compute_crossover_month(fee_base: float, grad_threshold: float,
                            agents_per_month: int = 30,
                            avg_daily_volume: float = 2_000_000) -> float:
    """Compute the month at which burns exceed new emissions."""
    creator_total = TOTAL_SUPPLY * ALLOC_CREATOR
    staking_total = TOTAL_SUPPLY * ALLOC_STAKING
    genesis_total = TOTAL_SUPPLY * ALLOC_GENESIS

    for month in range(1, 61):
        day = month * DAYS_PER_MONTH

        # ── Emission rate (staking) ───────────────────────────────
        year = min(day // 365, 3)
        weight = STAKING_YEAR_WEIGHTS[year]
        yearly_emission = staking_total * weight / sum(STAKING_YEAR_WEIGHTS)
        daily_emission = yearly_emission / 365

        # ── Vesting rate (creator) ────────────────────────────────
        if day <= CREATOR_VEST_DAYS:
            daily_vest = creator_total * (1 - CREATOR_TGE_FRACTION) / CREATOR_VEST_DAYS
        else:
            daily_vest = 0

        # ── Genesis unlock (all at TGE, no ongoing emission) ────
        daily_eco = 0  # genesis fully unlocked at TGE

        total_new_daily = daily_emission + daily_vest + daily_eco

        # ── Burn rate (90% of all revenue → Assistance Fund) ─────
        daily_fee_burn = avg_daily_volume * fee_base * REVENUE_TO_ASSISTANCE_FUND
        # Burns from agent creation (50% of 100 CORTEX per agent)
        daily_agent_burn = (agents_per_month / DAYS_PER_MONTH) * 50_000_000
        # Scale volume with agent count growth
        volume_mult = 1 + 0.02 * month  # 2% monthly growth
        total_daily_burn = daily_fee_burn * volume_mult + daily_agent_burn

        if total_daily_burn > total_new_daily:
            return month

    return 60  # didn't cross over in 5 years


def plot(save: bool = True):
    fee_rates = np.linspace(0.0025, 0.01, 20)    # 0.25% to 1.0%
    grad_thresholds = np.linspace(25_000, 100_000, 20)  # 25K to 100K CORTEX

    crossover = np.zeros((len(fee_rates), len(grad_thresholds)))

    for i, fee in enumerate(fee_rates):
        for j, grad in enumerate(grad_thresholds):
            # Higher graduation threshold → fewer agents graduate → less volume
            agent_mult = max(0.5, 1.0 - (grad - 50_000) / 100_000)
            crossover[i, j] = compute_crossover_month(
                fee, grad, agents_per_month=int(30 * agent_mult)
            )

    fig, ax = plt.subplots(figsize=(8, 6))

    im = ax.imshow(
        crossover, origin="lower", aspect="auto",
        cmap="RdYlGn_r",
        extent=[grad_thresholds[0] / 1000, grad_thresholds[-1] / 1000,
                fee_rates[0] * 100, fee_rates[-1] * 100],
    )

    cbar = fig.colorbar(im, ax=ax, label="Deflationary Crossover (Month)")

    # Mark the selected parameters
    ax.plot(50, 0.5, "s", color="white", markersize=12, markeredgecolor="black",
            markeredgewidth=2, zorder=5)
    ax.annotate("Selected\nparameters", xy=(50, 0.5),
                xytext=(65, 0.35), fontsize=9, color="black",
                arrowprops=dict(arrowstyle="->", color="black", lw=1.5))

    ax.set_xlabel("Graduation Threshold (K CORTEX)", fontsize=11)
    ax.set_ylabel("Base Fee Rate (%)", fontsize=11)
    ax.set_title("Sensitivity: Deflationary Crossover Month", fontsize=13)

    fig.tight_layout()

    if save:
        out = os.path.join(os.path.dirname(__file__), "..", "paper", "figures",
                           "sensitivity_heatmap.pdf")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"Saved {out}")

    return fig


if __name__ == "__main__":
    plot()
    plt.show()
