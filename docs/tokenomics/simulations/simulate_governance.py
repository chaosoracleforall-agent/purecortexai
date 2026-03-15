"""
Governance simulation for the Senator + Lawmaker model.

Models:
  - 1000 proposals with varying voter participation rates
  - veCORTEX distribution follows a power-law (Gini ~0.6)
  - Delegation scenarios affecting voting power concentration

Plots:
  1. Proposal approval rate vs quorum requirement by proposal type
  2. Voting power Gini coefficient under delegation scenarios
  3. Time-to-quorum under low/medium/high participation

Outputs: ../paper/figures/governance.pdf
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from config import PROPOSAL_TYPES, VE_MAX_LOCK_DAYS

# ── Matplotlib style ────────────────────────────────────────────────────
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("default")
plt.rcParams["font.family"] = "serif"

# ── Simulation parameters ───────────────────────────────────────────────
N_PROPOSALS = 1000
N_VOTERS = 5000  # total veCORTEX holders
RNG = np.random.default_rng(42)

# ── Colours ──────────────────────────────────────────────────────────────
PROPOSAL_COLORS = ["#1e88e5", "#43a047", "#e53935", "#ff9800"]
DELEGATION_COLORS = ["#78909c", "#1e88e5", "#0d47a1"]


def generate_ve_distribution(n_voters: int, gini_target: float = 0.60) -> np.ndarray:
    """Generate power-law veCORTEX distribution with approximate target Gini.

    Uses Pareto distribution, tuning alpha to achieve desired Gini.
    Gini for Pareto = 1 / (2*alpha - 1), so alpha = (1 + 1/Gini) / 2
    """
    alpha = (1 + 1 / gini_target) / 2
    raw = RNG.pareto(alpha, n_voters) + 1.0
    # Normalise so total = 1.0 (fractional voting power)
    return raw / raw.sum()


def simulate_proposal_approval(ve_dist: np.ndarray, quorum: float,
                                threshold: float, participation_rate: float,
                                n_proposals: int = N_PROPOSALS) -> float:
    """Simulate n_proposals and return approval rate.

    Each proposal: random subset of voters participate, each votes yes/no
    with probability weighted by a random "proposal quality" factor.
    """
    approvals = 0
    for _ in range(n_proposals):
        # Determine participating voters
        participating = RNG.random(len(ve_dist)) < participation_rate
        participation_weight = ve_dist[participating].sum()

        if participation_weight < quorum:
            continue  # quorum not met

        # Each voter votes yes with probability based on proposal quality
        # Quality drawn from Beta(3, 2) — slight lean toward approval
        quality = RNG.beta(3, 2)
        votes = RNG.random(participating.sum()) < quality
        yes_weight = ve_dist[participating][votes].sum()

        if yes_weight / participation_weight >= threshold:
            approvals += 1

    return approvals / n_proposals


def apply_delegation(ve_dist: np.ndarray, delegation_frac: float,
                     n_delegates: int) -> np.ndarray:
    """Simulate delegation: a fraction of holders delegate to top N holders."""
    delegated = ve_dist.copy()
    # Identify top delegates
    top_idx = np.argsort(delegated)[-n_delegates:]
    # Each non-top holder delegates with given probability
    for i in range(len(delegated)):
        if i not in top_idx and RNG.random() < delegation_frac:
            # Delegate to a random top holder
            delegate = RNG.choice(top_idx)
            delegated[delegate] += delegated[i]
            delegated[i] = 0.0
    return delegated


def gini_coefficient(values: np.ndarray) -> float:
    """Compute Gini coefficient."""
    if len(values) == 0 or np.sum(values) == 0:
        return 0.0
    sorted_vals = np.sort(values)
    n = len(sorted_vals)
    index = np.arange(1, n + 1)
    return (2 * np.sum(index * sorted_vals) / (n * np.sum(sorted_vals))) - (n + 1) / n


def simulate_time_to_quorum(ve_dist: np.ndarray, quorum: float,
                             participation_rate: float,
                             n_trials: int = 500) -> np.ndarray:
    """Simulate time-to-quorum (in hours) for proposals.

    Model: voters arrive as a Poisson process; each voter brings their
    veCORTEX weight. Time until cumulative weight >= quorum.
    """
    hourly_arrival_rate = len(ve_dist) * participation_rate / 72  # spread over 72h
    times = []

    for _ in range(n_trials):
        cumulative_weight = 0.0
        hours = 0.0

        while cumulative_weight < quorum:
            # Time until next voter arrives
            dt = RNG.exponential(1.0 / max(hourly_arrival_rate, 0.01))
            hours += dt

            if hours > 168:  # cap at 1 week
                hours = 168
                break

            # Random voter arrives
            voter = RNG.choice(len(ve_dist))
            cumulative_weight += ve_dist[voter]

        times.append(hours)

    return np.array(times)


def plot(save: bool = True):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

    ve_dist = generate_ve_distribution(N_VOTERS, gini_target=0.60)

    # ── Plot 1: Approval rate vs quorum for each proposal type ───────────
    ax = axes[0]
    quorum_range = np.linspace(0.02, 0.40, 30)
    participation_rates = [0.15, 0.30, 0.50]  # low, medium, high

    for j, pt in enumerate(PROPOSAL_TYPES):
        # Use medium participation
        approval_rates = []
        for q in quorum_range:
            rate = simulate_proposal_approval(ve_dist, q, pt.threshold,
                                               participation_rates[1], n_proposals=200)
            approval_rates.append(rate)

        ax.plot(quorum_range * 100, approval_rates,
                color=PROPOSAL_COLORS[j], linewidth=2,
                label=f"{pt.name}\n(thresh={pt.threshold:.0%})")

        # Mark actual quorum
        ax.axvline(x=pt.quorum * 100, color=PROPOSAL_COLORS[j],
                   linestyle=":", linewidth=1, alpha=0.6)

    ax.set_xlabel("Quorum requirement (%)", fontsize=11)
    ax.set_ylabel("Proposal approval rate", fontsize=11)
    ax.set_title("Approval Rate vs Quorum", fontsize=13)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 1.05)

    # ── Plot 2: Gini under delegation scenarios ─────────────────────────
    ax = axes[1]
    delegation_scenarios = [
        ("No delegation", 0.0, 0),
        ("Moderate (30% delegate to top 50)", 0.30, 50),
        ("Heavy (60% delegate to top 20)", 0.60, 20),
    ]

    gini_values = []
    labels = []

    for name, frac, n_del in delegation_scenarios:
        if frac == 0:
            dist = ve_dist.copy()
        else:
            dist = apply_delegation(ve_dist, frac, n_del)
        gini = gini_coefficient(dist)
        gini_values.append(gini)
        labels.append(name)

    bars = ax.barh(range(len(labels)), gini_values, color=DELEGATION_COLORS,
                   height=0.5, edgecolor="white")

    for i, (bar, g) in enumerate(zip(bars, gini_values)):
        ax.text(g + 0.01, i, f"{g:.3f}", va="center", fontsize=11, fontweight="bold",
                color=DELEGATION_COLORS[i])

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Gini coefficient", fontsize=11)
    ax.set_title("Voting Power Concentration", fontsize=13)
    ax.set_xlim(0, 1.0)

    # Annotate healthy range
    ax.axvspan(0.4, 0.65, alpha=0.08, color="green")
    ax.text(0.52, len(labels) - 0.5, "Healthy\nrange", fontsize=8, color="green",
            ha="center", alpha=0.7)

    # ── Plot 3: Time-to-quorum ───────────────────────────────────────────
    ax = axes[2]
    participation_labels = ["Low (15%)", "Medium (30%)", "High (50%)"]
    participation_colors = ["#90caf9", "#1e88e5", "#0d47a1"]

    # Use the "Parameter Change" proposal type (quorum=10%)
    quorum = PROPOSAL_TYPES[0].quorum
    bp_data = []

    for rate, label in zip(participation_rates, participation_labels):
        times = simulate_time_to_quorum(ve_dist, quorum, rate, n_trials=300)
        bp_data.append(times)

    bp = ax.boxplot(bp_data, labels=participation_labels, patch_artist=True,
                    widths=0.5, showfliers=False,
                    medianprops=dict(color="black", linewidth=2))

    for patch, color in zip(bp["boxes"], participation_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Add median annotations
    for i, data in enumerate(bp_data):
        med = np.median(data)
        ax.text(i + 1, med + 1, f"{med:.1f}h", ha="center", fontsize=9,
                fontweight="bold", color=participation_colors[i])

    ax.set_ylabel("Hours to reach quorum", fontsize=11)
    ax.set_title(f"Time-to-Quorum\n(Parameter Change, quorum={quorum:.0%})", fontsize=12)

    fig.suptitle("Governance Dynamics: Senator + Lawmaker Model", fontsize=15, y=1.03)
    fig.tight_layout()

    if save:
        out = os.path.join(os.path.dirname(__file__), "..", "paper", "figures",
                           "governance.pdf")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"Saved {out}")

    return fig


if __name__ == "__main__":
    plot()
    plt.show()
