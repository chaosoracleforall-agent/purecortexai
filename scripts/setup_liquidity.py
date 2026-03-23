#!/usr/bin/env python3
"""
PURECORTEX DEX Liquidity Pool Setup.

Seeds initial CORTEX/ALGO liquidity on Tinyman and Pact after mainnet
deployment. Uses the 15% liquidity allocation from the token distribution.

Usage:
    python scripts/setup_liquidity.py --deployer-mnemonic "..." \
        --cortex-asset-id 12345 \
        --cortex-amount 750000000000000 \
        --algo-amount 10000000000 \
        [--dry-run]

The 15% liquidity allocation (1.5 quadrillion CORTEX) is split:
    - 60% -> Tinyman CORTEX/ALGO pool
    - 40% -> Pact CORTEX/ALGO pool

LP tokens are sent to a 10-year timelock address (or held by the deployer
for manual locking if the timelock contract is not yet deployed).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from algosdk import mnemonic, account
from algosdk.v2client import algod

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "deployment.mainnet.json"

MAINNET_ALGOD_URL = "https://mainnet-api.4160.nodely.dev"

TINYMAN_V2_APP_ID = 1002541853
PACT_APP_ID = 620995314

TINYMAN_SPLIT = 0.60
PACT_SPLIT = 0.40


def get_deployer(mnemonic_phrase: str) -> tuple[str, str]:
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    address = account.address_from_private_key(private_key)
    return private_key, address


def main():
    parser = argparse.ArgumentParser(description="Setup CORTEX/ALGO DEX liquidity")
    parser.add_argument("--deployer-mnemonic", required=True)
    parser.add_argument("--cortex-asset-id", type=int, required=True)
    parser.add_argument("--cortex-amount", type=int, required=True,
                        help="Total CORTEX (in micro-units) to add as liquidity")
    parser.add_argument("--algo-amount", type=int, required=True,
                        help="Total ALGO (in microALGO) to add as liquidity")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        print("ERROR: Mainnet liquidity setup requires --confirm flag.")
        sys.exit(1)

    private_key, address = get_deployer(args.deployer_mnemonic)
    client = algod.AlgodClient("", MAINNET_ALGOD_URL)

    tinyman_cortex = int(args.cortex_amount * TINYMAN_SPLIT)
    tinyman_algo = int(args.algo_amount * TINYMAN_SPLIT)
    pact_cortex = args.cortex_amount - tinyman_cortex
    pact_algo = args.algo_amount - tinyman_algo

    print(f"Deployer:     {address}")
    print(f"CORTEX ASA:   {args.cortex_asset_id}")
    print(f"Mode:         {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    print(f"--- Tinyman V2 ({TINYMAN_SPLIT*100:.0f}%) ---")
    print(f"  CORTEX: {tinyman_cortex:>25,} micro-units ({tinyman_cortex/1e6:,.0f} tokens)")
    print(f"  ALGO:   {tinyman_algo:>25,} microALGO ({tinyman_algo/1e6:,.2f} ALGO)")
    print()
    print(f"--- Pact ({PACT_SPLIT*100:.0f}%) ---")
    print(f"  CORTEX: {pact_cortex:>25,} micro-units ({pact_cortex/1e6:,.0f} tokens)")
    print(f"  ALGO:   {pact_algo:>25,} microALGO ({pact_algo/1e6:,.2f} ALGO)")
    print()

    if args.dry_run:
        print("[DRY RUN] No transactions sent.")
        print()
        print("To create pools manually:")
        print(f"  1. Go to https://app.tinyman.org/#/pool/add-liquidity")
        print(f"     Asset 1: ALGO, Asset 2: {args.cortex_asset_id}")
        print(f"     Add {tinyman_cortex/1e6:,.0f} CORTEX + {tinyman_algo/1e6:,.2f} ALGO")
        print()
        print(f"  2. Go to https://app.pact.fi/add-liquidity")
        print(f"     Asset 1: ALGO, Asset 2: {args.cortex_asset_id}")
        print(f"     Add {pact_cortex/1e6:,.0f} CORTEX + {pact_algo/1e6:,.2f} ALGO")
        print()
        print("After pool creation:")
        print("  - Update deployment.mainnet.json with pool IDs")
        print("  - Lock LP tokens for 10 years (per tokenomics)")
        print("  - Register on Vestige.fi for tracking")
        return

    print("Automated DEX pool creation via SDK:")
    print("  Tinyman: Use tinyman-py-sdk to bootstrap_pool + add_initial_liquidity")
    print("  Pact:    Use pact-fi-sdk to create_pool + add_liquidity")
    print()
    print("Implementation requires the Tinyman and Pact Python SDKs.")
    print("Install: pip install tinyman-py-sdk pactsdk")
    print()

    # TODO: Implement automated pool creation with:
    # from tinyman.v2.client import TinymanV2Client
    # from pactsdk import PactClient
    # This requires the SDKs and careful transaction composition.
    # For launch, manual pool creation via the DEX UIs is the safest path.

    print("For the March 31 launch, use the manual process above.")
    print("Automated pool creation can be added post-launch.")

    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text())
        manifest["dex"]["tinyman"]["status"] = "pending_manual_setup"
        manifest["dex"]["pact"]["status"] = "pending_manual_setup"
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"\nUpdated {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
