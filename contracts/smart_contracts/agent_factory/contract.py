from algopy import (
    ARC4Contract,
    String,
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


class AgentFactory(ARC4Contract):
    def __init__(self) -> None:
        self.agent_supplies = BoxMap(UInt64, UInt64, key_prefix=b"")
        self.latest_asset_id = UInt64(0)
        self.cortex_token = UInt64(0)
        self.BASE_PRICE = UInt64(10_000)
        self.SLOPE = UInt64(1_000)

        # Dynamic fee parameters
        self.buy_fee_bps = UInt64(100)  # 1% buy fee
        self.sell_fee_bps = UInt64(200)  # 2% sell fee
        self.creation_fee = UInt64(100_000_000)  # 100 CORTEX (6 decimals)

        # Graduation threshold: 50,000 CORTEX worth of ALGO locked in curve
        self.GRADUATION_THRESHOLD = UInt64(50_000_000_000)

        # Maximum per-transaction amount to prevent uint64 overflow in bonding curve math
        # 100K tokens with 6 decimals = 100_000_000_000
        self.MAX_TX_AMOUNT = UInt64(100_000_000_000)

    # ------------------------------------------------------------------ #
    #  Bootstrap
    # ------------------------------------------------------------------ #

    @abimethod()
    def bootstrap_protocol(self) -> UInt64:
        """
        Creates the master $CORTEX utility token.
        Only callable by the application creator.
        """
        assert Txn.sender == Global.creator_address, "Only creator can bootstrap"
        assert self.cortex_token == UInt64(0), "Already bootstrapped"

        created_asset_tx = itxn.AssetConfig(
            asset_name="PURECORTEX",
            unit_name="CORTEX",
            total=UInt64(10_000_000_000_000_000),
            decimals=UInt64(6),
            manager=Global.current_application_address,
            url="https://purecortex.ai",
            fee=0,
        ).submit()

        self.cortex_token = created_asset_tx.created_asset.id
        return self.cortex_token

    # ------------------------------------------------------------------ #
    #  Agent creation
    # ------------------------------------------------------------------ #

    @abimethod()
    def create_agent(
        self,
        cortex_payment: gtxn.AssetTransferTransaction,
        name: String,
        unit_name: String,
    ) -> UInt64:
        """
        Creates a new Agent Token. Requires a CORTEX fee (default 100).
        """
        assert self.cortex_token != UInt64(0), "Protocol not bootstrapped"
        assert name.bytes.length > UInt64(0), "Name cannot be empty"
        assert name.bytes.length <= UInt64(32), "Name too long (max 32 bytes)"
        assert unit_name.bytes.length > UInt64(0), "Unit name cannot be empty"
        assert unit_name.bytes.length <= UInt64(8), "Unit name too long (max 8 bytes)"
        assert cortex_payment.sender == Txn.sender, "Fee sender must match caller"
        assert cortex_payment.xfer_asset.id == self.cortex_token, "Invalid fee asset"
        assert cortex_payment.asset_amount >= self.creation_fee, "Insufficient creation fee"
        assert (
            cortex_payment.asset_receiver == Global.current_application_address
        ), "Fee must go to factory"

        # Create the asset via Inner Transaction
        created_asset_tx = itxn.AssetConfig(
            asset_name=name,
            unit_name=unit_name,
            total=UInt64(1_000_000_000),  # 1 Billion Max Supply
            decimals=UInt64(6),
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            freeze=Global.current_application_address,
            clawback=Global.current_application_address,
            fee=0,
        ).submit()

        asset_id = created_asset_tx.created_asset.id
        self.latest_asset_id = asset_id

        # Initialize supply tracking box for the new agent token
        self.agent_supplies[asset_id] = UInt64(0)

        return asset_id

    # ------------------------------------------------------------------ #
    #  Bonding curve — buy
    # ------------------------------------------------------------------ #

    @abimethod(readonly=True)
    def calculate_buy_price(self, asset: Asset, amount: UInt64) -> UInt64:
        """
        Calculates ALGO required to buy 'amount' of tokens along the curve.
        Price = integral of (BASE_PRICE + SLOPE * supply) from S to S+amount.
        """
        assert amount > UInt64(0), "Amount must be positive"
        assert amount <= UInt64(1_000_000_000), "Amount exceeds max supply"
        assert amount <= self.MAX_TX_AMOUNT, "Amount exceeds max per-transaction limit"

        # If box doesn't exist, assume supply 0
        current_supply = UInt64(0)
        if op.Box.get(op.itob(asset.id))[1]:
            current_supply = self.agent_supplies[asset.id]

        base_cost = amount * self.BASE_PRICE

        two_supply_amount = UInt64(2) * current_supply * amount
        amount_sq = amount * amount
        area_doubled = two_supply_amount + amount_sq

        slope_cost = (self.SLOPE * area_doubled) // UInt64(2)

        return base_cost + slope_cost

    @abimethod()
    def buy_tokens(
        self, payment: gtxn.PaymentTransaction, asset: Asset, amount: UInt64
    ) -> None:
        """
        Buys tokens from the bonding curve by paying ALGO.
        A buy fee (default 1%) is added on top of the curve price.
        """
        assert payment.sender == Txn.sender, "Payment sender must match caller"
        assert (
            payment.receiver == Global.current_application_address
        ), "Payment must be directed to the factory contract"

        assert amount >= UInt64(1_000), "Minimum buy is 1000 micro-units"
        assert amount <= self.MAX_TX_AMOUNT, "Amount exceeds max per-transaction limit"

        required_algo = self.calculate_buy_price(asset, amount)

        # Apply buy fee
        fee = (required_algo * self.buy_fee_bps) // UInt64(10_000)
        total_required = required_algo + fee
        assert (
            payment.amount == total_required
        ), "Payment must exactly match required ALGO including fee"

        # Update state BEFORE external interaction (checks-effects-interactions)
        current_supply = UInt64(0)
        if op.Box.get(op.itob(asset.id))[1]:
            current_supply = self.agent_supplies[asset.id]
        self.agent_supplies[asset.id] = current_supply + amount

        # Transfer the tokens to the buyer via Inner Transaction
        itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=Txn.sender,
            asset_amount=amount,
            fee=0,
        ).submit()

    # ------------------------------------------------------------------ #
    #  Bonding curve — sell
    # ------------------------------------------------------------------ #

    @abimethod(readonly=True)
    def calculate_sell_price(self, asset: Asset, amount: UInt64) -> UInt64:
        """
        Calculate ALGO returned for selling 'amount' tokens.
        Integral of curve from (supply - amount) to supply, minus sell fee.
        """
        assert amount > UInt64(0), "Amount must be positive"

        current_supply = UInt64(0)
        if op.Box.get(op.itob(asset.id))[1]:
            current_supply = self.agent_supplies[asset.id]

        assert current_supply >= amount, "Cannot sell more than supply"

        new_supply = current_supply - amount

        # Base component
        base_cost = amount * self.BASE_PRICE

        # Slope area: SLOPE * (current_supply^2 - new_supply^2) / 2
        current_sq = current_supply * current_supply
        new_sq = new_supply * new_supply
        slope_cost = (self.SLOPE * (current_sq - new_sq)) // UInt64(2)

        # Gross before fee
        gross = base_cost + slope_cost

        # Apply sell fee (default 2%) — fee stays in the protocol
        fee = (gross * self.sell_fee_bps) // UInt64(10_000)
        return gross - fee

    @abimethod()
    def sell_tokens(
        self,
        token_transfer: gtxn.AssetTransferTransaction,
        asset: Asset,
        amount: UInt64,
    ) -> None:
        """
        Sells tokens back to the bonding curve for ALGO.
        The seller must send an asset transfer of the agent token to the contract
        in the same group transaction.
        """
        assert token_transfer.sender == Txn.sender, "Token sender must match caller"
        assert token_transfer.xfer_asset.id == asset.id, "Wrong asset"
        assert token_transfer.asset_amount == amount, "Token amount must exactly match sell amount"
        assert amount >= UInt64(1_000), "Minimum sell is 1000 micro-units"
        assert amount <= self.MAX_TX_AMOUNT, "Amount exceeds max per-transaction limit"
        assert (
            token_transfer.asset_receiver == Global.current_application_address
        ), "Tokens must go to factory"

        # Calculate sell price (accounts for fee internally)
        sell_price = self.calculate_sell_price(asset, amount)

        # Update state BEFORE external interaction (checks-effects-interactions)
        current_supply = self.agent_supplies[asset.id]
        self.agent_supplies[asset.id] = current_supply - amount

        # Pay ALGO to seller via inner transaction
        itxn.Payment(
            receiver=Txn.sender,
            amount=sell_price,
            fee=0,
        ).submit()

    # ------------------------------------------------------------------ #
    #  Graduation
    # ------------------------------------------------------------------ #

    @abimethod(readonly=True)
    def check_graduation(self, asset: Asset) -> bool:
        """
        Check if an agent token has met the graduation threshold.
        Graduation means the total value locked in the bonding curve exceeds
        the configured threshold, signaling readiness for DEX listing.
        """
        if not op.Box.get(op.itob(asset.id))[1]:
            return False

        current_supply = self.agent_supplies[asset.id]
        if current_supply == UInt64(0):
            return False

        # Total value locked = what selling all supply would return (pre-fee)
        # We compute gross curve value without the sell fee for this check
        base_cost = current_supply * self.BASE_PRICE
        current_sq = current_supply * current_supply
        slope_cost = (self.SLOPE * current_sq) // UInt64(2)
        total_value = base_cost + slope_cost

        return total_value >= self.GRADUATION_THRESHOLD

    # ------------------------------------------------------------------ #
    #  CORTEX distribution (testnet / airdrop)
    # ------------------------------------------------------------------ #

    @abimethod()
    def distribute_cortex(self, receiver: Account, amount: UInt64) -> None:
        """
        Distribute CORTEX tokens from the factory escrow.
        Only callable by the application creator.
        Used for testnet distribution and genesis airdrop.
        """
        assert Txn.sender == Global.creator_address, "Only creator can distribute"
        assert self.cortex_token != UInt64(0), "Protocol not bootstrapped"
        assert amount > UInt64(0), "Amount must be positive"
        assert amount <= UInt64(1_000_000_000_000), "Max 1M CORTEX per distribution"

        itxn.AssetTransfer(
            xfer_asset=Asset(self.cortex_token),
            asset_receiver=receiver,
            asset_amount=amount,
            fee=0,
        ).submit()

    # ------------------------------------------------------------------ #
    #  Governance / Admin
    # ------------------------------------------------------------------ #

    @abimethod()
    def update_fee_parameters(
        self, buy_fee: UInt64, sell_fee: UInt64
    ) -> None:
        """
        Update fee parameters.
        Only callable by the application creator (later: governance contract).
        Fees are in basis points (100 = 1%). Max 10%.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert buy_fee >= UInt64(10), "Min buy fee is 0.1%"
        assert buy_fee <= UInt64(1000), "Max buy fee is 10%"
        assert sell_fee >= UInt64(10), "Min sell fee is 0.1%"
        assert sell_fee <= UInt64(1000), "Max sell fee is 10%"
        self.buy_fee_bps = buy_fee
        self.sell_fee_bps = sell_fee

    @abimethod()
    def update_creation_fee(self, new_fee: UInt64) -> None:
        """
        Update agent creation fee (in CORTEX micro-units).
        Only callable by the application creator.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert new_fee >= UInt64(1_000_000), "Minimum creation fee is 1 CORTEX"
        self.creation_fee = new_fee

    @abimethod()
    def update_graduation_threshold(self, new_threshold: UInt64) -> None:
        """
        Update the graduation threshold.
        Only callable by the application creator.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert new_threshold > UInt64(0), "Threshold must be positive"
        self.GRADUATION_THRESHOLD = new_threshold
