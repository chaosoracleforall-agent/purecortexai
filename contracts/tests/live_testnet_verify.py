import algokit_utils
from algosdk import transaction
from smart_contracts.artifacts.agent_factory.agent_factory_client import (
    AgentFactoryClient,
)
import os

def verify_on_testnet():
    # 1. Fetch Mnemonic securely from environment (assumes set during execution)
    mnemonic = os.getenv("DEPLOYER_MNEMONIC")
    if not mnemonic:
        print("Error: DEPLOYER_MNEMONIC not found in environment.")
        return

    algorand = algokit_utils.AlgorandClient.testnet()
    deployer = algorand.account.from_mnemonic(mnemonic=mnemonic)
    
    # App ID from your deployment
    app_id = 757089323
    
    app_client = AgentFactoryClient(
        algorand=algorand,
        app_id=app_id,
        default_sender=deployer.address
    )

    print(f"--- STARTING LIVE TESTNET AUDIT FOR APP ID: {app_id} ---")

    # Fund the contract before creating agent to cover MBR (0.1 ALGO for asset + 0.1 base)
    print(f"Funding contract {app_client.app_address} to cover MBR...")
    algorand.send.payment(
        algokit_utils.PaymentParams(
            sender=deployer.address,
            receiver=app_client.app_address,
            amount=algokit_utils.AlgoAmount(algo=1)
        )
    )

    # TEST A: Create an Agent (Inner Transaction Test)
    try:
        print("Testing: create_agent('Sentinel-X', 'SNX')...")
        
        # We simulate first to find the next asset ID (mocked for Box reference)
        # On Algorand, we need to provide the box name in the application call.
        # Since we don't know the exact Asset ID yet (it's created in the same call),
        # we have a chicken-and-egg problem for the box reference.
        # For this test, we skip box storage or use a known box if possible.
        
        result = app_client.send.create_agent(
            args=("Sentinel-X", "SNX"),
            params=algokit_utils.CommonAppCallParams(
                extra_fee=algokit_utils.AlgoAmount(micro_algo=1000)
                # Note: For production, AgentFactory should handle box creation safely
            )
        )
        asset_id = result.abi_return
        print(f"✅ SUCCESS: Agent Token Created! Asset ID: {asset_id}")
    except Exception as e:
        print(f"❌ FAILED: Agent Creation: {e}")
        # If box ref failed, it's likely the contract logic needs a tweak for 
        # auto-referencing boxes.
        asset_id = None

    # TEST B: Calculate Buy Price
    if asset_id:
        try:
            print(f"Testing: calculate_buy_price for Asset {asset_id}...")
            price = app_client.send.calculate_buy_price(args=(asset_id, 1000))
            print(f"✅ SUCCESS: 1000 tokens will cost {price.abi_return / 1_000_000} ALGO")
        except Exception as e:
            print(f"❌ FAILED: Price Calculation: {e}")

    print("--- LIVE AUDIT COMPLETE ---")

if __name__ == "__main__":
    verify_on_testnet()
