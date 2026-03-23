"""Tests for the airdrop snapshot Merkle tree logic (offline, no indexer calls)."""

import hashlib
from scripts.airdrop_snapshot import (
    compute_merkle_root,
    wallet_leaf,
    generate_merkle_proof,
    TIER_ALLOCATIONS,
    TOTAL_AIRDROP,
    WalletEligibility,
)


def test_wallet_leaf_is_deterministic():
    leaf1 = wallet_leaf("AAAA", 1000)
    leaf2 = wallet_leaf("AAAA", 1000)
    assert leaf1 == leaf2
    assert len(leaf1) == 32


def test_wallet_leaf_changes_with_amount():
    leaf1 = wallet_leaf("AAAA", 1000)
    leaf2 = wallet_leaf("AAAA", 2000)
    assert leaf1 != leaf2


def test_wallet_leaf_changes_with_address():
    leaf1 = wallet_leaf("AAAA", 1000)
    leaf2 = wallet_leaf("BBBB", 1000)
    assert leaf1 != leaf2


def test_merkle_root_empty():
    root = compute_merkle_root([])
    assert root == b"\x00" * 32


def test_merkle_root_single_leaf():
    leaf = wallet_leaf("ADDR1", 5000)
    root = compute_merkle_root([leaf])
    assert root == leaf


def test_merkle_root_two_leaves():
    leaf1 = wallet_leaf("ADDR1", 1000)
    leaf2 = wallet_leaf("ADDR2", 2000)
    root = compute_merkle_root([leaf1, leaf2])

    sorted_leaves = sorted([leaf1, leaf2])
    expected = hashlib.sha256(b"\x01" + sorted_leaves[0] + sorted_leaves[1]).digest()
    assert root == expected


def test_merkle_root_deterministic():
    leaves = [wallet_leaf(f"ADDR{i}", i * 1000) for i in range(10)]
    root1 = compute_merkle_root(leaves)
    root2 = compute_merkle_root(leaves)
    assert root1 == root2


def test_merkle_root_changes_with_different_leaves():
    leaves1 = [wallet_leaf(f"ADDR{i}", i * 1000) for i in range(5)]
    leaves2 = [wallet_leaf(f"ADDR{i}", i * 2000) for i in range(5)]
    assert compute_merkle_root(leaves1) != compute_merkle_root(leaves2)


def test_tier_allocations_sum_to_100():
    total = sum(TIER_ALLOCATIONS.values())
    assert abs(total - 1.0) < 1e-9


def test_total_airdrop_is_31_percent():
    total_supply = 10_000_000_000_000_000
    assert TOTAL_AIRDROP == int(total_supply * 0.31)


def test_wallet_eligibility_dataclass():
    w = WalletEligibility(address="TEST_ADDR")
    assert w.address == "TEST_ADDR"
    assert w.tiers == []
    assert w.scores == {}
    assert w.total_allocation == 0

    w.tiers.append("testnet_pioneers")
    w.scores["testnet_pioneers"] = 1.0
    w.total_allocation = 500_000
    assert len(w.tiers) == 1
    assert w.total_allocation == 500_000
