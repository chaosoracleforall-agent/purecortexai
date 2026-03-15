"""
Market crash stress test: 50% price drop at month 12.

Compares recovery paths for:
  (a) Spot CORTEX holders
  (b) veCORTEX stakers (with fee revenue)
  (c) LP providers (with impermanent loss + fee income)

1000 Monte Carlo paths; crash occurs at month 12; evaluate at month 24.

Outputs: ../paper/figures/stress_test.pdf
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from config import (
    REVENUE_TO_ASSISTANCE_FUND, FEE_BASE, FEE_DYNAMIC, SIGMA_MAX,
    VE_BOOST_MAX, DAYS_PER_MONTH,
)

# ── Matplotlib style ────────────────────────────────────────────────────
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("default")
plt.rcParams["font.family"] = "serif"

# ── Simulation parameters ───────────────────────────────────────────────
N_PATHS = 1000
CRASH_MONTH = 12
EVAL_MONTH = 24
TOTAL_DAYS = EVAL_MONTH * DAYS_PER_MONTH
CRASH_DAY = CRASH_MONTH * DAYS_PER_MONTH
CRASH_MAGNITUDE = 0.50  # 50% price drop

INITIAL_PRICE = 1.0  # normalised
DAILY_DRIFT = 0.0002  # slight positive drift
DAILY_VOL_NORMAL = 0.03
DAILY_VOL_CRASH = 0.08  # elevated vol post-crash

# Staker parameters
STAKER_APR_BASE = 0.12  # 12% base APR from emissions
STAKER_FEE_YIELD_DAILY = 0.0001  # daily fee yield fraction (boosted)

# LP parameters
LP_FEE_SHARE = 0.003  # 0.3% per trade, LP share
LP_DAILY_VOLUME_FRAC = 0.02  # daily volume as fraction of pool

RNG = np.random.default_rng(42)

# ── Colours ──────────────────────────────────────────────────────────────
C_SPOT = "#ef5350"
C_STAKER = "#1e88e5"
C_LP = "#66bb6a"


def simulate_price_path() -> np.ndarray:
    """GBM price path with a forced crash at CRASH_DAY."""
    prices = np.zeros(TOTAL_DAYS)
    prices[0] = INITIAL_PRICE

    for d in range(1, TOTAL_DAYS):
        if d == CRASH_DAY:
            # Crash: instantaneous 50% drop
            prices[d] = prices[d - 1] * (1 - CRASH_MAGNITUDE)
        else:
            vol = DAILY_VOL_CRASH if d > CRASH_DAY and d < CRASH_DAY + 60 else DAILY_VOL_NORMAL
            drift = DAILY_DRIFT
            shock = RNG.normal(drift - 0.5 * vol**2, vol)
            prices[d] = prices[d - 1] * np.exp(shock)

    return prices


def spot_value(prices: np.ndarray) -> float:
    """Spot holder: final value = final price / initial price."""
    return prices[-1] / prices[0]


def staker_value(prices: np.ndarray) -> float:
    """veCORTEX staker: spot value + cumulative staking emissions + fee yield.

    Staker earns daily emissions + fee revenue (boosted), compounded.
    """
    daily_emission_rate = STAKER_APR_BASE / 365
    cumulative_yield = 0.0
    # Fee yield increases during high-vol periods
    for d in range(TOTAL_DAYS):
        vol = DAILY_VOL_CRASH if CRASH_DAY < d < CRASH_DAY + 60 else DAILY_VOL_NORMAL
        sigma = min(vol / DAILY_VOL_NORMAL, 1.0)
        fee_multiplier = 1.0 + 2.0 * sigma  # higher fees in volatile periods
        daily_yield = daily_emission_rate + STAKER_FEE_YIELD_DAILY * fee_multiplier
        cumulative_yield += daily_yield

    # Total value: spot appreciation + yield (denominated in tokens, valued at final price)
    spot = prices[-1] / prices[0]
    return spot * (1.0 + cumulative_yield)


def lp_value(prices: np.ndarray) -> float:
    """LP provider: subject to impermanent loss but earns trading fees.

    IL formula: IL = 2*sqrt(r)/(1+r) - 1, where r = P_final/P_initial
    Fee income accumulates daily, higher during volatile periods.
    """
    r = prices[-1] / prices[0]
    il_factor = 2 * np.sqrt(r) / (1 + r)  # always <= 1

    # Fee income: daily volume * fee rate
    cumulative_fee_income = 0.0
    for d in range(TOTAL_DAYS):
        vol = DAILY_VOL_CRASH if CRASH_DAY < d < CRASH_DAY + 60 else DAILY_VOL_NORMAL
        daily_fee = LP_DAILY_VOLUME_FRAC * LP_FEE_SHARE * (1 + vol / DAILY_VOL_NORMAL)
        cumulative_fee_income += daily_fee

    return il_factor + cumulative_fee_income


def run_simulation():
    """Run N_PATHS Monte Carlo simulations, return final portfolio values."""
    spot_vals = np.zeros(N_PATHS)
    staker_vals = np.zeros(N_PATHS)
    lp_vals = np.zeros(N_PATHS)

    for i in range(N_PATHS):
        prices = simulate_price_path()
        spot_vals[i] = spot_value(prices)
        staker_vals[i] = staker_value(prices)
        lp_vals[i] = lp_value(prices)

    return spot_vals, staker_vals, lp_vals


def plot(save: bool = True):
    spot_vals, staker_vals, lp_vals = run_simulation()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # ── Plot 1: Distribution of portfolio values at month 24 ─────────────
    ax = axes[0]
    bins = np.linspace(0, 2.5, 60)

    ax.hist(spot_vals, bins=bins, alpha=0.6, color=C_SPOT, label="Spot holders",
            density=True, edgecolor="white", linewidth=0.5)
    ax.hist(staker_vals, bins=bins, alpha=0.6, color=C_STAKER, label="veCORTEX stakers",
            density=True, edgecolor="white", linewidth=0.5)
    ax.hist(lp_vals, bins=bins, alpha=0.6, color=C_LP, label="LP providers",
            density=True, edgecolor="white", linewidth=0.5)

    # Median lines
    for vals, color, name in [(spot_vals, C_SPOT, "Spot"),
                               (staker_vals, C_STAKER, "Staker"),
                               (lp_vals, C_LP, "LP")]:
        med = np.median(vals)
        ax.axvline(x=med, color=color, linestyle="--", linewidth=1.5)
        ax.text(med + 0.02, ax.get_ylim()[1] * 0.9, f"{name}\nmed={med:.2f}",
                fontsize=8, color=color, va="top")

    ax.axvline(x=1.0, color="black", linestyle=":", linewidth=1, alpha=0.5)
    ax.text(1.01, ax.get_ylim()[1] * 0.5, "Break-even", fontsize=8, rotation=90,
            color="black", alpha=0.5)

    ax.set_xlabel("Portfolio value (normalised, 1.0 = initial)", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.set_title("Portfolio Value Distribution at Month 24\n(50% crash at Month 12)",
                 fontsize=12)
    ax.legend(fontsize=10)

    # ── Plot 2: Recovery statistics ──────────────────────────────────────
    ax = axes[1]
    groups = ["Spot", "veCORTEX\nStaker", "LP\nProvider"]
    medians = [np.median(spot_vals), np.median(staker_vals), np.median(lp_vals)]
    q25 = [np.percentile(spot_vals, 25), np.percentile(staker_vals, 25),
           np.percentile(lp_vals, 25)]
    q75 = [np.percentile(spot_vals, 75), np.percentile(staker_vals, 75),
           np.percentile(lp_vals, 75)]

    colors = [C_SPOT, C_STAKER, C_LP]
    x = np.arange(len(groups))
    bars = ax.bar(x, medians, color=colors, alpha=0.8, width=0.5, edgecolor="white")

    # Error bars for IQR
    yerr_low = [medians[i] - q25[i] for i in range(3)]
    yerr_high = [q75[i] - medians[i] for i in range(3)]
    ax.errorbar(x, medians, yerr=[yerr_low, yerr_high], fmt="none",
                ecolor="black", capsize=8, linewidth=1.5)

    ax.axhline(y=1.0, color="black", linestyle=":", linewidth=1, alpha=0.5)
    ax.text(2.3, 1.01, "Break-even", fontsize=9, color="black", alpha=0.6)

    # Annotate bars
    for i, (med, bar) in enumerate(zip(medians, bars)):
        pct = (med - 1.0) * 100
        sign = "+" if pct >= 0 else ""
        ax.text(i, med + yerr_high[i] + 0.03, f"{sign}{pct:.0f}%",
                ha="center", fontsize=11, fontweight="bold", color=colors[i])

    # Probability of recovery (value >= 1.0)
    prob_recover = [
        np.mean(spot_vals >= 1.0) * 100,
        np.mean(staker_vals >= 1.0) * 100,
        np.mean(lp_vals >= 1.0) * 100,
    ]
    for i, prob in enumerate(prob_recover):
        ax.text(i, 0.05, f"P(recover)={prob:.0f}%",
                ha="center", fontsize=9, color="white", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=11)
    ax.set_ylabel("Portfolio value (normalised)", fontsize=11)
    ax.set_title("Recovery Comparison After 50% Crash", fontsize=12)
    ax.set_ylim(0, max(q75) + 0.3)

    fig.suptitle("Stress Test: Market Crash Scenario", fontsize=15, y=1.02)
    fig.tight_layout()

    if save:
        out = os.path.join(os.path.dirname(__file__), "..", "paper", "figures",
                           "stress_test.pdf")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"Saved {out}")

    return fig


if __name__ == "__main__":
    plot()
    plt.show()
