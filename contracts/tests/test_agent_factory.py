import pytest
from algopy import UInt64
from algopy_testing import algopy_testing_context
from smart_contracts.agent_factory.contract import AgentFactory


def test_initial_state():
    with algopy_testing_context() as ctx:
        contract = AgentFactory()
        assert contract.BASE_PRICE == UInt64(10_000)
        assert contract.SLOPE == UInt64(1_000)

def test_calculate_buy_price():
    with algopy_testing_context() as ctx:
        contract = AgentFactory()
        
        # We need to mock the box storage and asset ID
        mock_asset = ctx.any.asset()
        contract.agent_supplies[mock_asset.id] = UInt64(0)
        
        # Test buying 1000 tokens at supply 0
        amount = UInt64(1000)
        price = contract.calculate_buy_price(mock_asset, amount)
        
        # Calculation:
        # Base: 1000 * 10_000 = 10_000_000
        # Slope area: (0 * 1000 + (1000^2)//2) = 500_000
        # Slope cost: 1_000 * 500_000 = 500_000_000
        # Total = 510_000_000
        assert price == UInt64(510_000_000)


def test_calculate_sell_price():
    with algopy_testing_context() as ctx:
        contract = AgentFactory()
        mock_asset = ctx.any.asset()
        contract.agent_supplies[mock_asset.id] = UInt64(2_000)

        sell_price = contract.calculate_sell_price(mock_asset, UInt64(1_000))

        # Base: 1_000 * 10_000 = 10_000_000
        # Slope: 1_000 * (2_000^2 - 1_000^2) / 2 = 1_500_000_000
        # Gross: 1_510_000_000
        # 2% fee: 30_200_000
        # Net: 1_479_800_000
        assert sell_price == UInt64(1_479_800_000)


def test_check_graduation():
    with algopy_testing_context() as ctx:
        contract = AgentFactory()
        mock_asset = ctx.any.asset()
        contract.agent_supplies[mock_asset.id] = UInt64(10_000_000)

        assert contract.check_graduation(mock_asset) is True
