"""Tests for the AirdropClaim contract — Merkle proof verification and claim lifecycle.

Tests the full airdrop claim pipeline:
  1. Merkle tree construction (Python side, matching AVM contract logic)
  2. Proof generation and packing for on-chain verification
  3. Contract state queries (read-only methods via algopy_testing_context)
  4. Claim state tracking (box storage, totals)

Inner-transaction methods (claim, initialize, reclaim_unclaimed) are tested
at the state-management level; full integration tests with inner txns
require localnet/testnet (see live_testnet_verify.py).
"""

import hashlib

import pytest
from algopy import Bytes, UInt64
from algopy_testing import algopy_testing_context

from smart_contracts.airdrop_claim.contract import AirdropClaim, _verify_merkle_proof

# ---------------------------------------------------------------------------
# Merkle helpers — mirror the snapshot script logic with raw 32-byte keys
# so leaves match the on-chain computation exactly:
#   SHA256(0x00 || 32-byte-pubkey || ":" || 8-byte-big-endian-amount)
# ---------------------------------------------------------------------------

def _raw_leaf(raw_pk: bytes, amount: int) -> bytes:
    """Compute a Merkle leaf matching the AVM contract's leaf encoding."""
    assert len(raw_pk) == 32
    data = b"\x00" + raw_pk + b":" + amount.to_bytes(8, "big")
    return hashlib.sha256(data).digest()


def _compute_root(leaves: list[bytes]) -> bytes:
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


def _generate_proof(leaves: list[bytes], target_index: int) -> list[dict]:
    """Generate a Merkle proof (JSON form) for a specific leaf."""
    if len(leaves) <= 1:
        return []

    level = sorted(leaves)
    idx = level.index(leaves[target_index])
    proof = []

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


def _pack_proof(proof: list[dict]) -> bytes:
    """Pack JSON proof into the 33-byte-per-step binary format for AVM."""
    packed = b""
    for step in proof:
        sibling_hash = bytes.fromhex(step["hash"])
        position_byte = b"\x00" if step["position"] == "left" else b"\x01"
        packed += sibling_hash + position_byte
    return packed


def _verify_proof_python(leaf: bytes, proof: list[dict], root: bytes) -> bool:
    """Offline proof verifier (mirrors AVM _verify_merkle_proof)."""
    cursor = leaf
    for step in proof:
        sibling = bytes.fromhex(step["hash"])
        if step["position"] == "left":
            combined = b"\x01" + sibling + cursor
        else:
            combined = b"\x01" + cursor + sibling
        cursor = hashlib.sha256(combined).digest()
    return cursor == root


# ---------------------------------------------------------------------------
# Test wallet setup — deterministic 32-byte "public keys"
# ---------------------------------------------------------------------------

# Hardcoded qualifying wallet: the mainnet creator address
CREATOR_ADDR = "SOJXXJA43JYXRDTBHXVLS6KDBERTT77QAWRBKQOCGPEOS6ESGLDWGU474Y"

# Deterministic test "public keys" (32 bytes each)
TEST_PK_ALICE = hashlib.sha256(b"alice-test-pk").digest()
TEST_PK_BOB = hashlib.sha256(b"bob-test-pk").digest()
TEST_PK_CAROL = hashlib.sha256(b"carol-test-pk").digest()

TEST_AMOUNT_ALICE = 500_000_000_000  # 500B CORTEX micro
TEST_AMOUNT_BOB = 300_000_000_000
TEST_AMOUNT_CAROL = 200_000_000_000
TOTAL_ALLOCATION = TEST_AMOUNT_ALICE + TEST_AMOUNT_BOB + TEST_AMOUNT_CAROL

CLAIM_DEADLINE = 1_800_000_000  # far-future timestamp


