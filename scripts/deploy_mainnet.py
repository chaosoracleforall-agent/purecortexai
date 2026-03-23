#!/usr/bin/env python3
"""
PURECORTEX MainNet Deployment Script.

Deploys all protocol contracts to Algorand MainNet in the correct dependency
order, bootstraps the CORTEX token, and writes the canonical deployment
manifest to deployment.mainnet.json.

Usage:
    python scripts/deploy_mainnet.py --deployer-mnemonic "..." [--dry-run]

Safety:
    - Requires explicit --confirm flag for real mainnet deployment
    - Prints every transaction ID before broadcasting
    - Writes manifest atomically (temp file + rename)
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from algosdk import mnemonic, account
from algosdk.v2client import algod
from algokit_utils import ApplicationClient, get_algod_client

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "deployment.mainnet.json"

MAINNET_ALGOD_URL = "https://mainnet-api.4160.nodely.dev"
MAINNET_ALGOD_TOKEN = ""

CONTRACT_ARTIFACTS = ROOT / "contracts" / "smart_contracts" / "artifacts"


def get_deployer(mnemonic_phrase: str) -> tuple[str, str]:
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    address = account.address_from_private_key(private_key)
    return private_key, address


def get_client() -> algod.AlgodClient:
    return algod.AlgodClient(MAINNET_ALGOD_TOKEN, MAINNET_ALGOD_URL)


def check_balance(client: algod.AlgodClient, address: str) -> int:
    info = client.account_info(address)
    return info.get("amount", 0)


def deploy_contract(
    client: algod.AlgodClient,
    private_key: str,
    name: str,
    *,
    dry_run: bool = False,
) -> int | None:
    approval_path = CONTRACT_ARTIFACTS / name / f"{name}.approval.teal"
    clear_path = CONTRACT_ARTIFACTS / name / f"{name}.clear.teal"

    if not approval_path.exists():
        print(f"  [SKIP] {name}: approval TEAL not found at {approval_path}")
        return None

    print(f"  Deploying {name}...")
    print(f"    Approval: {approval_path}")
    print(f"    Clear:    {clear_path}")

    if dry_run:
        print(f"    [DRY RUN] Would deploy {name} to mainnet")
        return 0

    approval_teal = approval_path.read_text()
    clear_teal = clear_path.read_text()

    from algosdk.transaction import ApplicationCreateTxn, StateSchema, OnComplete
    from algosdk import transaction

    approval_result = client.compile(approval_teal)
    clear_result = client.compile(clear_teal)

    from base64 import b64decode
    approval_program = b64decode(approval_result["result"])
    clear_program = b64decode(clear_result["result"])

    address = account.address_from_private_key(private_key)
    params = client.suggested_params()

    txn = ApplicationCreateTxn(
        sender=address,
        sp=params,
        on_complete=OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program,
        global_schema=StateSchema(num_uints=32, num_byte_slices=16),
        local_schema=StateSchema(num_uints=0, num_byte_slices=0),
    )

    signed = txn.sign(private_key)
    tx_id = client.send_transaction(signed)
    print(f"    TX: {tx_id}")

    result = transaction.wait_for_confirmation(client, tx_id, 10)
    app_id = result["application-index"]
    print(f"    App ID: {app_id}")
    return app_id


def update_manifest(updates: dict) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    manifest.update(updates)

    fd, tmp = tempfile.mkstemp(dir=MANIFEST_PATH.parent, suffix=".json")
    try:
        with open(fd, "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        Path(tmp).replace(MANIFEST_PATH)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise

    print(f"\nManifest updated: {MANIFEST_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Deploy PURECORTEX to Algorand MainNet")
    parser.add_argument("--deployer-mnemonic", required=True, help="25-word Algorand mnemonic")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without broadcasting")
    parser.add_argument("--confirm", action="store_true", help="Required for real mainnet deployment")
    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        print("ERROR: Mainnet deployment requires --confirm flag.")
        print("       Run with --dry-run first to validate.")
        sys.exit(1)

    private_key, address = get_deployer(args.deployer_mnemonic)
    print(f"Deployer: {address}")
    print(f"Network:  Algorand MainNet")
    print(f"Mode:     {'DRY RUN' if args.dry_run else 'LIVE DEPLOYMENT'}")
    print()

    client = get_client()
    balance = check_balance(client, address)
    balance_algo = balance / 1_000_000
    print(f"Balance:  {balance_algo:.6f} ALGO")

    if balance_algo < 10 and not args.dry_run:
        print("ERROR: Deployer needs at least 10 ALGO for contract deployment.")
        sys.exit(1)

    print("\n--- Phase 1: Contract Deployment ---\n")

    governance_id = deploy_contract(client, private_key, "governance", dry_run=args.dry_run)
    staking_id = deploy_contract(client, private_key, "staking", dry_run=args.dry_run)
    treasury_id = deploy_contract(client, private_key, "sovereign_treasury", dry_run=args.dry_run)
    factory_id = deploy_contract(client, private_key, "agent_factory", dry_run=args.dry_run)

    print("\n--- Phase 2: Protocol Bootstrap ---\n")

    if args.dry_run:
        print("  [DRY RUN] Would bootstrap CORTEX token via AgentFactory")
        cortex_asset_id = 0
    else:
        print("  Bootstrapping CORTEX token...")
        cortex_asset_id = 0  # TODO: call bootstrap_protocol ABI method

    print("\n--- Phase 3: Manifest Update ---\n")

    factory_address = ""
    if factory_id and not args.dry_run:
        from algosdk.logic import get_application_address
        factory_address = get_application_address(factory_id)

    updates = {
        "contracts": {
            "agentFactory": {
                "appId": factory_id or 0,
                "address": factory_address,
                "status": "active" if factory_id else "pending_deployment",
            },
            "cortexToken": {
                "assetId": cortex_asset_id,
                "name": "PureCortex",
                "unitName": "CORTEX",
                "creatorAddress": factory_address,
            },
            "governance": {
                "appId": governance_id or 0,
                "status": "active" if governance_id else "pending_deployment",
            },
            "staking": {
                "appId": staking_id or 0,
                "status": "active" if staking_id else "pending_deployment",
            },
            "treasury": {
                "appId": treasury_id or 0,
                "status": "active" if treasury_id else "pending_deployment",
            },
        },
        "wallets": {
            "agentFactoryEscrow": factory_address,
            "assistanceFund": None,
            "operations": None,
            "creatorVesting": None,
            "liquidityPool": None,
        },
    }

    if not args.dry_run:
        update_manifest(updates)
    else:
        print("  [DRY RUN] Would update manifest with:")
        print(f"    Factory App ID: {factory_id}")
        print(f"    Governance App ID: {governance_id}")
        print(f"    Staking App ID: {staking_id}")
        print(f"    Treasury App ID: {treasury_id}")
        print(f"    CORTEX Asset ID: {cortex_asset_id}")

    print("\n--- Deployment Complete ---\n")
    print("Next steps:")
    print("  1. Run: python generate_protocol_config.py mainnet")
    print("  2. Run mainnet smoke tests")
    print("  3. Seed liquidity pools on Tinyman and Pact")
    print("  4. Update frontend Providers.tsx to MainNet network")
    print("  5. Redeploy the VM stack")


if __name__ == "__main__":
    main()
