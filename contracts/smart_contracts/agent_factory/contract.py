from algopy import (
    ARC4Contract,
    String,
    UInt64,
    Asset,
    Txn,
    Global,
    BoxMap,
    itxn,
    gtxn,
    op
)
from algopy.arc4 import abimethod


class AgentFactory(ARC4Contract):
    def __init__(self) -> None:
        self.agent_supplies = BoxMap(UInt64, UInt64)
        self.latest_asset_id = UInt64(0)
        self.cortex_token = UInt64(0)
        self.BASE_PRICE = UInt64(10_000)
        self.SLOPE = UInt64(1_000)

    @abimethod()
    def bootstrap_protocol(self) -> UInt64:
        """
        Creates the master $CORTEX utility token.
        """
        assert self.cortex_token == UInt64(0), "Already bootstrapped"
        
        created_asset_tx = itxn.AssetConfig(
            asset_name="PureCortex",
            unit_name="CORTEX",
            total=UInt64(10_000_000_000_000_000),
            decimals=UInt64(6),
            manager=Global.current_application_address,
            url="https://purecortex.ai",
            fee=0
        ).submit()
        
        self.cortex_token = created_asset_tx.created_asset.id
        return self.cortex_token

    @abimethod()
    def create_agent(self, cortex_payment: gtxn.AssetTransferTransaction, name: String, unit_name: String) -> UInt64:
        """
        Creates a new Agent Token. Requires a 100 $CORTEX fee.
        """
        assert self.cortex_token != UInt64(0), "Protocol not bootstrapped"
        assert cortex_payment.xfer_asset.id == self.cortex_token, "Invalid fee asset"
        assert cortex_payment.asset_amount >= UInt64(100_000_000), "Fee must be 100 $CORTEX"
        assert cortex_payment.asset_receiver == Global.current_application_address, "Fee must go to factory"
        
        # Create the asset via Inner Transaction
        created_asset_tx = itxn.AssetConfig(
            asset_name=name,
            unit_name=unit_name,
            total=UInt64(1_000_000_000), # 1 Billion Max Supply
            decimals=UInt64(6),
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            freeze=Global.current_application_address,
            clawback=Global.current_application_address,
            fee=0
        ).submit()
        
        asset_id = created_asset_tx.created_asset.id
        self.latest_asset_id = asset_id
        
        return asset_id

    @abimethod(readonly=True)
    def calculate_buy_price(self, asset: Asset, amount: UInt64) -> UInt64:
        """
        Calculates ALGO required to buy 'amount' of tokens along the curve.
        """
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
    def buy_tokens(self, payment: gtxn.PaymentTransaction, asset: Asset, amount: UInt64) -> None:
        """
        Buys tokens from the bonding curve by paying ALGO.
        """
        assert payment.receiver == Global.current_application_address, "Payment must be directed to the factory contract"
        
        required_algo = self.calculate_buy_price(asset, amount)
        assert payment.amount >= required_algo, "Insufficient ALGO payment for requested amount"
        
        # Transfer the tokens to the buyer via Inner Transaction
        itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=Txn.sender,
            asset_amount=amount,
            fee=0
        ).submit()
        
        # Update or Create supply box
        current_supply = UInt64(0)
        if op.Box.get(op.itob(asset.id))[1]:
            current_supply = self.agent_supplies[asset.id]
            
        self.agent_supplies[asset.id] = current_supply + amount
