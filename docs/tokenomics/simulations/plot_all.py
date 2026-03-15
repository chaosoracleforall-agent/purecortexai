"""
Master script: run all PURECORTEX tokenomics simulations and generate all figures.

Usage:
    python plot_all.py           # generate all figures
    python plot_all.py --show    # generate and display interactively
"""

import sys
import time

import simulate_supply
import simulate_bonding_curve
import simulate_staking_yield
import simulate_fees
import simulate_stress
import simulate_composability
import simulate_governance
import simulate_sensitivity


SIMULATIONS = [
    ("Supply trajectory",    simulate_supply),
    ("Bonding curve",        simulate_bonding_curve),
    ("Staking yield",        simulate_staking_yield),
    ("Fee revenue",          simulate_fees),
    ("Stress test",          simulate_stress),
    ("Composability",        simulate_composability),
    ("Governance",           simulate_governance),
    ("Sensitivity",          simulate_sensitivity),
]


def run_all(show: bool = False):
    """Run all simulations sequentially and save figures."""
    import matplotlib.pyplot as plt

    total_start = time.time()
    print("=" * 60)
    print("PURECORTEX Tokenomics Simulation Suite")
    print("=" * 60)

    for name, module in SIMULATIONS:
        start = time.time()
        print(f"\n{'─' * 40}")
        print(f"Running: {name}...")
        try:
            module.plot(save=True)
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  FAILED after {elapsed:.1f}s: {e}")

    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 60}")
    print(f"All simulations complete in {total_elapsed:.1f}s")
    print(f"Figures saved to ../paper/figures/")
    print("=" * 60)

    if show:
        plt.show()


if __name__ == "__main__":
    show = "--show" in sys.argv
    run_all(show=show)