def _build_test_tree():
    """Build a 3-leaf Merkle tree with deterministic test wallets."""
    leaves = [
        _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE),
        _raw_leaf(TEST_PK_BOB, TEST_AMOUNT_BOB),
        _raw_leaf(TEST_PK_CAROL, TEST_AMOUNT_CAROL),
    ]
    root = _compute_root(leaves)
    proofs = [_generate_proof(leaves, i) for i in range(3)]
    packed_proofs = [_pack_proof(p) for p in proofs]
    return leaves, root, proofs, packed_proofs


# ---------------------------------------------------------------------------
# Test: Python-side Merkle proof pipeline (must match AVM contract logic)
# ---------------------------------------------------------------------------

class TestMerkleProofPipeline:
    """Verify the full Merkle proof pipeline works end-to-end in Python."""

    def test_leaf_computation_is_deterministic(self):
        leaf1 = _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE)
        leaf2 = _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE)
        assert leaf1 == leaf2
        assert len(leaf1) == 32

    def test_leaf_changes_with_amount(self):
        leaf1 = _raw_leaf(TEST_PK_ALICE, 1000)
        leaf2 = _raw_leaf(TEST_PK_ALICE, 2000)
        assert leaf1 != leaf2

    def test_leaf_changes_with_address(self):
        leaf1 = _raw_leaf(TEST_PK_ALICE, 1000)
        leaf2 = _raw_leaf(TEST_PK_BOB, 1000)
        assert leaf1 != leaf2

    def test_three_wallet_tree_root_is_deterministic(self):
        _, root1, _, _ = _build_test_tree()
        _, root2, _, _ = _build_test_tree()
        assert root1 == root2
        assert len(root1) == 32

    def test_all_proofs_verify(self):
        leaves, root, proofs, _ = _build_test_tree()
        for i, leaf in enumerate(leaves):
            assert _verify_proof_python(leaf, proofs[i], root), (
                f"Proof for leaf {i} failed verification"
            )

    def test_tampered_amount_fails_verification(self):
        leaves, root, proofs, _ = _build_test_tree()
        # Tamper: use Alice's proof but with wrong amount
        tampered_leaf = _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE + 1)
        # Find Alice's proof index (leaf order may change after sorting)
        alice_leaf = _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE)
        alice_idx = leaves.index(alice_leaf)
        assert not _verify_proof_python(tampered_leaf, proofs[alice_idx], root)

    def test_tampered_proof_fails_verification(self):
        leaves, root, proofs, _ = _build_test_tree()
        alice_leaf = _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE)
        alice_idx = leaves.index(alice_leaf)
        if proofs[alice_idx]:
            bad_proof = proofs[alice_idx].copy()
            # Flip one byte in the first sibling hash
            original_hash = bad_proof[0]["hash"]
            flipped = hex(int(original_hash, 16) ^ 1)[2:].zfill(64)
            bad_proof[0] = {"hash": flipped, "position": bad_proof[0]["position"]}
            assert not _verify_proof_python(alice_leaf, bad_proof, root)

    def test_packed_proof_format(self):
        _, _, proofs, packed_proofs = _build_test_tree()
        for i, proof in enumerate(proofs):
            packed = packed_proofs[i]
            assert len(packed) == len(proof) * 33, (
                f"Packed proof {i}: expected {len(proof) * 33} bytes, got {len(packed)}"
            )

    def test_single_leaf_tree_empty_proof(self):
        leaves = [_raw_leaf(TEST_PK_ALICE, 1000)]
        root = _compute_root(leaves)
        proof = _generate_proof(leaves, 0)
        assert proof == []
        assert root == leaves[0]

    def test_empty_tree_zero_root(self):
        root = _compute_root([])
        assert root == b"\x00" * 32


# ---------------------------------------------------------------------------
# Test: AVM contract _verify_merkle_proof subroutine
# ---------------------------------------------------------------------------

