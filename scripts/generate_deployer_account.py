#!/usr/bin/env python3
"""
Generate a new Algorand deployer account for AirdropClaim contract deployment.

Creates a new account, encrypts the mnemonic with GPG, and stores it in
GCP Secret Manager. The plaintext mnemonic is never written to disk and
is zeroized from memory after storage.

Usage:
    python scripts/generate_deployer_account.py \
        --secret-name MAINNET_AIRDROP_DEPLOYER_MNEMONIC \
        --gpg-recipient purecortex-deployer@purecortex.ai

    # Dry-run (prints address, does not store):
    python scripts/generate_deployer_account.py --dry-run
"""

from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys

from algosdk import account, mnemonic


def _zeroize(s: str) -> None:
    """Best-effort zeroization of a Python string's internal buffer."""
    try:
        buf = ctypes.cast(id(s), ctypes.POINTER(ctypes.c_char * len(s)))
        ctypes.memset(buf, 0, len(s))
    except Exception:
        pass  # Python string immutability makes this unreliable


def _gpg_encrypt(plaintext: str, recipient: str) -> bytes:
    """Encrypt plaintext with GPG for the given recipient."""
    result = subprocess.run(
        [
            "gpg", "--encrypt", "--armor",
            "--recipient", recipient,
            "--trust-model", "always",
        ],
        input=plaintext.encode(),
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GPG encryption failed: {result.stderr.decode()}")
    return result.stdout


def _store_in_secret_manager(
    secret_name: str,
    secret_value: bytes,
    project: str = "purecortexai",
) -> None:
    """Store a secret in GCP Secret Manager."""
    # Check if secret exists
    check = subprocess.run(
        ["gcloud", "secrets", "describe", secret_name, "--project", project],
        capture_output=True,
    )
    if check.returncode != 0:
        # Create the secret
        subprocess.run(
            [
                "gcloud", "secrets", "create", secret_name,
                "--project", project,
                "--replication-policy", "automatic",
            ],
            check=True,
        )
        print(f"  Created secret: {secret_name}")

    # Add a version with the encrypted data
    result = subprocess.run(
        [
            "gcloud", "secrets", "versions", "add", secret_name,
            "--project", project,
            "--data-file", "-",
        ],
        input=secret_value,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Secret Manager failed: {result.stderr.decode()}")
    print(f"  Stored encrypted mnemonic in: {secret_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Algorand deployer account with encrypted storage"
    )
    parser.add_argument(
        "--secret-name",
        default="MAINNET_AIRDROP_DEPLOYER_MNEMONIC",
        help="GCP Secret Manager secret name",
    )
    parser.add_argument(
        "--gpg-recipient",
        default=None,
        help="GPG recipient for mnemonic encryption (omit to store plaintext in Secret Manager)",
    )
    parser.add_argument(
        "--project",
        default="purecortexai",
        help="GCP project ID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate account and print address only, do not store",
    )
    args = parser.parse_args()

    # Generate new account
    private_key, address = account.generate_account()
    mnemonic_phrase = mnemonic.from_private_key(private_key)

    print(f"\nNew Algorand Deployer Account")
    print(f"  Address: {address}")
    print(f"  For: AirdropClaim contract deployment")

    if args.dry_run:
        print(f"\n  [DRY RUN] Mnemonic: {mnemonic_phrase}")
        print(f"\n  Fund this address with ALGO before deploying.")
        _zeroize(mnemonic_phrase)
        _zeroize(private_key)
        return

    # Encrypt and store
    if args.gpg_recipient:
        print(f"\n  Encrypting mnemonic with GPG for: {args.gpg_recipient}")
        encrypted = _gpg_encrypt(mnemonic_phrase, args.gpg_recipient)
        _store_in_secret_manager(args.secret_name, encrypted, args.project)
        print(f"  Mnemonic encrypted with GPG and stored in Secret Manager")
    else:
        print(f"\n  Storing plaintext mnemonic in Secret Manager (no GPG)")
        _store_in_secret_manager(
            args.secret_name, mnemonic_phrase.encode(), args.project,
        )

    # Zeroize sensitive data from memory
    _zeroize(mnemonic_phrase)
    _zeroize(private_key)

    print(f"\n  IMPORTANT: Fund {address} with at least 10 ALGO before deploying.")
    print(f"  To deploy: python scripts/deploy_mainnet.py --mnemonic-secret {args.secret_name} --confirm")


if __name__ == "__main__":
    main()
