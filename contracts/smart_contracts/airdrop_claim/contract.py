from algopy import (
    ARC4Contract,
    BoxMap,
    UInt64,
    Asset,
    Account,
    Txn,
    Global,
    Bytes,
    itxn,
    op,
    subroutine,
)
from algopy.arc4 import abimethod


@subroutine
def _verify_merkle_proof(
    leaf: Bytes,
    proof: Bytes,
    merkle_root: Bytes,
) -> bool:
    """Verify a Merkle proof against a root hash.

    The *proof* argument is a packed byte array where each step is exactly
    33 bytes: 32 bytes of sibling hash followed by 1 byte position flag
    (0x00 = sibling is on the left, 0x01 = sibling is on the right).

    Domain separation matches the Python snapshot implementation:
      - leaf nodes: SHA256(0x00 || data)  (computed by caller)
      - internal nodes: SHA256(0x01 || left || right)
    """
    proof_len = proof.length
    # Each step is 33 bytes (32 hash + 1 position)
    assert proof_len % UInt64(33) == UInt64(0), "Invalid proof length"

    cursor = leaf
    step_count = proof_len // UInt64(33)
    idx = UInt64(0)

    while idx < step_count:
        offset = idx * UInt64(33)
        sibling = op.extract(proof, offset, 32)
        position = op.extract(proof, offset + UInt64(32), 1)

        if position == Bytes(b"\x00"):
            # Sibling is on the left
            combined = Bytes(b"\x01") + sibling + cursor
        else:
            # Sibling is on the right
            combined = Bytes(b"\x01") + cursor + sibling
        cursor = op.sha256(combined)
        idx += UInt64(1)

    return cursor == merkle_root


class AirdropClaim(ARC4Contract):
    """
    Non-custodial Airdrop Claim Contract for PURECORTEX.

    Users claim their CORTEX allocation by submitting a Merkle proof
    that verifies their address and amount against the published
    snapshot root. The contract verifies the proof on-chain, marks the
    address as claimed in box storage, and transfers tokens directly
    to the caller.

    Key properties:
      - Non-custodial: any eligible user can call claim() directly
      - User pays all fees (app call fee + inner transfer fee + box MBR)
      - Double-claim protection via box storage
      - Time-bounded: claims expire after claim_deadline
      - Unclaimed tokens can be reclaimed by creator after deadline
    """

    def __init__(self) -> None:
        self.cortex_token = UInt64(0)
        self.merkle_root = Bytes()
        self.claim_deadline = UInt64(0)
        self.total_allocated = UInt64(0)
        self.total_claimed = UInt64(0)
        self.initialized = UInt64(0)
        # Box storage for claim tracking: key = 32-byte address, value = 1 byte
        self.claims = BoxMap(Bytes, Bytes, key_prefix=b"c")

    @abimethod()
    def initialize(
        self,
        cortex_asset: Asset,
        merkle_root: Bytes,
        claim_deadline: UInt64,
        total_allocation: UInt64,
    ) -> None:
        """Set up the airdrop claim contract. Creator-only, once."""
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert self.initialized == UInt64(0), "Already initialized"
        assert merkle_root.length == UInt64(32), "Merkle root must be 32 bytes"
        assert claim_deadline > Global.latest_timestamp, "Deadline must be in the future"
        assert total_allocation > UInt64(0), "Allocation must be positive"

        self.cortex_token = cortex_asset.id
        self.merkle_root = merkle_root
        self.claim_deadline = claim_deadline
        self.total_allocated = total_allocation
        self.initialized = UInt64(1)

        # Opt the contract into the CORTEX ASA
        itxn.AssetTransfer(
            xfer_asset=cortex_asset,
            asset_receiver=Global.current_application_address,
            asset_amount=UInt64(0),
            fee=0,
        ).submit()

    @abimethod()
    def claim(self, amount: UInt64, proof: Bytes) -> UInt64:
        """
        Claim CORTEX tokens using a Merkle proof.

        Anyone can call this method. The caller (Txn.sender) must:
          1. Be opted into the CORTEX ASA
          2. Not have already claimed
          3. Provide a valid Merkle proof for (sender_address, amount)
          4. Call before the claim deadline
          5. Pay the transaction fee and box MBR

        The proof is a packed byte array: each step is 33 bytes
        (32-byte sibling hash + 1-byte position flag).
        """
        assert self.initialized == UInt64(1), "Not initialized"
        assert Global.latest_timestamp <= self.claim_deadline, "Claim period expired"
        assert amount > UInt64(0), "Amount must be positive"

        # Check not already claimed
        sender_key = Txn.sender.bytes
        assert sender_key not in self.claims, "Already claimed"

        # Compute leaf: SHA256(0x00 || "address:amount")
        # The address is the 58-char Algorand base32 address string
        # We use the raw 32-byte public key for determinism
        leaf_data = Bytes(b"\x00") + sender_key + Bytes(b":") + op.itob(amount)
        leaf = op.sha256(leaf_data)

        # Verify the Merkle proof
        assert _verify_merkle_proof(leaf, proof, self.merkle_root), "Invalid Merkle proof"

        # Enforce ceiling: total_claimed can never exceed total_allocated
        assert self.total_claimed + amount <= self.total_allocated, "Exceeds total allocation"

        # Mark as claimed (box storage - user pays MBR)
        self.claims[sender_key] = Bytes(b"\x01")

        # Update totals
        self.total_claimed = self.total_claimed + amount

        # Transfer CORTEX to the caller
        itxn.AssetTransfer(
            xfer_asset=Asset(self.cortex_token),
            asset_receiver=Txn.sender,
            asset_amount=amount,
            fee=0,
        ).submit()

        return amount

    @abimethod()
    def reclaim_unclaimed(self, receiver: Account) -> UInt64:
        """
        Reclaim unclaimed CORTEX after the deadline.
        Only callable by the creator after claim_deadline.
        Returns unclaimed tokens to the specified receiver (e.g., treasury).
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert self.initialized == UInt64(1), "Not initialized"
        assert Global.latest_timestamp > self.claim_deadline, "Claim period not yet expired"

        unclaimed = self.total_allocated - self.total_claimed
        assert unclaimed > UInt64(0), "No unclaimed tokens"

        # Mark all remaining as claimed to prevent repeated calls
        self.total_claimed = self.total_allocated

        itxn.AssetTransfer(
            xfer_asset=Asset(self.cortex_token),
            asset_receiver=receiver,
            asset_amount=unclaimed,
            fee=0,
        ).submit()

        return unclaimed

    @abimethod(readonly=True)
    def get_claim_status(self, address: Account) -> Bytes:
        """
        Check claim status for an address.
        Returns packed bytes: claimed (1 byte) || deadline (8 bytes) || remaining (8 bytes)
        """
        claimed = Bytes(b"\x01") if address.bytes in self.claims else Bytes(b"\x00")
        remaining = self.total_allocated - self.total_claimed
        return claimed + op.itob(self.claim_deadline) + op.itob(remaining)

    @abimethod(readonly=True)
    def get_airdrop_info(self) -> Bytes:
        """Return packed airdrop state for off-chain display."""
        return (
            op.itob(self.total_allocated)
            + op.itob(self.total_claimed)
            + op.itob(self.claim_deadline)
            + self.merkle_root
        )