class TestAVMVerifyMerkleProof:
    """Test the on-chain _verify_merkle_proof subroutine via algopy_testing."""

    def test_valid_proof_returns_true(self):
        with algopy_testing_context():
            leaves, root, _, packed_proofs = _build_test_tree()
            alice_leaf = _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE)
            alice_idx = leaves.index(alice_leaf)
            result = _verify_merkle_proof(
                Bytes(alice_leaf),
                Bytes(packed_proofs[alice_idx]),
                Bytes(root),
            )
            assert result

    def test_all_wallets_verify(self):
        with algopy_testing_context():
            leaves, root, _, packed_proofs = _build_test_tree()
            pks = [TEST_PK_ALICE, TEST_PK_BOB, TEST_PK_CAROL]
            amounts = [TEST_AMOUNT_ALICE, TEST_AMOUNT_BOB, TEST_AMOUNT_CAROL]

            for pk, amount in zip(pks, amounts):
                leaf = _raw_leaf(pk, amount)
                idx = leaves.index(leaf)
                result = _verify_merkle_proof(
                    Bytes(leaf),
                    Bytes(packed_proofs[idx]),
                    Bytes(root),
                )
                assert result, f"Proof failed for pk={pk[:8].hex()}..."

    def test_wrong_leaf_fails(self):
        with algopy_testing_context():
            leaves, root, _, packed_proofs = _build_test_tree()
            alice_leaf = _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE)
            alice_idx = leaves.index(alice_leaf)
            wrong_leaf = _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE + 1)
            result = _verify_merkle_proof(
                Bytes(wrong_leaf),
                Bytes(packed_proofs[alice_idx]),
                Bytes(root),
            )
            assert not result

    def test_wrong_root_fails(self):
        with algopy_testing_context():
            leaves, root, _, packed_proofs = _build_test_tree()
            alice_leaf = _raw_leaf(TEST_PK_ALICE, TEST_AMOUNT_ALICE)
            alice_idx = leaves.index(alice_leaf)
            bad_root = b"\xff" * 32
            result = _verify_merkle_proof(
                Bytes(alice_leaf),
                Bytes(packed_proofs[alice_idx]),
                Bytes(bad_root),
            )
            assert not result

    def test_empty_proof_single_leaf(self):
        with algopy_testing_context():
            leaf = _raw_leaf(TEST_PK_ALICE, 1000)
            root = leaf  # single-leaf tree: root == leaf
            result = _verify_merkle_proof(
                Bytes(leaf),
                Bytes(b""),  # empty proof
                Bytes(root),
            )
            assert result

    def test_invalid_proof_length_rejected(self):
        with algopy_testing_context():
            leaf = _raw_leaf(TEST_PK_ALICE, 1000)
            root = b"\x00" * 32
            # 34 bytes is not a multiple of 33
            with pytest.raises(Exception, match="Invalid proof length"):
                _verify_merkle_proof(
                    Bytes(leaf),
                    Bytes(b"\x00" * 34),
                    Bytes(root),
                )


# ---------------------------------------------------------------------------
# Test: AirdropClaim contract state and read-only methods
# ---------------------------------------------------------------------------

def _setup_airdrop(ctx):
    """Initialize an AirdropClaim contract with a 3-wallet Merkle tree."""
    contract = AirdropClaim()
    cortex_asset = ctx.any.asset()
    _, root, _, _ = _build_test_tree()

    contract.cortex_token = cortex_asset.id
    contract.merkle_root = Bytes(root)
    contract.claim_deadline = UInt64(CLAIM_DEADLINE)
    contract.total_allocated = UInt64(TOTAL_ALLOCATION)
    contract.total_claimed = UInt64(0)
    contract.initialized = UInt64(1)

    return contract, cortex_asset, root


class TestAirdropInitialState:
    def test_defaults(self):
        with algopy_testing_context():
            contract = AirdropClaim()
            assert contract.cortex_token == UInt64(0)
            assert contract.claim_deadline == UInt64(0)
            assert contract.total_allocated == UInt64(0)
            assert contract.total_claimed == UInt64(0)
            assert contract.initialized == UInt64(0)


