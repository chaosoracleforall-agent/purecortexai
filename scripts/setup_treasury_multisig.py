#!/usr/bin/env python3
"""
PURECORTEX Treasury Multisig Setup Script.

Creates a 2-of-3 Algorand multisig address for treasury operations using
three constituent addresses: the deployer wallet, a cold storage wallet,
and a hardware wallet.

The resulting multisig address can be used as the operations wallet in
deployment.mainnet.json, requiring any 2 of the 3 signers to authorize
treasury withdrawals and other high-value operations.

Usage:
    # Display multisig address only (dry-run is the default)
    python scripts/setup_treasury_multisig.py \\
        --deployer  DEPLOYER_ADDRESS_HERE \\
        --cold      COLD_WALLET_ADDRESS_HERE \\
        --hardware  HARDWARE_WALLET_ADDRESS_HERE

    # Update deployment.mainnet.json with the new multisig as operations wallet
    python scripts/setup_treasury_multisig.py \\
        --deployer  DEPLOYER_ADDRESS_HERE \\
        --cold      COLD_WALLET_ADDRESS_HERE \\
        --hardware  HARDWARE_WALLET_ADDRESS_HERE \\
        --update-manifest

    # Explicit dry-run (same as default, prints info without writing anything)
    python scripts/setup_treasury_multisig.py \\
        --deployer  DEPLOYER_ADDRESS_HERE \\
        --cold      COLD_WALLET_ADDRESS_HERE \\
        --hardware  HARDWARE_WALLET_ADDRESS_HERE \\
        --dry-run

Notes:
    - The multisig version is 1 (the only version supported by Algorand).
    - The threshold is 2 (any 2 of 3 signers must approve a transaction).
    - Address order matters: the multisig address is deterministic based on
      the ordered list of constituent addresses. This script always orders
      them as [deployer, cold, hardware].
    - To sign a multisig transaction, use algosdk.transaction.MultisigTransaction.
      Each signer appends their signature independently, and the transaction
      can be broadcast once the threshold (2) is met.

Security:
    - This script does NOT require any private keys or mnemonics.
    - It only operates on public addresses.
    - No transactions are created or broadcast.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from algosdk import encoding
from algosdk.transaction import Multisig


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "deployment.mainnet.json"

MULTISIG_VERSION = 1
MULTISIG_THRESHOLD = 2


def validate_algorand_address(address: str, label: str) -> str:
    """Validate that a string is a well-formed Algorand address."""
    try:
        encoding.decode_address(address)
    except Exception as e:
        print(f"ERROR: Invalid {label} address: {address}", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        sys.exit(1)
    return address


def create_multisig(deployer: str, cold: str, hardware: str) -> Multisig:
    """
    Create a 2-of-3 Algorand Multisig from three addresses.

    The address list order is fixed as [deployer, cold, hardware] to ensure
    deterministic multisig address generation. Changing the order would
    produce a different multisig address.

    Args:
        deployer: The deployer/hot wallet Algorand address.
        cold: The cold storage Algorand address.
        hardware: The hardware wallet Algorand address.

    Returns:
        An algosdk.transaction.Multisig object.
    """
    msig = Multisig(
        version=MULTISIG_VERSION,
        threshold=MULTISIG_THRESHOLD,
        addresses=[deployer, cold, hardware],
    )
    return msig


def update_manifest(multisig_address: str, dry_run: bool) -> None:
    """
    Update deployment.mainnet.json with the multisig as the operations wallet.

    Reads the existing manifest, updates wallets.operations and adds a
    wallets.operationsMultisig metadata block, then writes atomically
    (temp file + rename).

    Args:
        multisig_address: The Algorand multisig address string.
        dry_run: If True, print what would change but do not write.
    """
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    old_operations = manifest.get("wallets", {}).get("operations", "(not set)")

    manifest.setdefault("wallets", {})
    manifest["wallets"]["operations"] = multisig_address
    manifest["wallets"]["operationsMultisig"] = {
        "type": "multisig",
        "version": MULTISIG_VERSION,
        "threshold": MULTISIG_THRESHOLD,
        "note": "2-of-3 multisig: deployer + cold + hardware",
    }

    if dry_run:
        print("\n[DRY RUN] Would update deployment.mainnet.json:")
        print(f"  wallets.operations: {old_operations} -> {multisig_address}")
        print("  wallets.operationsMultisig: (new metadata block)")
        return

    # Atomic write: write to temp file in the same directory, then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=MANIFEST_PATH.parent, suffix=".tmp", prefix="deployment.mainnet."
    )
    try:
        with open(fd, "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        Path(tmp_path).replace(MANIFEST_PATH)
        print(f"\nUpdated {MANIFEST_PATH}")
        print(f"  wallets.operations: {old_operations} -> {multisig_address}")
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a 2-of-3 Algorand multisig address for PURECORTEX treasury operations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Just display the multisig address
  python scripts/setup_treasury_multisig.py \\
      --deployer ADDR1 --cold ADDR2 --hardware ADDR3

  # Display and update deployment.mainnet.json
  python scripts/setup_treasury_multisig.py \\
      --deployer ADDR1 --cold ADDR2 --hardware ADDR3 \\
      --update-manifest
        """,
    )
    parser.add_argument(
        "--deployer",
        required=True,
        help="Algorand address of the deployer/hot wallet",
    )
    parser.add_argument(
        "--cold",
        required=True,
        help="Algorand address of the cold storage wallet",
    )
    parser.add_argument(
        "--hardware",
        required=True,
        help="Algorand address of the hardware wallet",
    )
    parser.add_argument(
        "--update-manifest",
        action="store_true",
        default=False,
        help="Update deployment.mainnet.json with the multisig as the operations wallet",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print what would happen without making any changes (default behavior unless --update-manifest is given)",
    )

    args = parser.parse_args()

    # Validate all three addresses
    deployer = validate_algorand_address(args.deployer, "deployer")
    cold = validate_algorand_address(args.cold, "cold")
    hardware = validate_algorand_address(args.hardware, "hardware")

    # Check for duplicate addresses
    if len({deployer, cold, hardware}) < 3:
        print("ERROR: All three addresses must be unique.", file=sys.stderr)
        sys.exit(1)

    # Create the multisig
    msig = create_multisig(deployer, cold, hardware)
    multisig_address = msig.address()

    # Display results
    print("=" * 70)
    print("PURECORTEX Treasury Multisig (2-of-3)")
    print("=" * 70)
    print()
    print(f"  Multisig Address:  {multisig_address}")
    print()
    print("  Signers:")
    print(f"    1. Deployer:  {deployer}")
    print(f"    2. Cold:      {cold}")
    print(f"    3. Hardware:  {hardware}")
    print()
    print(f"  Version:    {MULTISIG_VERSION}")
    print(f"  Threshold:  {MULTISIG_THRESHOLD} of 3")
    print()
    print("  Any 2 of the 3 signers must approve each transaction.")
    print("=" * 70)

    # Update manifest if requested
    if args.update_manifest:
        update_manifest(multisig_address, dry_run=args.dry_run)
    elif args.dry_run:
        print("\n[DRY RUN] No changes made. Use --update-manifest to write to deployment.mainnet.json.")


if __name__ == "__main__":
    main()
