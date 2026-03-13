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
        # Maps Asset ID to its current circulating supply
        self.agent_supplies = BoxMap(UInt64, UInt64)
        
        # Track the last created asset ID globally for easy discovery
        self.latest_asset_id = UInt64(0)
        
        # Bonding Curve Constants (Hybrid Linear model)
        self.BASE_PRICE = UInt64(10_000) # MicroAlgos (0.01 ALGO base)
        self.SLOPE = UInt64(1_000) # MicroAlgos increase per token issued

    @abimethod()
    def create_agent(self, name: String, unit_name: String) -> UInt64:
        """
        Creates a new Agent Token and initializes its bonding curve state.
        Returns the ID of the newly created Asset.
        """
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
        
        # We don't initialize the box here to avoid required box references 
        # in the same transaction as creation. 
        # The first buy_tokens call will create the box.
        
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
