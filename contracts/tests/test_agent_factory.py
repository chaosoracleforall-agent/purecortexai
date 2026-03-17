import pytest
from algopy import Bytes, UInt64
from algopy_testing import algopy_testing_context

from smart_contracts.agent_factory.contract import AgentFactory


def _agent_config_bytes(
    *,
    base_price: int,
    slope: int,
    buy_fee_bps: int,
    sell_fee_bps: int,
    graduation_threshold: int,
) -> Bytes:
    return Bytes(
        base_price.to_bytes(8, "big")
        + slope.to_bytes(8, "big")
        + buy_fee_bps.to_bytes(8, "big")
        + sell_fee_bps.to_bytes(8, "big")
        + graduation_threshold.to_bytes(8, "big")
    )


def _calculate_buy_price(
    *,
    current_supply: int,
    amount: int,
    base_price: int,
    slope: int,
    token_scale: int = 1_000_000,
) -> int:
    base_cost = (amount * base_price) // token_scale
    area_doubled = (2 * current_supply * amount) + (amount * amount)
    slope_cost = (slope * area_doubled) // (2 * token_scale * token_scale)
    return base_cost + slope_cost


def _calculate_sell_price(
    *,
    current_supply: int,
    amount: int,
    base_price: int,
    slope: int,
    sell_fee_bps: int,
    token_scale: int = 1_000_000,
) -> int:
    new_supply = current_supply - amount
    base_return = (amount * base_price) // token_scale
    slope_return = (slope * ((current_supply * current_supply) - (new_supply * new_supply))) // (
        2 * token_scale * token_scale
    )
    gross = base_return + slope_return
    fee = (gross * sell_fee_bps) // 10_000
    return gross - fee


def test_initial_state():
    with algopy_testing_context():
        contract = AgentFactory()
        assert contract.BASE_PRICE == UInt64(10_000)
        assert contract.SLOPE == UInt64(1_000)
        assert contract.buy_fee_bps == UInt64(100)
        assert contract.sell_fee_bps == UInt64(200)
        assert contract.GRADUATION_THRESHOLD == UInt64(50_000_000_000)
        assert contract.MIN_BASE_PRICE == UInt64(1_000)
        assert contract.MAX_BASE_PRICE == UInt64(100_000)
        assert contract.MAX_AGENT_SUPPLY == UInt64(1_000_000_000)


def test_get_agent_config_and_supply_use_separate_box_state():
    with algopy_testing_context() as ctx:
        contract = AgentFactory()
        mock_asset = ctx.any.asset()
        config_data = _agent_config_bytes(
            base_price=12_000,
            slope=700,
            buy_fee_bps=125,
            sell_fee_bps=250,
            graduation_threshold=7_500_000_000,
        )

        contract.agent_configs[mock_asset.id] = config_data
        contract.agent_supplies[mock_asset.id] = UInt64(3_500_000)

        assert contract.get_agent_config(mock_asset) == config_data
        assert contract.get_agent_supply(mock_asset) == UInt64(3_500_000)


def test_calculate_buy_price_uses_scaled_agent_specific_curve():
    with algopy_testing_context() as ctx:
        contract = AgentFactory()
        mock_asset = ctx.any.asset()
        current_supply = 3_000_000
        amount = 2_000_000
        base_price = 20_000
        slope = 2_000

        contract.agent_configs[mock_asset.id] = _agent_config_bytes(
            base_price=base_price,
            slope=slope,
            buy_fee_bps=100,
            sell_fee_bps=200,
            graduation_threshold=50_000_000_000,
        )
        contract.agent_supplies[mock_asset.id] = UInt64(current_supply)

        price = contract.calculate_buy_price(mock_asset, UInt64(amount))
        expected = _calculate_buy_price(
            current_supply=current_supply,
            amount=amount,
            base_price=base_price,
            slope=slope,
        )

        assert price == UInt64(expected)


def test_calculate_sell_price_uses_agent_specific_fee():
    with algopy_testing_context() as ctx:
        contract = AgentFactory()
        mock_asset = ctx.any.asset()
        current_supply = 8_000_000
        amount = 2_000_000
        base_price = 15_000
        slope = 1_500
        sell_fee_bps = 350

        contract.agent_configs[mock_asset.id] = _agent_config_bytes(
            base_price=base_price,
            slope=slope,
            buy_fee_bps=100,
            sell_fee_bps=sell_fee_bps,
            graduation_threshold=50_000_000_000,
        )
        contract.agent_supplies[mock_asset.id] = UInt64(current_supply)

        sell_price = contract.calculate_sell_price(mock_asset, UInt64(amount))
        expected = _calculate_sell_price(
            current_supply=current_supply,
            amount=amount,
            base_price=base_price,
            slope=slope,
            sell_fee_bps=sell_fee_bps,
        )

        assert sell_price == UInt64(expected)


def test_check_graduation_uses_agent_specific_override_threshold():
    with algopy_testing_context() as ctx:
        contract = AgentFactory()
        mock_asset = ctx.any.asset()
        contract.agent_configs[mock_asset.id] = _agent_config_bytes(
            base_price=40_000,
            slope=0,
            buy_fee_bps=100,
            sell_fee_bps=200,
            graduation_threshold=300_000,
        )
        contract.agent_supplies[mock_asset.id] = UInt64(10_000_000)

        assert contract.check_graduation(mock_asset) is True


def test_resolve_graduation_threshold_uses_default_when_zero():
    with algopy_testing_context():
        contract = AgentFactory()
        assert contract._resolve_graduation_threshold(UInt64(0)) == contract.GRADUATION_THRESHOLD
        assert contract._resolve_graduation_threshold(UInt64(9_000_000_000)) == UInt64(9_000_000_000)


def test_validate_launch_params_enforces_protocol_guardrails():
    with algopy_testing_context():
        contract = AgentFactory()

        contract._validate_launch_params(
            UInt64(10_000),
            UInt64(1_000),
            UInt64(100),
            UInt64(200),
            UInt64(50_000_000_000),
        )

        with pytest.raises(AssertionError):
            contract._validate_launch_params(
                UInt64(999),
                UInt64(1_000),
                UInt64(100),
                UInt64(200),
                UInt64(50_000_000_000),
            )

        with pytest.raises(AssertionError):
            contract._validate_launch_params(
                UInt64(10_000),
                UInt64(20_000),
                UInt64(100),
                UInt64(200),
                UInt64(50_000_000_000),
            )

        with pytest.raises(AssertionError):
            contract._validate_launch_params(
                UInt64(10_000),
                UInt64(1_000),
                UInt64(1_100),
                UInt64(200),
                UInt64(50_000_000_000),
            )

        with pytest.raises(AssertionError):
            contract._validate_launch_params(
                UInt64(10_000),
                UInt64(1_000),
                UInt64(100),
                UInt64(200),
                UInt64(999_999_999),
            )
