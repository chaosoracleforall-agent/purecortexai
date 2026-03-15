"""
Network effects from cross-agent MCP composability.

Models:
  - N agents, each connecting to a random subset of others
  - Network value fitted against Metcalfe's law: V ~ k * n*(n-1)/2
  - Composability Score: CS_i = sum(calls * sqrt(unique_callers)) * quality

Outputs: ../paper/figures/network_value.pdf
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from config import SCENARIOS, SIMULATION_MONTHS, DAYS_PER_MONTH

# ── Matplotlib style ────────────────────────────────────────────────────
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("default")
plt.rcParams["font.family"] = "serif"

# ── Colours ──────────────────────────────────────────────────────────────
C_OBSERVED = "#1e88e5"
C_METCALFE = "#ef5350"
C_ZIPF = "#66bb6a"
C_GINI = "#ff9800"

RNG = np.random.default_rng(42)

# ── Network parameters ──────────────────────────────────────────────────
MAX_AGENTS = 500
CONNECTION_PROB_BASE = 0.05  # base probability of any two agents connecting
QUALITY_MEAN = 0.7
QUALITY_STD = 0.15


def build_network(n_agents: int):
    """Build a random agent network and compute edges + composability scores.

    Each agent pair connects with probability that decreases slightly as
    network grows (reflecting specialisation).
    """
    if n_agents < 2:
        return 0, np.array([0.0])

    # Connection probability scales inversely with sqrt(n) to model
    # the fact that agents specialise as the network grows
    p_connect = min(CONNECTION_PROB_BASE * (50 / max(n_agents, 50)) ** 0.3, 0.3)

    # Adjacency (upper triangle to avoid double-counting)
    adj = RNG.random((n_agents, n_agents)) < p_connect
    np.fill_diagonal(adj, False)
    adj = np.triu(adj)  # undirected
    total_edges = int(adj.sum())

    # Compute composability score for each agent
    # CS_i = sum_j(calls_ij * sqrt(unique_callers_j)) * quality_i
    quality = np.clip(RNG.normal(QUALITY_MEAN, QUALITY_STD, n_agents), 0.1, 1.0)

    # Simulate call counts: each connected pair has some call volume
    call_counts = adj * RNG.poisson(10, (n_agents, n_agents))

    # unique_callers for each agent j = number of agents that call j
    full_adj = adj + adj.T
    unique_callers = full_adj.sum(axis=0)  # in-degree

    scores = np.zeros(n_agents)
    for i in range(n_agents):
        connected_to = np.where(full_adj[i] > 0)[0]
        if len(connected_to) == 0:
            continue
        calls = np.array([call_counts[min(i, j), max(i, j)] for j in connected_to])
        callers = np.array([unique_callers[j] for j in connected_to])
        scores[i] = np.sum(calls * np.sqrt(np.maximum(callers, 1))) * quality[i]

    return total_edges, scores


def metcalfe_law(n, k):
    """Metcalfe: V = k * n*(n-1)/2."""
    return k * n * (n - 1) / 2


def compute_network_growth():
    """Compute network value as agents are added."""
    agent_counts = np.arange(5, MAX_AGENTS + 1, 5)
    edges = np.zeros(len(agent_counts))
    total_scores = np.zeros(len(agent_counts))
    all_score_distributions = []

    for i, n in enumerate(agent_counts):
        e, scores = build_network(n)
        edges[i] = e
        total_scores[i] = scores.sum()
        if n in [50, 150, 300, 500]:
            all_score_distributions.append((n, scores))

    return agent_counts, edges, total_scores, all_score_distributions


def gini_coefficient(values: np.ndarray) -> float:
    """Compute Gini coefficient of a distribution."""
    if len(values) == 0 or np.sum(values) == 0:
        return 0.0
    sorted_vals = np.sort(values)
    n = len(sorted_vals)
    index = np.arange(1, n + 1)
    return (2 * np.sum(index * sorted_vals) / (n * np.sum(sorted_vals))) - (n + 1) / n


def plot(save: bool = True):
    agent_counts, edges, total_scores, score_dists = compute_network_growth()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # ── Plot 1: Network value vs number of agents ────────────────────────
    ax = axes[0]

    # Normalise to "network value units"
    first_nonzero = total_scores[total_scores > 0][0] if np.any(total_scores > 0) else 1.0
    network_value = total_scores / first_nonzero  # relative to smallest nonzero

    ax.plot(agent_counts, network_value, "o-", color=C_OBSERVED,
            markersize=3, linewidth=1.5, label="Observed (composability)", zorder=3)

    # Fit Metcalfe's law
    try:
        popt, _ = curve_fit(metcalfe_law, agent_counts, network_value, p0=[0.01])
        k_fit = popt[0]
        metcalfe_fit = metcalfe_law(agent_counts, k_fit)
        ax.plot(agent_counts, metcalfe_fit, "--", color=C_METCALFE,
                linewidth=2, label=f"Metcalfe fit (k={k_fit:.4f})", zorder=2)
    except RuntimeError:
        pass

    # Reference: linear growth
    first_nv = network_value[network_value > 0][0] if np.any(network_value > 0) else 1.0
    first_ac = agent_counts[network_value > 0][0] if np.any(network_value > 0) else agent_counts[0]
    linear_ref = first_nv * (agent_counts / first_ac)
    ax.plot(agent_counts, linear_ref, ":", color="#bdbdbd", linewidth=1.5,
            label="Linear reference")

    ax.set_xlabel("Number of agents", fontsize=11)
    ax.set_ylabel("Network value (relative)", fontsize=11)
    ax.set_title("Superlinear Network Growth", fontsize=13)
    ax.legend(fontsize=9)

    # Annotate superlinearity
    mid_idx = len(agent_counts) // 2
    if network_value[mid_idx] > linear_ref[mid_idx] and linear_ref[-1] > 0:
        ratio = network_value[-1] / linear_ref[-1]
        ax.annotate(f"{ratio:.1f}x linear\nat {agent_counts[-1]} agents",
                    xy=(agent_counts[-1], network_value[-1]),
                    xytext=(agent_counts[-1] - 150, network_value[-1] * 0.7),
                    fontsize=10, color=C_OBSERVED,
                    arrowprops=dict(arrowstyle="->", color=C_OBSERVED, lw=1.2))

    # ── Plot 2: Composability reward distribution (Gini) ─────────────────
    ax = axes[1]

    if score_dists:
        for n_agents, scores in score_dists:
            sorted_scores = np.sort(scores)
            cumulative = np.cumsum(sorted_scores) / np.sum(sorted_scores)
            agents_frac = np.arange(1, len(sorted_scores) + 1) / len(sorted_scores)
            gini = gini_coefficient(scores)
            ax.plot(agents_frac, cumulative,
                    linewidth=2, label=f"N={n_agents} (Gini={gini:.2f})")

    # Perfect equality line
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, alpha=0.5, label="Perfect equality")

    ax.set_xlabel("Cumulative share of agents", fontsize=11)
    ax.set_ylabel("Cumulative share of composability rewards", fontsize=11)
    ax.set_title("Lorenz Curves: Reward Distribution", fontsize=13)
    ax.legend(fontsize=9, loc="upper left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")

    fig.suptitle("Cross-Agent MCP Composability: Network Effects", fontsize=15, y=1.02)
    fig.tight_layout()

    if save:
        out = os.path.join(os.path.dirname(__file__), "..", "paper", "figures",
                           "network_value.pdf")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"Saved {out}")

    return fig


if __name__ == "__main__":
    plot()
    plt.show()
