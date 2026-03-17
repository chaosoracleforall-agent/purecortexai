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
        # Separate per-agent boxes let clients read immutable curve parameters
        # independently from the live minted supply.
        self.agent_configs = BoxMap(UInt64, Bytes, key_prefix=b"c")
        self.agent_supplies = BoxMap(UInt64, UInt64, key_prefix=b"s")
        self.latest_asset_id = UInt64(0)
        self.pending_asset_id = UInt64(0)
        self.pending_base_price = UInt64(0)
        self.pending_slope = UInt64(0)
        self.pending_buy_fee_bps = UInt64(0)
        self.pending_sell_fee_bps = UInt64(0)
        self.pending_graduation_threshold = UInt64(0)
        self.pending_supply = UInt64(0)
        self.cortex_token = UInt64(0)

        # Default launch parameters used when a creator does not override them.
        self.BASE_PRICE = UInt64(10_000)
        self.SLOPE = UInt64(1_000)
        self.TOKEN_SCALE = UInt64(1_000_000)  # 6-decimal agent token precision

        # Default fee parameters applied to new launches unless overridden.
        self.buy_fee_bps = UInt64(100)  # 1% buy fee
        self.sell_fee_bps = UInt64(200)  # 2% sell fee
        self.creation_fee = UInt64(100_000_000)  # 100 CORTEX (6 decimals)

        # Default graduation threshold: 50,000 CORTEX worth of ALGO locked in curve
        self.GRADUATION_THRESHOLD = UInt64(50_000_000_000)

        # Maximum per-transaction amount to prevent uint64 overflow in bonding curve math
        # 100K tokens with 6 decimals = 100_000_000_000
        self.MAX_TX_AMOUNT = UInt64(100_000_000_000)

        # Protocol-wide launch guardrails.
        self.MIN_BASE_PRICE = UInt64(1_000)
        self.MAX_BASE_PRICE = UInt64(100_000)
        self.MIN_SLOPE = UInt64(1)
        self.MAX_SLOPE = UInt64(10_000)
        self.MIN_FEE_BPS = UInt64(0)
        self.MAX_FEE_BPS = UInt64(1_000)
        self.MIN_GRADUATION_THRESHOLD = UInt64(1_000_000_000)
        self.MAX_GRADUATION_THRESHOLD = UInt64(500_000_000_000)
        self.MAX_AGENT_SUPPLY = UInt64(1_000_000_000)

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _agent_config_exists(self, asset_id: UInt64) -> bool:
        return op.Box.get(b"c" + op.itob(asset_id))[1]

    def _agent_supply_exists(self, asset_id: UInt64) -> bool:
        return op.Box.get(b"s" + op.itob(asset_id))[1]

    def _require_agent_config(self, asset_id: UInt64) -> Bytes:
        if self._agent_config_exists(asset_id):
            return self.agent_configs[asset_id]
        assert self.pending_asset_id == asset_id, "Agent config not found"
        return self._encode_agent_config(
            self.pending_base_price,
            self.pending_slope,
            self.pending_buy_fee_bps,
            self.pending_sell_fee_bps,
            self.pending_graduation_threshold,
        )

    def _get_agent_supply(self, asset_id: UInt64) -> UInt64:
        if self._agent_supply_exists(asset_id):
            return self.agent_supplies[asset_id]
        if self.pending_asset_id == asset_id:
            return self.pending_supply
        return UInt64(0)

    def _clear_pending_agent(self) -> None:
        self.pending_asset_id = UInt64(0)
        self.pending_base_price = UInt64(0)
        self.pending_slope = UInt64(0)
        self.pending_buy_fee_bps = UInt64(0)
        self.pending_sell_fee_bps = UInt64(0)
        self.pending_graduation_threshold = UInt64(0)
        self.pending_supply = UInt64(0)

    def _encode_agent_config(
        self,
        base_price: UInt64,
        slope: UInt64,
        buy_fee_bps: UInt64,
        sell_fee_bps: UInt64,
        graduation_threshold: UInt64,
    ) -> Bytes:
        return (
            op.itob(base_price)
            + op.itob(slope)
            + op.itob(buy_fee_bps)
            + op.itob(sell_fee_bps)
            + op.itob(graduation_threshold)
        )

    def _validate_launch_params(
        self,
        base_price: UInt64,
        slope: UInt64,
        buy_fee_bps: UInt64,
        sell_fee_bps: UInt64,
        graduation_threshold: UInt64,
    ) -> None:
        assert (
            base_price >= self.MIN_BASE_PRICE
        ), "Base price below protocol minimum"
        assert (
            base_price <= self.MAX_BASE_PRICE
        ), "Base price above protocol maximum"
        assert slope >= self.MIN_SLOPE, "Slope below protocol minimum"
        assert slope <= self.MAX_SLOPE, "Slope above protocol maximum"
        assert buy_fee_bps >= self.MIN_FEE_BPS, "Buy fee below protocol minimum"
        assert buy_fee_bps <= self.MAX_FEE_BPS, "Buy fee above protocol maximum"
        assert (
            sell_fee_bps >= self.MIN_FEE_BPS
        ), "Sell fee below protocol minimum"
        assert (
            sell_fee_bps <= self.MAX_FEE_BPS
        ), "Sell fee above protocol maximum"
        assert (
            graduation_threshold >= self.MIN_GRADUATION_THRESHOLD
        ), "Graduation threshold below protocol minimum"
        assert (
            graduation_threshold <= self.MAX_GRADUATION_THRESHOLD
        ), "Graduation threshold above protocol maximum"

    def _resolve_graduation_threshold(self, graduation_threshold_override: UInt64) -> UInt64:
        if graduation_threshold_override == UInt64(0):
            return self.GRADUATION_THRESHOLD
        return graduation_threshold_override

    def _get_config_base_price(self, config_data: Bytes) -> UInt64:
        return op.btoi(op.extract(config_data, 0, 8))

    def _get_config_slope(self, config_data: Bytes) -> UInt64:
        return op.btoi(op.extract(config_data, 8, 8))

    def _get_config_buy_fee_bps(self, config_data: Bytes) -> UInt64:
        return op.btoi(op.extract(config_data, 16, 8))

    def _get_config_sell_fee_bps(self, config_data: Bytes) -> UInt64:
        return op.btoi(op.extract(config_data, 24, 8))

    def _get_config_graduation_threshold(self, config_data: Bytes) -> UInt64:
        return op.btoi(op.extract(config_data, 32, 8))

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
        base_price: UInt64,
        slope: UInt64,
        buy_fee_bps: UInt64,
        sell_fee_bps: UInt64,
        graduation_threshold_override: UInt64,
    ) -> UInt64:
        """
        Creates a new Agent Token with immutable per-agent curve parameters.
        Requires the CORTEX creation fee and enforces bounded launch settings.
        """
        assert self.cortex_token != UInt64(0), "Protocol not bootstrapped"
        assert (
            self.pending_asset_id == UInt64(0)
        ), "Finalize pending agent configuration before creating another agent"
        assert name.bytes.length > UInt64(0), "Name cannot be empty"
        assert name.bytes.length <= UInt64(32), "Name too long (max 32 bytes)"
        assert unit_name.bytes.length > UInt64(0), "Unit name cannot be empty"
        assert unit_name.bytes.length <= UInt64(8), "Unit name too long (max 8 bytes)"

        graduation_threshold = self._resolve_graduation_threshold(
            graduation_threshold_override
        )
        self._validate_launch_params(
            base_price,
            slope,
            buy_fee_bps,
            sell_fee_bps,
            graduation_threshold,
        )

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
        # Defer per-agent box materialization until the asset id is known to clients.
        self.pending_asset_id = asset_id
        self.pending_base_price = base_price
        self.pending_slope = slope
        self.pending_buy_fee_bps = buy_fee_bps
        self.pending_sell_fee_bps = sell_fee_bps
        self.pending_graduation_threshold = graduation_threshold
        self.pending_supply = UInt64(0)

        return asset_id

    @abimethod()
    def finalize_agent_config(self, asset: Asset) -> None:
        """
        Materialize the pending agent config/supply into `c`/`s` boxes once
        the created asset id is known to the caller for box references.
        """
        assert self.pending_asset_id == asset.id, "No pending config for this asset"
        assert not self._agent_config_exists(asset.id), "Agent config already finalized"
        self.agent_configs[asset.id] = self._encode_agent_config(
            self.pending_base_price,
            self.pending_slope,
            self.pending_buy_fee_bps,
            self.pending_sell_fee_bps,
            self.pending_graduation_threshold,
        )
        self.agent_supplies[asset.id] = self.pending_supply
        self._clear_pending_agent()

    @abimethod(readonly=True)
    def get_agent_config(self, asset: Asset) -> Bytes:
        """Return the packed per-agent launch configuration."""
        return self._require_agent_config(asset.id)

    @abimethod(readonly=True)
    def get_agent_supply(self, asset: Asset) -> UInt64:
        """Return the authoritative live curve supply for an agent."""
        assert (
            self._agent_config_exists(asset.id) or self.pending_asset_id == asset.id
        ), "Agent config not found"
        return self._get_agent_supply(asset.id)

    # ------------------------------------------------------------------ #
    #  Bonding curve — buy
    # ------------------------------------------------------------------ #

    @abimethod(readonly=True)
    def calculate_buy_price(self, asset: Asset, amount: UInt64) -> UInt64:
        """
        Calculates ALGO required to buy 'amount' of tokens along the curve.
        Price = integral of (BASE_PRICE + SLOPE * supply) from S to S+amount.
        """
        config_data = self._require_agent_config(asset.id)
        assert amount > UInt64(0), "Amount must be positive"
        assert amount <= self.MAX_AGENT_SUPPLY, "Amount exceeds max supply"
        assert amount <= self.MAX_TX_AMOUNT, "Amount exceeds max per-transaction limit"

        base_price = self._get_config_base_price(config_data)
        slope = self._get_config_slope(config_data)
        current_supply = self._get_agent_supply(asset.id)

        # Convert micro-token units into whole-token price space so user-facing
        # token decimals do not explode the curve math.
        base_cost = (amount * base_price) // self.TOKEN_SCALE

        two_supply_amount = UInt64(2) * current_supply * amount
        amount_sq = amount * amount
        area_doubled = two_supply_amount + amount_sq

        slope_cost = (slope * area_doubled) // (
            UInt64(2) * self.TOKEN_SCALE * self.TOKEN_SCALE
        )

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

        config_data = self._require_agent_config(asset.id)
        required_algo = self.calculate_buy_price(asset, amount)

        # Apply the per-agent buy fee.
        fee = (required_algo * self._get_config_buy_fee_bps(config_data)) // UInt64(10_000)
        total_required = required_algo + fee
        assert (
            payment.amount == total_required
        ), "Payment must exactly match required ALGO including fee"

        # Update state BEFORE external interaction (checks-effects-interactions)
        current_supply = self._get_agent_supply(asset.id)
        assert (
            current_supply + amount <= self.MAX_AGENT_SUPPLY
        ), "Buy exceeds remaining agent supply"
        if self.pending_asset_id == asset.id and not self._agent_supply_exists(asset.id):
            self.pending_supply = current_supply + amount
        else:
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
        config_data = self._require_agent_config(asset.id)
        assert amount > UInt64(0), "Amount must be positive"

        base_price = self._get_config_base_price(config_data)
        slope = self._get_config_slope(config_data)
        current_supply = self._get_agent_supply(asset.id)

        assert current_supply >= amount, "Cannot sell more than supply"

        new_supply = current_supply - amount

        # Base component
        base_cost = (amount * base_price) // self.TOKEN_SCALE

        # Slope area: SLOPE * (current_supply^2 - new_supply^2) / 2
        current_sq = current_supply * current_supply
        new_sq = new_supply * new_supply
        slope_cost = (slope * (current_sq - new_sq)) // (
            UInt64(2) * self.TOKEN_SCALE * self.TOKEN_SCALE
        )

        # Gross before fee
        gross = base_cost + slope_cost

        # Apply the per-agent sell fee — fee stays in the protocol.
        fee = (gross * self._get_config_sell_fee_bps(config_data)) // UInt64(10_000)
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
        current_supply = self._get_agent_supply(asset.id)
        if self.pending_asset_id == asset.id and not self._agent_supply_exists(asset.id):
            self.pending_supply = current_supply - amount
        else:
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
        if not self._agent_config_exists(asset.id) and self.pending_asset_id != asset.id:
            return False

        config_data = self._require_agent_config(asset.id)
        current_supply = self._get_agent_supply(asset.id)
        if current_supply == UInt64(0):
            return False

        # Total value locked = what selling all supply would return (pre-fee)
        # We compute gross curve value without the sell fee for this check
        base_price = self._get_config_base_price(config_data)
        slope = self._get_config_slope(config_data)
        graduation_threshold = self._get_config_graduation_threshold(config_data)

        base_cost = (current_supply * base_price) // self.TOKEN_SCALE
        current_sq = current_supply * current_supply
        slope_cost = (slope * current_sq) // (
            UInt64(2) * self.TOKEN_SCALE * self.TOKEN_SCALE
        )
        total_value = base_cost + slope_cost

        return total_value >= graduation_threshold

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
        Update the default launch fee parameters used for future agent creation.
        Existing agent configs remain immutable once created.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert buy_fee >= self.MIN_FEE_BPS, "Buy fee below protocol minimum"
        assert buy_fee <= self.MAX_FEE_BPS, "Buy fee above protocol maximum"
        assert sell_fee >= self.MIN_FEE_BPS, "Sell fee below protocol minimum"
        assert sell_fee <= self.MAX_FEE_BPS, "Sell fee above protocol maximum"
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
        Update the default graduation threshold for future agent launches.
        Existing agent configs remain immutable once created.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert (
            new_threshold >= self.MIN_GRADUATION_THRESHOLD
        ), "Threshold below protocol minimum"
        assert (
            new_threshold <= self.MAX_GRADUATION_THRESHOLD
        ), "Threshold above protocol maximum"
        self.GRADUATION_THRESHOLD = new_threshold