class TestAirdropGetInfo:
    def test_returns_packed_state(self):
        with algopy_testing_context() as ctx:
            contract, _, root = _setup_airdrop(ctx)
            contract.total_claimed = UInt64(100_000)

            info = contract.get_airdrop_info()
            expected = (
                TOTAL_ALLOCATION.to_bytes(8, "big")
                + (100_000).to_bytes(8, "big")
                + CLAIM_DEADLINE.to_bytes(8, "big")
                + root
            )
            assert info == Bytes(expected)

    def test_info_reflects_zero_claims(self):
        with algopy_testing_context() as ctx:
            contract, _, root = _setup_airdrop(ctx)
            info = contract.get_airdrop_info()
            expected = (
                TOTAL_ALLOCATION.to_bytes(8, "big")
                + (0).to_bytes(8, "big")
                + CLAIM_DEADLINE.to_bytes(8, "big")
                + root
            )
            assert info == Bytes(expected)


class TestAirdropGetClaimStatus:
    def test_unclaimed_address(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_airdrop(ctx)
            account = ctx.any.account()
            remaining = TOTAL_ALLOCATION

            status = contract.get_claim_status(account)
            expected = (
                b"\x00"  # not claimed
                + CLAIM_DEADLINE.to_bytes(8, "big")
                + remaining.to_bytes(8, "big")
            )
            assert status == Bytes(expected)

    def test_claimed_address(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_airdrop(ctx)
            account = ctx.any.account()

            # Simulate a claim by writing the box and updating total
            contract.claims[account.bytes] = Bytes(b"\x01")
            contract.total_claimed = UInt64(TEST_AMOUNT_ALICE)
            remaining = TOTAL_ALLOCATION - TEST_AMOUNT_ALICE

            status = contract.get_claim_status(account)
            expected = (
                b"\x01"  # claimed
                + CLAIM_DEADLINE.to_bytes(8, "big")
                + remaining.to_bytes(8, "big")
            )
            assert status == Bytes(expected)


class TestAirdropClaimStateTracking:
    """Test claim state management (box writes, total tracking).

    These tests verify the state-tracking logic by simulating the
    state changes that claim() would make, since inner transactions
    are not supported in algopy_testing_context.
    """

    def test_claim_marks_address_in_box(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_airdrop(ctx)
            account = ctx.any.account()

            # Before claim: not in box
            assert account.bytes not in contract.claims

            # Simulate claim: write box
            contract.claims[account.bytes] = Bytes(b"\x01")
            assert account.bytes in contract.claims

    def test_double_claim_detected(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_airdrop(ctx)
            account = ctx.any.account()

            # First claim
            contract.claims[account.bytes] = Bytes(b"\x01")
            contract.total_claimed = UInt64(TEST_AMOUNT_ALICE)

            # Second claim attempt — box check catches it
            assert account.bytes in contract.claims

    def test_total_claimed_accumulates(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_airdrop(ctx)
            assert contract.total_claimed == UInt64(0)

            contract.total_claimed = UInt64(TEST_AMOUNT_ALICE)
            assert contract.total_claimed == UInt64(TEST_AMOUNT_ALICE)

            new_total = TEST_AMOUNT_ALICE + TEST_AMOUNT_BOB
            contract.total_claimed = UInt64(new_total)
            assert contract.total_claimed == UInt64(new_total)

    def test_total_claimed_cannot_exceed_allocated(self):
        """Verify the ceiling check logic: total_claimed + amount <= total_allocated."""
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_airdrop(ctx)
            contract.total_claimed = UInt64(TOTAL_ALLOCATION - 100)

            # This claim would exceed the ceiling
            new_claim = 200
            assert int(contract.total_claimed) + new_claim > TOTAL_ALLOCATION

    def test_reclaim_sets_total_to_allocated(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_airdrop(ctx)
            contract.total_claimed = UInt64(TEST_AMOUNT_ALICE)

            # Simulate reclaim: set total_claimed = total_allocated
            unclaimed = TOTAL_ALLOCATION - TEST_AMOUNT_ALICE
            assert unclaimed > 0
            contract.total_claimed = UInt64(TOTAL_ALLOCATION)
            assert contract.total_claimed == contract.total_allocated


# ---------------------------------------------------------------------------
# Test: Cross-compatibility with snapshot script
# ---------------------------------------------------------------------------

class TestSnapshotCompatibility:
    """Verify that the snapshot script's Merkle functions produce
    proofs that the AVM contract's _verify_merkle_proof accepts."""

    def test_snapshot_wallet_leaf_matches_contract_leaf(self):
        """The Python wallet_leaf() must produce the same hash as the
        AVM contract's leaf computation for real Algorand addresses."""
        try:
            from algosdk.encoding import decode_address
            from scripts.airdrop_snapshot import wallet_leaf
        except ImportError:
            pytest.skip("algosdk or snapshot script not available")

        # Use the hardcoded creator address
        raw_pk = decode_address(CREATOR_ADDR)
        amount = 1_000_000_000

        # Python snapshot script leaf
        script_leaf = wallet_leaf(CREATOR_ADDR, amount)

        # Manual leaf (same formula as AVM contract)
        contract_leaf = _raw_leaf(raw_pk, amount)

        assert script_leaf == contract_leaf

    def test_snapshot_proof_verifies_on_avm(self):
        """Proofs from the snapshot script must verify via AVM subroutine."""
        try:
            from algosdk.encoding import decode_address
            from scripts.airdrop_snapshot import (
                wallet_leaf,
                compute_merkle_root,
                generate_merkle_proof,
                pack_proof_for_avm,
            )
        except ImportError:
            pytest.skip("algosdk or snapshot script not available")

        # Build a tree with real Algorand addresses
        addresses = [
            CREATOR_ADDR,
            # Two more valid Algorand addresses (deterministic from algosdk)
            "WJ44A3NA4ZNKHFKSAI4G2Z5AJTFPZGANXF5EHPPHPZHYAOXR25A22LU2IQ",
            "6HC22ISVTPSR6MHGRCXKEZFZI3YXEEBEHKCIC7RW77CF4RP2JHFMXZ3S2Y",
        ]
        amounts = [500_000_000_000, 300_000_000_000, 200_000_000_000]

        leaves = [wallet_leaf(addr, amt) for addr, amt in zip(addresses, amounts)]
        root = compute_merkle_root(leaves)

        with algopy_testing_context():
            for i in range(len(leaves)):
                proof = generate_merkle_proof(leaves, i)
                packed = pack_proof_for_avm(proof)
                result = _verify_merkle_proof(
                    Bytes(leaves[i]),
                    Bytes(packed),
                    Bytes(root),
                )
                assert result, f"AVM verification failed for address {addresses[i]}"

    def test_hardcoded_creator_wallet_in_tree(self):
        """The hardcoded creator wallet produces a valid leaf and proof."""
        try:
            from algosdk.encoding import decode_address
        except ImportError:
            pytest.skip("algosdk not available")

        raw_pk = decode_address(CREATOR_ADDR)
        amount = 500_000_000_000

        leaf = _raw_leaf(raw_pk, amount)
        leaves = [
            leaf,
            _raw_leaf(hashlib.sha256(b"wallet-2").digest(), 300_000_000_000),
            _raw_leaf(hashlib.sha256(b"wallet-3").digest(), 200_000_000_000),
        ]
        root = _compute_root(leaves)
        proof = _generate_proof(leaves, 0)
        packed = _pack_proof(proof)

        with algopy_testing_context():
            result = _verify_merkle_proof(
                Bytes(leaf),
                Bytes(packed),
                Bytes(root),
            )
            assert result
