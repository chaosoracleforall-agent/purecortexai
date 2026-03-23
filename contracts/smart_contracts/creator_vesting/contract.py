from algopy import (
    ARC4Contract,
    UInt64,
    Asset,
    Account,
    Txn,
    Global,
    Bytes,
    itxn,
    op,
)
from algopy.arc4 import abimethod


class CreatorVesting(ARC4Contract):
    """
    Creator Vesting Contract for PURECORTEX.

    Enforces the creator's 10% allocation vesting schedule:
      - 10% released at TGE (Token Generation Event)
      - Remaining 90% vests linearly over 180 days (daily tranches)

    The contract holds the full creator allocation and releases tokens
    according to the vesting schedule. Only the designated beneficiary
    can claim vested tokens.

    Parameters set at initialization:
      - cortex_token: the CORTEX ASA ID
      - beneficiary: the creator's wallet address
      - tge_timestamp: Unix timestamp of the TGE
      - total_allocation: total CORTEX allocated to creator
      - tge_release_bps: basis points released at TGE (1000 = 10%)
      - vesting_days: number of days for linear vesting of remainder
    """

    def __init__(self) -> None:
        self.cortex_token = UInt64(0)
        self.beneficiary = Bytes()
        self.tge_timestamp = UInt64(0)
        self.total_allocation = UInt64(0)
        self.tge_release_bps = UInt64(1000)  # 10%
        self.vesting_days = UInt64(180)
        self.total_claimed = UInt64(0)
        self.initialized = UInt64(0)

    @abimethod()
    def initialize(
        self,
        cortex_asset: Asset,
        beneficiary: Account,
        tge_timestamp: UInt64,
        total_allocation: UInt64,
    ) -> None:
        """Set up the vesting contract. Only callable by the creator once."""
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert self.initialized == UInt64(0), "Already initialized"

        self.cortex_token = cortex_asset.id
        self.beneficiary = beneficiary.bytes
        self.tge_timestamp = tge_timestamp
        self.total_allocation = total_allocation
        self.initialized = UInt64(1)

        itxn.AssetTransfer(
            xfer_asset=cortex_asset,
            asset_receiver=Global.current_application_address,
            asset_amount=UInt64(0),
            fee=0,
        ).submit()

    @abimethod(readonly=True)
    def get_vested_amount(self) -> UInt64:
        """Calculate the total amount vested as of the current timestamp."""
        assert self.initialized == UInt64(1), "Not initialized"

        now = Global.latest_timestamp
        if now < self.tge_timestamp:
            return UInt64(0)

        tge_amount = (self.total_allocation * self.tge_release_bps) // UInt64(10_000)
        remaining = self.total_allocation - tge_amount

        elapsed = now - self.tge_timestamp
        total_vesting_seconds = self.vesting_days * UInt64(86_400)

        if elapsed >= total_vesting_seconds:
            return self.total_allocation

        daily_vesting = remaining // self.vesting_days
        days_elapsed = elapsed // UInt64(86_400)
        vested_from_schedule = daily_vesting * days_elapsed

        return tge_amount + vested_from_schedule

    @abimethod(readonly=True)
    def get_claimable(self) -> UInt64:
        """Return how many tokens the beneficiary can claim right now."""
        vested = self.get_vested_amount()
        if vested <= self.total_claimed:
            return UInt64(0)
        return vested - self.total_claimed

    @abimethod()
    def claim(self) -> UInt64:
        """Claim vested tokens. Only callable by the beneficiary."""
        assert self.initialized == UInt64(1), "Not initialized"
        assert Txn.sender == Account(self.beneficiary), "Only beneficiary can claim"

        claimable = self.get_claimable()
        assert claimable > UInt64(0), "Nothing to claim"

        self.total_claimed = self.total_claimed + claimable

        itxn.AssetTransfer(
            xfer_asset=Asset(self.cortex_token),
            asset_receiver=Account(self.beneficiary),
            asset_amount=claimable,
            fee=0,
        ).submit()

        return claimable

    @abimethod(readonly=True)
    def get_vesting_info(self) -> Bytes:
        """Return packed vesting state for off-chain display."""
        return (
            op.itob(self.total_allocation)
            + op.itob(self.total_claimed)
            + op.itob(self.tge_timestamp)
            + op.itob(self.vesting_days)
            + op.itob(self.tge_release_bps)
        )
