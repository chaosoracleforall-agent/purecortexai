#!/usr/bin/env python3
"""
PURECORTEX Airdrop Snapshot Service.

Queries the Algorand Indexer to build the eligibility list for the Genesis
Airdrop. Evaluates all 7 tiers and produces a Merkle tree for on-chain
verification of claims.

Usage:
    python scripts/airdrop_snapshot.py [--output snapshots/] [--block ROUND]
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from algosdk.v2client import indexer

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "snapshots"

MAINNET_INDEXER_URL = "https://mainnet-idx.4160.nodely.dev"
TESTNET_INDEXER_URL = "https://testnet-idx.4160.nodely.dev"

TINYMAN_V2_APP_ID = 1002541853
PACT_APP_ID = 620995314
FOLKS_LENDING_APP_ID = 686498781
GOVERNANCE_ESCROW_PREFIX = "GOVERRR"

TOTAL_AIRDROP = 3_100_000_000_000_000

TIER_ALLOCATIONS = {
    "testnet_pioneers": 0.05,
    "algorand_defi": 0.30,
    "algorand_governors": 0.20,
    "nfd_holders": 0.10,
    "developers": 0.10,
    "social_campaign": 0.15,
    "community_tasks": 0.10,
}

MIN_ALGO_BALANCE = 10_000_000
MIN_WALLET_AGE_ROUNDS = 1_000_000


@dataclass
class WalletEligibility:
    address: str
    tiers: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    total_allocation: int = 0


def get_indexer(network: str = "mainnet") -> indexer.IndexerClient:
    url = MAINNET_INDEXER_URL if network == "mainnet" else TESTNET_INDEXER_URL
    return indexer.IndexerClient("", url)


def snapshot_defi_users(idx: indexer.IndexerClient, block: int | None = None) -> dict[str, dict[str, Any]]:
    """Identify wallets that interacted with major Algorand DeFi protocols."""
    wallets: dict[str, dict[str, Any]] = {}
    app_ids = [TINYMAN_V2_APP_ID, PACT_APP_ID, FOLKS_LENDING_APP_ID]

    search_kwargs: dict[str, Any] = {}
    if block is not None:
        search_kwargs["max_round"] = block

    for app_id in app_ids:
        print(f"  Scanning app {app_id}...")
        try:
            response = idx.search_transactions(
                application_id=app_id,
                limit=1000,
                **search_kwargs,
            )
            for txn in response.get("transactions", []):
                sender = txn.get("sender", "")
                if sender and sender not in wallets:
                    wallets[sender] = {
                        "protocols": [],
                        "first_seen": txn.get("round-time", 0),
                    }
                if sender:
                    protocol = {
                        TINYMAN_V2_APP_ID: "tinyman",
                        PACT_APP_ID: "pact",
                        FOLKS_LENDING_APP_ID: "folks_finance",
                    }.get(app_id, str(app_id))
                    if protocol not in wallets[sender]["protocols"]:
                        wallets[sender]["protocols"].append(protocol)
        except Exception as e:
            print(f"    Warning: Failed to scan app {app_id}: {e}")

    filtered: dict[str, dict[str, Any]] = {}
    for addr, info in wallets.items():
        try:
            acct_info = idx.account_info(addr)
            acct = acct_info.get("account", {})
            balance = acct.get("amount", 0)
            created_round = acct.get("created-at-round", 0)

            if balance < MIN_ALGO_BALANCE:
                continue

            if block is not None and created_round > 0:
                wallet_age = block - created_round
                if wallet_age < MIN_WALLET_AGE_ROUNDS:
                    continue

            filtered[addr] = info
        except Exception as e:
            print(f"    Warning: Could not verify wallet {addr}: {e}")

    return filtered


NFD_REGISTRY_APP_ID = 760937186  # NFD v2 registry on mainnet


def snapshot_governors(idx: indexer.IndexerClient, block: int | None = None) -> set[str]:
    """Identify wallets that participated in Algorand governance periods."""
    governors: set[str] = set()
    search_kwargs: dict[str, Any] = {"limit": 1000}
    if block is not None:
        search_kwargs["max_round"] = block

    try:
        # Governance commitment transactions send ALGO to escrow addresses
        # starting with "GOVERRR". We look for payment transactions to these.
        response = idx.search_transactions(
            note_prefix=b"af/gov",
            **search_kwargs,
        )
        for txn in response.get("transactions", []):
            sender = txn.get("sender", "")
            if sender:
                governors.add(sender)
    except Exception as e:
        print(f"    Warning: Governance scan (note prefix) failed: {e}")

    try:
        # Also check for accounts that sent commitment transactions
        response = idx.search_transactions(
            address=GOVERNANCE_ESCROW_PREFIX,
            address_role="receiver",
            **search_kwargs,
        )
        for txn in response.get("transactions", []):
            sender = txn.get("sender", "")
            if sender:
                governors.add(sender)
    except Exception as e:
        print(f"    Warning: Governance scan (escrow) failed: {e}")

    return governors


def snapshot_nfd_holders(idx: indexer.IndexerClient) -> set[str]:
    """Identify wallets that own at least one .algo NFD (Non-Fungible Domain)."""
    holders: set[str] = set()

    try:
        response = idx.search_transactions(
            application_id=NFD_REGISTRY_APP_ID,
            limit=1000,
        )
        for txn in response.get("transactions", []):
            sender = txn.get("sender", "")
            if sender:
                holders.add(sender)
    except Exception as e:
        print(f"    Warning: NFD holder scan failed: {e}")

    return holders


def snapshot_developers(idx: indexer.IndexerClient, block: int | None = None) -> set[str]:
    """Identify wallets that deployed smart contracts on Algorand."""
    developers: set[str] = set()
    search_kwargs: dict[str, Any] = {"limit": 1000, "txn_type": "appl"}
    if block is not None:
        search_kwargs["max_round"] = block

    try:
        response = idx.search_transactions(**search_kwargs)
        for txn in response.get("transactions", []):
            # Application create transactions have on_completion = 0
            # and include an approval_program
            app_txn = txn.get("application-transaction", {})
            if app_txn.get("on-completion") == "noop" and app_txn.get("approval-program"):
                sender = txn.get("sender", "")
                if sender:
                    developers.add(sender)
    except Exception as e:
        print(f"    Warning: Developer scan failed: {e}")

    return developers


def snapshot_social_campaign(db_url: str | None = None) -> set[str]:
    """Pull registered wallets from the airdrop_registrations table."""
    registrations: set[str] = set()

    if not db_url:
        db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("    Warning: DATABASE_URL not set — skipping social campaign tier")
        return registrations

    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT wallet_address FROM airdrop_registrations"))
            for row in result:
                registrations.add(row[0])
    except Exception as e:
        print(f"    Warning: Social campaign scan failed: {e}")

    return registrations


def snapshot_community_tasks(db_url: str | None = None) -> set[str]:
    """Pull wallets that completed community tasks from the database."""
    participants: set[str] = set()

    if not db_url:
        db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("    Warning: DATABASE_URL not set — skipping community tasks tier")
        return participants

    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as conn:
            # community_task_completions table stores task completers
            result = conn.execute(sqlalchemy.text(
                "SELECT DISTINCT wallet_address FROM community_task_completions"
            ))
            for row in result:
                participants.add(row[0])
    except Exception as e:
        print(f"    Warning: Community tasks scan failed: {e}")

    return participants


def snapshot_testnet_pioneers(idx: indexer.IndexerClient, testnet_app_ids: list[int]) -> set[str]:
    """Identify wallets that interacted with PureCortex testnet contracts."""
    pioneers: set[str] = set()
    testnet_idx = get_indexer("testnet")

    for app_id in testnet_app_ids:
        try:
            response = testnet_idx.search_transactions(
                application_id=app_id,
                limit=1000,
            )
            for txn in response.get("transactions", []):
                sender = txn.get("sender", "")
                if sender:
                    pioneers.add(sender)
        except Exception as e:
            print(f"    Warning: Failed to scan testnet app {app_id}: {e}")

    return pioneers


def compute_merkle_root(leaves: list[bytes]) -> bytes:
    """Compute a Merkle root from a sorted list of leaf hashes.

    Uses domain separation: leaf nodes are prefixed with 0x00,
    internal nodes with 0x01 to prevent second-preimage attacks.
    Odd leaves are carried up rather than duplicated.
    """
    if not leaves:
        return b"\x00" * 32

    level = sorted(leaves)

    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                combined = b"\x01" + level[i] + level[i + 1]
                next_level.append(hashlib.sha256(combined).digest())
            else:
                next_level.append(level[i])
        level = next_level

    return level[0]


def wallet_leaf(address: str, amount: int) -> bytes:
    """Compute the Merkle leaf for a wallet's allocation.

    Encoding uses raw bytes to match the AVM smart contract:
      SHA256(0x00 || 32-byte-public-key || ":" || 8-byte-big-endian-amount)

    For backwards compatibility with off-chain tools that don't have
    algosdk, falls back to the UTF-8 string encoding when the address
    cannot be decoded (e.g. in unit tests with short test addresses).
    """
    try:
        from algosdk.encoding import decode_address
        raw_pk = decode_address(address)  # 32 bytes
        data = b"\x00" + raw_pk + b":" + amount.to_bytes(8, "big")
    except Exception:
        # Fallback for test addresses that aren't valid Algorand addresses
        data = b"\x00" + address.encode() + b":" + amount.to_bytes(8, "big")
    return hashlib.sha256(data).digest()


def pack_proof_for_avm(proof: list[dict[str, Any]]) -> bytes:
    """Pack a JSON proof into the binary format expected by the AVM contract.

    Each step becomes 33 bytes: 32-byte sibling hash + 1-byte position flag.
    Position flag: 0x00 = sibling is on the left, 0x01 = sibling is on the right.
    """
    packed = b""
    for step in proof:
        sibling_hash = bytes.fromhex(step["hash"])
        # In the JSON proof, "left" means the sibling is to the left of us
        # In the AVM contract, 0x00 = sibling on left, 0x01 = sibling on right
        position_byte = b"\x00" if step["position"] == "left" else b"\x01"
        packed += sibling_hash + position_byte
    return packed


def generate_merkle_proof(leaves: list[bytes], target_index: int) -> list[dict[str, Any]]:
    """Generate a Merkle proof for a specific leaf index.

    Uses the same domain separation as compute_merkle_root (0x01 prefix
    for internal nodes) and carries odd leaves up without duplication.
    """
    if len(leaves) <= 1:
        return []

    level = sorted(leaves)
    proof = []
    idx = level.index(leaves[target_index]) if target_index < len(leaves) else 0

    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                if i == idx or i + 1 == idx:
                    sibling_idx = i + 1 if i == idx else i
                    proof.append({
                        "hash": level[sibling_idx].hex(),
                        "position": "right" if sibling_idx > idx else "left",
                    })
                combined = b"\x01" + level[i] + level[i + 1]
                next_level.append(hashlib.sha256(combined).digest())
            else:
                next_level.append(level[i])

        idx = idx // 2
        level = next_level

    return proof


def run_snapshot(
    network: str = "mainnet",
    block: int | None = None,
    testnet_app_ids: list[int] | None = None,
    db_url: str | None = None,
) -> dict[str, Any]:
    """Execute the full airdrop snapshot pipeline across all 7 tiers."""
    print(f"Starting airdrop snapshot on {network}...")
    idx = get_indexer(network)

    if testnet_app_ids is None:
        manifest_path = ROOT / "deployment.testnet.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            testnet_app_ids = [
                manifest["contracts"]["agentFactory"]["appId"],
                manifest["contracts"]["governance"]["appId"],
                manifest["contracts"]["staking"]["appId"],
                manifest["contracts"]["treasury"]["appId"],
            ]
        else:
            testnet_app_ids = []

    eligibility: dict[str, WalletEligibility] = {}

    print("\n[1/7] Scanning testnet pioneers...")
    pioneers = snapshot_testnet_pioneers(idx, testnet_app_ids)
    print(f"  Found {len(pioneers)} testnet pioneer wallets")
    for addr in pioneers:
        if addr not in eligibility:
            eligibility[addr] = WalletEligibility(address=addr)
        eligibility[addr].tiers.append("testnet_pioneers")
        eligibility[addr].scores["testnet_pioneers"] = 1.0

    print("\n[2/7] Scanning DeFi users...")
    defi_wallets = snapshot_defi_users(idx, block)
    print(f"  Found {len(defi_wallets)} DeFi-active wallets")
    for addr, info in defi_wallets.items():
        if addr not in eligibility:
            eligibility[addr] = WalletEligibility(address=addr)
        eligibility[addr].tiers.append("algorand_defi")
        protocol_count = len(info.get("protocols", []))
        eligibility[addr].scores["algorand_defi"] = min(1.0, protocol_count / 3.0)

    print("\n[3/7] Scanning Algorand governors...")
    governors = snapshot_governors(idx, block)
    print(f"  Found {len(governors)} governance participants")
    for addr in governors:
        if addr not in eligibility:
            eligibility[addr] = WalletEligibility(address=addr)
        eligibility[addr].tiers.append("algorand_governors")
        eligibility[addr].scores["algorand_governors"] = 1.0

    print("\n[4/7] Scanning NFD holders...")
    nfd_holders = snapshot_nfd_holders(idx)
    print(f"  Found {len(nfd_holders)} NFD holders")
    for addr in nfd_holders:
        if addr not in eligibility:
            eligibility[addr] = WalletEligibility(address=addr)
        eligibility[addr].tiers.append("nfd_holders")
        eligibility[addr].scores["nfd_holders"] = 1.0

    print("\n[5/7] Scanning developers...")
    developers = snapshot_developers(idx, block)
    print(f"  Found {len(developers)} developer wallets")
    for addr in developers:
        if addr not in eligibility:
            eligibility[addr] = WalletEligibility(address=addr)
        eligibility[addr].tiers.append("developers")
        eligibility[addr].scores["developers"] = 1.0

    print("\n[6/7] Scanning social campaign registrations...")
    social = snapshot_social_campaign(db_url)
    print(f"  Found {len(social)} social campaign registrations")
    for addr in social:
        if addr not in eligibility:
            eligibility[addr] = WalletEligibility(address=addr)
        eligibility[addr].tiers.append("social_campaign")
        eligibility[addr].scores["social_campaign"] = 1.0

    print("\n[7/7] Scanning community task completions...")
    community = snapshot_community_tasks(db_url)
    print(f"  Found {len(community)} community task participants")
    for addr in community:
        if addr not in eligibility:
            eligibility[addr] = WalletEligibility(address=addr)
        eligibility[addr].tiers.append("community_tasks")
        eligibility[addr].scores["community_tasks"] = 1.0

    print("\nComputing allocations...")
    tier_counts: dict[str, int] = defaultdict(int)
    for wallet in eligibility.values():
        for tier in wallet.tiers:
            tier_counts[tier] += 1

    for wallet in eligibility.values():
        total = 0
        for tier in wallet.tiers:
            tier_pool = int(TOTAL_AIRDROP * TIER_ALLOCATIONS.get(tier, 0))
            count = max(1, tier_counts[tier])
            score = wallet.scores.get(tier, 1.0)
            allocation = int((tier_pool / count) * score)
            total += allocation
        wallet.total_allocation = total

    print("\nBuilding Merkle tree...")
    sorted_wallets = sorted(eligibility.values(), key=lambda w: w.address)
    leaves = [wallet_leaf(w.address, w.total_allocation) for w in sorted_wallets]
    merkle_root = compute_merkle_root(leaves)

    # Generate proofs for each wallet (both JSON and packed AVM format)
    print("Generating Merkle proofs...")
    wallet_proofs: dict[str, dict[str, Any]] = {}
    for i, wallet in enumerate(sorted_wallets):
        proof = generate_merkle_proof(leaves, i)
        packed = pack_proof_for_avm(proof)
        wallet_proofs[wallet.address] = {
            "amount": wallet.total_allocation,
            "proof": proof,
            "proof_packed_hex": packed.hex(),
        }

    result = {
        "snapshot_time": time.time(),
        "snapshot_block": block,
        "network": network,
        "total_eligible_wallets": len(eligibility),
        "total_allocation": sum(w.total_allocation for w in eligibility.values()),
        "merkle_root": merkle_root.hex(),
        "tier_summary": {
            tier: {
                "eligible_wallets": tier_counts.get(tier, 0),
                "pool_allocation": int(TOTAL_AIRDROP * pct),
            }
            for tier, pct in TIER_ALLOCATIONS.items()
        },
        "wallets": [asdict(w) for w in sorted_wallets],
        "proofs": wallet_proofs,
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"airdrop_snapshot_{network}_{int(time.time())}.json"
    output_path.write_text(json.dumps(result, indent=2))
    print(f"\nSnapshot written to {output_path}")
    print(f"Merkle root: {merkle_root.hex()}")
    print(f"Total eligible: {len(eligibility)} wallets")
    print(f"Total allocated: {sum(w.total_allocation for w in eligibility.values()):,} CORTEX (micro)")

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PURECORTEX Airdrop Snapshot")
    parser.add_argument("--network", default="mainnet", choices=["mainnet", "testnet"])
    parser.add_argument("--block", type=int, default=None, help="Snapshot at specific block round")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    run_snapshot(network=args.network, block=args.block)


if __name__ == "__main__":
    main()
