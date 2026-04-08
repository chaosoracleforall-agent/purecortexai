#!/usr/bin/env python3
"""
PURECORTEX MainNet Deployment Script.

Deploys all protocol contracts to Algorand MainNet in the correct dependency
order, bootstraps the CORTEX token, and writes the canonical deployment
manifest to deployment.mainnet.json.

Usage:
    # Preferred: mnemonic from env var (set via `read -s` to avoid shell history)
    PURECORTEX_DEPLOYER_MNEMONIC="..." python scripts/deploy_mainnet.py [--dry-run]

    # Alternative: mnemonic from a file with restricted permissions (mode 600)
    python scripts/deploy_mainnet.py --mnemonic-file ~/.purecortex/deployer.key

    # Alternative: pull from GCP Secret Manager
    python scripts/deploy_mainnet.py --mnemonic-secret MAINNET_PURECORTEX_DEPLOYER_MNEMONIC

Safety:
    - Requires explicit --confirm flag for real mainnet deployment
    - Mnemonic is NEVER accepted as a CLI argument (visible in process list)
    - Prints every transaction ID before broadcasting
    - Writes manifest atomically (temp file + rename)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import math

from algosdk import mnemonic, account
from algosdk import abi
from algosdk.atomic_transaction_composer import AtomicTransactionComposer, AccountTransactionSigner
from algosdk.v2client import algod

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "deployment.mainnet.json"

MAINNET_ALGOD_URL = "https://mainnet-api.4160.nodely.dev"
MAINNET_ALGOD_TOKEN = ""

CONTRACT_ARTIFACTS = ROOT / "contracts" / "smart_contracts" / "artifacts"


def _resolve_artifact_paths(name: str) -> tuple[Path, Path]:
    artifact_dir = CONTRACT_ARTIFACTS / name
    if not artifact_dir.exists():
        raise FileNotFoundError(f"Artifact directory missing for {name}: {artifact_dir}")

    approval_matches = sorted(artifact_dir.glob("*.approval.teal"))
    clear_matches = sorted(artifact_dir.glob("*.clear.teal"))
    if not approval_matches or not clear_matches:
        raise FileNotFoundError(
            f"Missing compiled TEAL for {name} in {artifact_dir}. "
            "Expected *.approval.teal and *.clear.teal files."
        )

    return approval_matches[0], clear_matches[0]


def _load_mnemonic(
    *,
    mnemonic_file: str | None = None,
    mnemonic_secret: str | None = None,
) -> str:
    """Load deployer mnemonic from env var, file, or GCP Secret Manager.

    Never accepts the mnemonic as a CLI argument — command-line args are
    visible in process listings and persisted in shell history.
    """
    env_val = os.environ.get("PURECORTEX_DEPLOYER_MNEMONIC", "").strip()
    if env_val:
        return env_val

    if mnemonic_file:
        p = Path(mnemonic_file).expanduser()
        if not p.exists():
            print(f"ERROR: Mnemonic file not found: {p}", file=sys.stderr)
            sys.exit(1)
        mode = p.stat().st_mode & 0o777
        if mode & 0o077:
            print(
                f"ERROR: Mnemonic file {p} has insecure permissions {oct(mode)}. "
                f"Run: chmod 600 {p}",
                file=sys.stderr,
            )
            sys.exit(1)
        return p.read_text().strip()

    if mnemonic_secret:
        try:
            result = subprocess.check_output(
                [
                    "gcloud", "secrets", "versions", "access", "latest",
                    f"--secret={mnemonic_secret}",
                    f"--project={os.environ.get('PURECORTEX_GCP_PROJECT', 'purecortexai')}",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            return result.strip()
        except subprocess.CalledProcessError:
            print(f"ERROR: Could not read secret {mnemonic_secret} from Secret Manager", file=sys.stderr)
            sys.exit(1)

    print(
        "ERROR: No deployer mnemonic provided.\n"
        "  Set PURECORTEX_DEPLOYER_MNEMONIC env var, or use --mnemonic-file, or --mnemonic-secret.\n"
        "  The mnemonic is never accepted as a CLI argument for security reasons.",
        file=sys.stderr,
    )
    sys.exit(1)


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
    approval_path, clear_path = _resolve_artifact_paths(name)

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
    extra_pages = max(0, math.ceil(max(0, len(approval_program) - 2048) / 2048))

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
        extra_pages=extra_pages,
    )

    signed = txn.sign(private_key)
    tx_id = client.send_transaction(signed)
    print(f"    TX: {tx_id}")

    result = transaction.wait_for_confirmation(client, tx_id, 10)
    app_id = result["application-index"]
    print(f"    App ID: {app_id}")
    return app_id


def bootstrap_cortex_token(
    client: algod.AlgodClient,
    private_key: str,
    factory_app_id: int,
    *,
    dry_run: bool = False,
) -> int:
    if factory_app_id <= 0:
        raise ValueError("Cannot bootstrap protocol before deploying AgentFactory.")

    if dry_run:
        print("  [DRY RUN] Would call AgentFactory.bootstrap_protocol()")
        return 0

    method = abi.Method.from_signature("bootstrap_protocol()uint64")
    sender = account.address_from_private_key(private_key)
    signer = AccountTransactionSigner(private_key)

    from algosdk import transaction
    from algosdk.logic import get_application_address

    factory_app_address = get_application_address(factory_app_id)
    factory_balance = client.account_info(factory_app_address).get("amount", 0)
    required_factory_balance = 500_000
    if factory_balance < required_factory_balance:
        top_up = required_factory_balance - factory_balance
        fund_sp = client.suggested_params()
        fund_sp.flat_fee = True
        fund_sp.fee = 1_000
        fund_txn = transaction.PaymentTxn(
            sender=sender,
            sp=fund_sp,
            receiver=factory_app_address,
            amt=top_up,
        )
        fund_tx_id = client.send_transaction(fund_txn.sign(private_key))
        transaction.wait_for_confirmation(client, fund_tx_id, 10)
        print(f"    Funded factory app account: {fund_tx_id} (+{top_up} microALGO)")

    sp = client.suggested_params()
    # bootstrap_protocol performs inner transactions (ASA creation), so the outer
    # app call must prepay enough fee to satisfy inner txn minimums.
    sp.flat_fee = True
    sp.fee = 4_000

    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=factory_app_id,
        method=method,
        sender=sender,
        sp=sp,
        signer=signer,
        method_args=[],
    )

    result = atc.execute(client, 8)
    tx_id = result.tx_ids[-1]
    cortex_asset_id = int(result.abi_results[0].return_value)
    print(f"    TX: {tx_id}")
    print(f"    CORTEX Asset ID: {cortex_asset_id}")
    return cortex_asset_id


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
    parser.add_argument(
        "--mnemonic-file",
        help="Path to a file containing the deployer mnemonic (must be mode 600)",
    )
    parser.add_argument(
        "--mnemonic-secret",
        help="GCP Secret Manager secret name containing the deployer mnemonic",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate without broadcasting")
    parser.add_argument("--confirm", action="store_true", help="Required for real mainnet deployment")
    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        print("ERROR: Mainnet deployment requires --confirm flag.")
        print("       Run with --dry-run first to validate.")
        sys.exit(1)

    mnemonic_phrase = _load_mnemonic(
        mnemonic_file=args.mnemonic_file,
        mnemonic_secret=args.mnemonic_secret,
    )
    private_key, address = get_deployer(mnemonic_phrase)
    mnemonic_phrase = "0" * len(mnemonic_phrase)
    del mnemonic_phrase
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
    creator_vesting_id = deploy_contract(client, private_key, "creator_vesting", dry_run=args.dry_run)

    print("\n--- Phase 2: Protocol Bootstrap ---\n")

    print("  Bootstrapping CORTEX token...")
    cortex_asset_id = bootstrap_cortex_token(
        client,
        private_key,
        factory_id or 0,
        dry_run=args.dry_run,
    )

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
            "creatorVesting": {
                "appId": creator_vesting_id or 0,
                "status": "active" if creator_vesting_id else "pending_deployment",
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
        print(f"    CreatorVesting App ID: {creator_vesting_id}")
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
