"""
Bonding curve comparison: linear, quadratic, and exponential price discovery.

Plots:
  1. Price vs Supply for all 3 curves
  2. Total cost to buy N tokens from supply=0
  3. Price impact of a 10,000-token buy at various supply levels

Outputs: ../paper/figures/bonding_curve_comparison.pdf
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from config import BASE_PRICE, SLOPE

# ── Matplotlib style ────────────────────────────────────────────────────
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("default")
plt.rcParams["font.family"] = "serif"

# ── Curve parameters ────────────────────────────────────────────────────
B = BASE_PRICE          # base price
S_LINEAR = 500          # linear slope
S_QUAD = SLOPE          # quadratic slope (from config)
K_EXP = 0.001           # exponential growth rate

# ── Colours ──────────────────────────────────────────────────────────────
C_LINEAR = "#78909c"
C_QUAD = "#1e88e5"
C_EXP = "#ef5350"

MAX_SUPPLY = 50_000  # tokens for plotting range


def price_linear(q):
    return B + S_LINEAR * q


def price_quadratic(q):
    return B + S_QUAD * q


def price_exponential(q):
    return B * np.exp(K_EXP * q)


def cost_linear(n):
    """Total cost to buy n tokens starting from supply=0: integral of P(q) dq."""
    return B * n + S_LINEAR * n**2 / 2


def cost_quadratic(n):
    return B * n + S_QUAD * n**2 / 2


def cost_exponential(n):
    return (B / K_EXP) * (np.exp(K_EXP * n) - 1)


def price_impact(price_fn, current_supply, buy_amount):
    """Percentage price increase from buying buy_amount tokens at current_supply."""
    p_before = price_fn(current_supply)
    p_after = price_fn(current_supply + buy_amount)
    return (p_after - p_before) / p_before * 100


def plot(save: bool = True):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    q = np.linspace(0, MAX_SUPPLY, 1000)

    # ── Plot 1: Price vs Supply ──────────────────────────────────────────
    ax = axes[0]
    ax.plot(q, price_linear(q), label="Linear (S=500)", color=C_LINEAR, linewidth=2)
    ax.plot(q, price_quadratic(q), label="Quadratic (S=1000)", color=C_QUAD, linewidth=2)
    ax.plot(q, price_exponential(q), label="Exponential (k=0.001)", color=C_EXP, linewidth=2)
    ax.set_xlabel("Cumulative Supply (tokens)", fontsize=11)
    ax.set_ylabel("Price (micro-ALGO)", fontsize=11)
    ax.set_title("Price vs Supply", fontsize=13)
    ax.legend(fontsize=9)
    ax.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))

    # ── Plot 2: Total cost to buy N tokens ───────────────────────────────
    ax = axes[1]
    n = np.linspace(0, MAX_SUPPLY, 1000)
    ax.plot(n, cost_linear(n), label="Linear", color=C_LINEAR, linewidth=2)
    ax.plot(n, cost_quadratic(n), label="Quadratic", color=C_QUAD, linewidth=2)
    ax.plot(n, cost_exponential(n), label="Exponential", color=C_EXP, linewidth=2)
    ax.set_xlabel("Tokens purchased (from supply = 0)", fontsize=11)
    ax.set_ylabel("Total cost (micro-ALGO)", fontsize=11)
    ax.set_title("Cost to Accumulate", fontsize=13)
    ax.legend(fontsize=9)
    ax.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))

    # ── Plot 3: Price impact at various supply levels ────────────────────
    ax = axes[2]
    buy_amount = 10_000
    supply_levels = np.linspace(1000, MAX_SUPPLY, 200)
    impact_lin = [price_impact(price_linear, s, buy_amount) for s in supply_levels]
    impact_quad = [price_impact(price_quadratic, s, buy_amount) for s in supply_levels]
    impact_exp = [price_impact(price_exponential, s, buy_amount) for s in supply_levels]

    ax.plot(supply_levels, impact_lin, label="Linear", color=C_LINEAR, linewidth=2)
    ax.plot(supply_levels, impact_quad, label="Quadratic", color=C_QUAD, linewidth=2)
    ax.plot(supply_levels, impact_exp, label="Exponential", color=C_EXP, linewidth=2)
    ax.set_xlabel("Current supply level (tokens)", fontsize=11)
    ax.set_ylabel("Price impact (%)", fontsize=11)
    ax.set_title(f"Impact of {buy_amount:,}-Token Buy", fontsize=13)
    ax.legend(fontsize=9)

    fig.suptitle("Bonding Curve Comparison", fontsize=15, y=1.02)
    fig.tight_layout()

    if save:
        out = os.path.join(os.path.dirname(__file__), "..", "paper", "figures",
                           "bonding_curve_comparison.pdf")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"Saved {out}")

    return fig


if __name__ == "__main__":
    plot()
    plt.show()
