from algopy import (
    ARC4Contract,
    UInt64,
    Asset,
    Account,
    Txn,
    Global,
    BoxMap,
    Bytes,
    itxn,
    gtxn,
    op,
)
from algopy.arc4 import abimethod


class VeCortexStaking(ARC4Contract):
    """
    veCORTEX staking contract.

    Users lock CORTEX tokens for a configurable duration (1 week to 4 years)
    and receive veCORTEX voting power with a time-weighted boost up to 2.5x.

    Features:
    - Time-locked staking with linear boost scaling
    - Delegation of voting power to Lawmaker agents
    - Reward pool tracking for the 24% emission allocation
    - Clean unstake after lock expiry
    """

    def __init__(self) -> None:
        self.cortex_token = UInt64(0)
        self.total_staked = UInt64(0)
        self.reward_pool = UInt64(0)

        # Stakes: account_bytes -> encoded stake data
        # Encoding: amount(8) + unlock_round(8) + ve_power(8) + boost(8) = 32 bytes
        # key_prefix=b"s" so op.Box.get(b"s" + key) matches self.stakes[key]
        self.stakes = BoxMap(Bytes, Bytes, key_prefix=b"s")

        # Delegations: account_bytes -> delegate_account_bytes
        # Uses distinct prefix "d" to avoid collisions with stakes
        self.delegations = BoxMap(Bytes, Bytes, key_prefix=b"d")

        # Staking parameters
        self.MIN_LOCK_DAYS = UInt64(7)  # 1 week minimum
        self.MAX_LOCK_DAYS = UInt64(1460)  # 4 years maximum
        self.MAX_BOOST = UInt64(2500)  # 2.5x in basis points (1000 = 1x)
        self.ROUNDS_PER_DAY = UInt64(17280)  # ~3 rounds/min on Algorand

    # ------------------------------------------------------------------ #
    #  Initialization
    # ------------------------------------------------------------------ #

    @abimethod()
    def initialize(self, cortex_asset: Asset) -> None:
        """
        Initialize the staking contract with the CORTEX token reference.
        Must opt-in to the asset so the contract can hold and return tokens.
        Only callable by the application creator.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert self.cortex_token == UInt64(0), "Already initialized"
        self.cortex_token = cortex_asset.id

        # Opt-in to the CORTEX asset
        itxn.AssetTransfer(
            xfer_asset=cortex_asset,
            asset_receiver=Global.current_application_address,
            asset_amount=UInt64(0),
            fee=0,
        ).submit()

    # ------------------------------------------------------------------ #
    #  Staking
    # ------------------------------------------------------------------ #

    @abimethod()
    def stake(
        self,
        cortex_transfer: gtxn.AssetTransferTransaction,
        lock_days: UInt64,
    ) -> None:
        """
        Stake CORTEX tokens with a specified lock duration.

        The caller must include an asset transfer of CORTEX to this contract
        in the same group transaction. Lock duration determines the veCORTEX
        boost multiplier (1x at 7 days, up to 2.5x at 4 years).
        """
        assert self.cortex_token != UInt64(0), "Not initialized"
        assert cortex_transfer.xfer_asset.id == self.cortex_token, "Wrong token"
        assert lock_days >= self.MIN_LOCK_DAYS, "Lock too short"
        assert lock_days <= self.MAX_LOCK_DAYS, "Lock too long"
        assert (
            cortex_transfer.asset_receiver == Global.current_application_address
        ), "Must send to contract"

        amount = cortex_transfer.asset_amount
        assert amount > UInt64(0), "Must stake a positive amount"

        # Check that the sender does not already have an active stake
        stake_key = Txn.sender.bytes
        assert not op.Box.get(b"s" + stake_key)[1], "Already staking — unstake first"

        # Calculate unlock round
        unlock_round = Global.round + (lock_days * self.ROUNDS_PER_DAY)

        # Calculate boost: 1000 (1x) + lock_days * 1500 / MAX_LOCK_DAYS
        # At MIN_LOCK_DAYS (7):   boost ~1007  (~1.007x)
        # At MAX_LOCK_DAYS (1460): boost = 2500 (2.5x)
        boost = UInt64(1000) + (lock_days * UInt64(1500)) // self.MAX_LOCK_DAYS
        if boost > self.MAX_BOOST:
            boost = self.MAX_BOOST

        # veCORTEX power = amount * boost / 1000
        ve_power = (amount * boost) // UInt64(1000)

        # Store stake info: amount(8) + unlock_round(8) + ve_power(8) + boost(8)
        stake_data = (
            op.itob(amount)
            + op.itob(unlock_round)
            + op.itob(ve_power)
            + op.itob(boost)
        )
        self.stakes[stake_key] = stake_data

        self.total_staked = self.total_staked + amount

    # ------------------------------------------------------------------ #
    #  Unstaking
    # ------------------------------------------------------------------ #

    @abimethod()
    def unstake(self) -> None:
        """
        Unstake CORTEX tokens after the lock period has expired.
        Returns the original staked amount to the sender.
        Removes the stake record and any active delegation.
        """
        stake_key = Txn.sender.bytes
        assert op.Box.get(b"s" + stake_key)[1], "No active stake"

        stake_data = self.stakes[stake_key]
        amount = op.btoi(op.extract(stake_data, 0, 8))
        unlock_round = op.btoi(op.extract(stake_data, 8, 8))

        assert Global.round >= unlock_round, "Lock period not expired"

        # Return CORTEX via inner transaction
        itxn.AssetTransfer(
            xfer_asset=Asset(self.cortex_token),
            asset_receiver=Txn.sender,
            asset_amount=amount,
            fee=0,
        ).submit()

        # Remove stake record
        del self.stakes[stake_key]

        # Remove delegation if one exists (check with "d" prefix for delegations BoxMap)
        if op.Box.get(b"d" + stake_key)[1]:
            del self.delegations[stake_key]

        self.total_staked = self.total_staked - amount

    # ------------------------------------------------------------------ #
    #  Delegation
    # ------------------------------------------------------------------ #

    @abimethod()
    def delegate(self, lawmaker: Account) -> None:
        """
        Delegate veCORTEX voting power to a Lawmaker agent address.
        The delegatee can then vote on governance proposals on your behalf.
        """
        stake_key = Txn.sender.bytes
        assert op.Box.get(b"s" + stake_key)[1], "No active stake"
        self.delegations[stake_key] = lawmaker.bytes

    @abimethod()
    def revoke_delegation(self) -> None:
        """
        Revoke an existing delegation.
        Takes effect in the next governance epoch.
        """
        stake_key = Txn.sender.bytes
        assert op.Box.get(b"s" + stake_key)[1], "No active stake"
        # Only delete if delegation exists (check with "d" prefix for delegations BoxMap)
        if op.Box.get(b"d" + stake_key)[1]:
            del self.delegations[stake_key]

    # ------------------------------------------------------------------ #
    #  Read-only queries
    # ------------------------------------------------------------------ #

    @abimethod(readonly=True)
    def get_ve_power(self, account: Account) -> UInt64:
        """Get the veCORTEX voting power for an account."""
        stake_key = account.bytes
        if not op.Box.get(b"s" + stake_key)[1]:
            return UInt64(0)
        stake_data = self.stakes[stake_key]
        return op.btoi(op.extract(stake_data, 16, 8))

    @abimethod(readonly=True)
    def get_stake_info(self, account: Account) -> Bytes:
        """
        Get the full stake info for an account.
        Returns 32 bytes: amount(8) + unlock_round(8) + ve_power(8) + boost(8).
        Returns empty bytes if no stake exists.
        """
        stake_key = account.bytes
        if not op.Box.get(b"s" + stake_key)[1]:
            return Bytes(b"")
        return self.stakes[stake_key]

    @abimethod(readonly=True)
    def get_delegate(self, account: Account) -> Bytes:
        """
        Get the delegate address for an account.
        Returns 32-byte address or empty bytes if no delegation.
        """
        stake_key = account.bytes
        if not op.Box.get(b"d" + stake_key)[1]:
            return Bytes(b"")
        return self.delegations[stake_key]

    @abimethod(readonly=True)
    def get_total_staked(self) -> UInt64:
        """Get the total CORTEX currently staked across all users."""
        return self.total_staked

    # ------------------------------------------------------------------ #
    #  Reward pool management
    # ------------------------------------------------------------------ #

    @abimethod()
    def fund_reward_pool(
        self, cortex_transfer: gtxn.AssetTransferTransaction
    ) -> None:
        """
        Add CORTEX to the staking reward pool.
        Typically called by the protocol to distribute the 24% emission allocation.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert cortex_transfer.xfer_asset.id == self.cortex_token, "Wrong token"
        assert (
            cortex_transfer.asset_receiver == Global.current_application_address
        ), "Must send to contract"
        self.reward_pool = self.reward_pool + cortex_transfer.asset_amount

    # ------------------------------------------------------------------ #
    #  Admin
    # ------------------------------------------------------------------ #

    @abimethod()
    def update_lock_parameters(
        self, min_days: UInt64, max_days: UInt64, max_boost: UInt64
    ) -> None:
        """
        Update staking lock parameters. Only callable by creator.
        max_boost is in basis points (2500 = 2.5x).
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert min_days >= UInt64(1), "Minimum 1 day"
        assert max_days >= min_days, "Max must exceed min"
        assert max_boost >= UInt64(1000), "Boost must be at least 1x"
        assert max_boost <= UInt64(10000), "Boost cannot exceed 10x"
        self.MIN_LOCK_DAYS = min_days
        self.MAX_LOCK_DAYS = max_days
        self.MAX_BOOST = max_boost
