from algopy import (
    ARC4Contract,
    UInt64,
    Asset,
    Account,
    Txn,
    Global,
    Bytes,
    itxn,
    gtxn,
    op,
)
from algopy.arc4 import abimethod


class SovereignTreasury(ARC4Contract):
    """
    Sovereign Treasury contract for PureCortex.

    Receives protocol fee revenue (in ALGO) and splits it:
      - 90% -> buyback-and-burn pool (accumulates ALGO for periodic DEX swaps)
      - 10% -> Operations account

    Also provides a burn mechanism: CORTEX tokens sent to this contract
    can be permanently burned by sending them to the Algorand zero address.

    Revenue flow:
      AgentFactory fees -> Treasury.process_revenue() -> 90/10 split
      Treasury ALGO -> periodic Tinyman/Pact swap -> CORTEX -> burn
    """

    def __init__(self) -> None:
        self.cortex_token = UInt64(0)
        self.operations_address = Bytes()
        self.total_burned = UInt64(0)
        self.total_revenue = UInt64(0)
        self.buyback_balance = UInt64(0)  # ALGO accumulated for buyback
        self.buyback_pct = UInt64(90)  # 90% to buyback, 10% to operations

    # ------------------------------------------------------------------ #
    #  Initialization
    # ------------------------------------------------------------------ #

    @abimethod()
    def initialize(self, cortex_asset: Asset, ops_address: Account) -> None:
        """
        Initialize the treasury with the CORTEX token and operations address.
        Opts in to the CORTEX asset so the contract can receive and burn tokens.
        Only callable by the application creator.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert self.cortex_token == UInt64(0), "Already initialized"

        self.cortex_token = cortex_asset.id
        self.operations_address = ops_address.bytes

        # Opt-in to CORTEX so the contract can receive tokens for burning
        itxn.AssetTransfer(
            xfer_asset=cortex_asset,
            asset_receiver=Global.current_application_address,
            asset_amount=UInt64(0),
            fee=0,
        ).submit()

    # ------------------------------------------------------------------ #
    #  Revenue processing
    # ------------------------------------------------------------------ #

    @abimethod()
    def process_revenue(self, payment: gtxn.PaymentTransaction) -> None:
        """
        Process incoming ALGO revenue from protocol fees.

        Splits the payment:
          - buyback_pct% (default 90%) stays in contract for buyback-and-burn
          - remainder goes to the operations address

        The buyback ALGO accumulates until execute_buyback is called
        (which would swap on a DEX in production).
        """
        assert (
            payment.receiver == Global.current_application_address
        ), "Must pay treasury"
        assert payment.amount > UInt64(0), "Zero revenue"

        revenue = payment.amount
        self.total_revenue = self.total_revenue + revenue

        # Calculate split
        buyback_amount = (revenue * self.buyback_pct) // UInt64(100)
        ops_amount = revenue - buyback_amount

        # Track buyback balance
        self.buyback_balance = self.buyback_balance + buyback_amount

        # Send operations share immediately
        if ops_amount > UInt64(0):
            itxn.Payment(
                receiver=Account(self.operations_address),
                amount=ops_amount,
                fee=0,
            ).submit()

    # ------------------------------------------------------------------ #
    #  Buyback and burn
    # ------------------------------------------------------------------ #

    @abimethod()
    def execute_burn(
        self, cortex_transfer: gtxn.AssetTransferTransaction
    ) -> None:
        """
        Burn CORTEX tokens by sending them to the Algorand zero address.

        The caller must send CORTEX tokens to this contract in the same
        group transaction. The contract then forwards them to the zero
        address, permanently removing them from circulation.
        """
        assert cortex_transfer.xfer_asset.id == self.cortex_token, "Wrong token"
        assert (
            cortex_transfer.asset_receiver == Global.current_application_address
        ), "Must send to treasury"

        burn_amount = cortex_transfer.asset_amount
        assert burn_amount > UInt64(0), "Nothing to burn"

        # Send to Algorand zero address (permanent burn)
        itxn.AssetTransfer(
            xfer_asset=Asset(self.cortex_token),
            asset_receiver=Global.zero_address,
            asset_amount=burn_amount,
            fee=0,
        ).submit()

        self.total_burned = self.total_burned + burn_amount

    @abimethod()
    def withdraw_buyback_algo(self, amount: UInt64) -> None:
        """
        Withdraw accumulated buyback ALGO for off-chain DEX swap.

        In production, this would be replaced by an on-chain DEX integration
        (Tinyman, Pact, etc.). For now, the creator can withdraw ALGO to
        perform the swap manually and then call execute_burn with the
        purchased CORTEX.

        Only callable by the application creator.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert amount <= self.buyback_balance, "Exceeds buyback balance"
        assert amount > UInt64(0), "Zero withdrawal"

        itxn.Payment(
            receiver=Txn.sender,
            amount=amount,
            fee=0,
        ).submit()

        self.buyback_balance = self.buyback_balance - amount

    # ------------------------------------------------------------------ #
    #  Read-only queries
    # ------------------------------------------------------------------ #

    @abimethod(readonly=True)
    def get_total_burned(self) -> UInt64:
        """Get the total CORTEX tokens burned by this treasury."""
        return self.total_burned

    @abimethod(readonly=True)
    def get_total_revenue(self) -> UInt64:
        """Get the total ALGO revenue processed by this treasury."""
        return self.total_revenue

    @abimethod(readonly=True)
    def get_buyback_balance(self) -> UInt64:
        """Get the ALGO balance accumulated for buyback-and-burn."""
        return self.buyback_balance

    @abimethod(readonly=True)
    def get_treasury_stats(self) -> Bytes:
        """
        Get full treasury statistics.
        Returns 32 bytes: total_revenue(8) + total_burned(8) +
        buyback_balance(8) + buyback_pct(8).
        """
        return (
            op.itob(self.total_revenue)
            + op.itob(self.total_burned)
            + op.itob(self.buyback_balance)
            + op.itob(self.buyback_pct)
        )

    # ------------------------------------------------------------------ #
    #  Admin
    # ------------------------------------------------------------------ #

    @abimethod()
    def update_buyback_percentage(self, new_pct: UInt64) -> None:
        """
        Update the buyback-vs-operations split percentage.
        Only callable by the application creator.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert new_pct <= UInt64(100), "Cannot exceed 100%"
        assert new_pct >= UInt64(50), "Buyback must be at least 50%"
        self.buyback_pct = new_pct

    @abimethod()
    def update_operations_address(self, new_address: Account) -> None:
        """
        Update the operations wallet address.
        Only callable by the application creator.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        self.operations_address = new_address.bytes
