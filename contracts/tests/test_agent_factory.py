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
    scaled_area = area_doubled // token_scale
    slope_cost = (slope * scaled_area) // (2 * token_scale)
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
    sq_diff = (current_supply * current_supply) - (new_supply * new_supply)
    scaled_diff = sq_diff // token_scale
    slope_return = (slope * scaled_diff) // (2 * token_scale)
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


class TestBondingCurveOverflowSafety:
    """Boundary value tests verifying no UInt64 overflow at max parameters."""

    MAX_AGENT_SUPPLY = 1_000_000_000
    MAX_TX_AMOUNT = 100_000_000_000
    MIN_BUY = 1_000
    MAX_SLOPE = 10_000
    MAX_BASE_PRICE = 100_000
    TOKEN_SCALE = 1_000_000

    def _setup_agent(self, ctx, contract, *, base_price, slope, supply):
        mock_asset = ctx.any.asset()
        contract.agent_configs[mock_asset.id] = _agent_config_bytes(
            base_price=base_price,
            slope=slope,
            buy_fee_bps=100,
            sell_fee_bps=200,
            graduation_threshold=50_000_000_000,
        )
        contract.agent_supplies[mock_asset.id] = UInt64(supply)
        return mock_asset

    def test_buy_max_supply_max_slope_no_overflow(self):
        """Buy MAX_AGENT_SUPPLY tokens at MAX_SLOPE from zero supply."""
        with algopy_testing_context() as ctx:
            contract = AgentFactory()
            asset = self._setup_agent(
                ctx, contract,
                base_price=self.MAX_BASE_PRICE,
                slope=self.MAX_SLOPE,
                supply=0,
            )
            price = contract.calculate_buy_price(asset, UInt64(self.MAX_AGENT_SUPPLY))
            expected = _calculate_buy_price(
                current_supply=0,
                amount=self.MAX_AGENT_SUPPLY,
                base_price=self.MAX_BASE_PRICE,
                slope=self.MAX_SLOPE,
            )
            assert price == UInt64(expected)
            assert expected > 0

    def test_buy_min_amount_returns_nonzero_base(self):
        """Minimum buy (1000 micro-units) should produce a non-zero price from base_cost."""
        with algopy_testing_context() as ctx:
            contract = AgentFactory()
            asset = self._setup_agent(
                ctx, contract, base_price=10_000, slope=1_000, supply=0,
            )
            price = contract.calculate_buy_price(asset, UInt64(self.MIN_BUY))
            assert price > UInt64(0)

    def test_buy_near_max_supply_no_overflow(self):
        """Buy last 1000 units when supply is near max."""
        with algopy_testing_context() as ctx:
            contract = AgentFactory()
            remaining = self.MIN_BUY
            current = self.MAX_AGENT_SUPPLY - remaining
            asset = self._setup_agent(
                ctx, contract,
                base_price=self.MAX_BASE_PRICE,
                slope=self.MAX_SLOPE,
                supply=current,
            )
            price = contract.calculate_buy_price(asset, UInt64(remaining))
            expected = _calculate_buy_price(
                current_supply=current,
                amount=remaining,
                base_price=self.MAX_BASE_PRICE,
                slope=self.MAX_SLOPE,
            )
            assert price == UInt64(expected)

    def test_sell_max_supply_max_slope_no_overflow(self):
        """Sell entire supply at MAX_SLOPE."""
        with algopy_testing_context() as ctx:
            contract = AgentFactory()
            asset = self._setup_agent(
                ctx, contract,
                base_price=self.MAX_BASE_PRICE,
                slope=self.MAX_SLOPE,
                supply=self.MAX_AGENT_SUPPLY,
            )
            sell_price = contract.calculate_sell_price(asset, UInt64(self.MAX_AGENT_SUPPLY))
            expected = _calculate_sell_price(
                current_supply=self.MAX_AGENT_SUPPLY,
                amount=self.MAX_AGENT_SUPPLY,
                base_price=self.MAX_BASE_PRICE,
                slope=self.MAX_SLOPE,
                sell_fee_bps=200,
            )
            assert sell_price == UInt64(expected)
            assert expected > 0

    def test_sell_min_amount_at_high_supply(self):
        """Sell minimum amount when supply is at max."""
        with algopy_testing_context() as ctx:
            contract = AgentFactory()
            asset = self._setup_agent(
                ctx, contract,
                base_price=10_000,
                slope=self.MAX_SLOPE,
                supply=self.MAX_AGENT_SUPPLY,
            )
            sell_price = contract.calculate_sell_price(asset, UInt64(self.MIN_BUY))
            assert sell_price >= UInt64(0)

    def test_graduation_max_params_no_overflow(self):
        """check_graduation at MAX_AGENT_SUPPLY with MAX_SLOPE should not overflow."""
        with algopy_testing_context() as ctx:
            contract = AgentFactory()
            asset = self._setup_agent(
                ctx, contract,
                base_price=self.MAX_BASE_PRICE,
                slope=self.MAX_SLOPE,
                supply=self.MAX_AGENT_SUPPLY,
            )
            result = contract.check_graduation(asset)
            assert isinstance(result, bool)

    def test_buy_sell_symmetry_at_moderate_values(self):
        """Buy then sell same amount should return less due to fees."""
        with algopy_testing_context() as ctx:
            contract = AgentFactory()
            amount = 10_000_000  # 10 tokens
            asset = self._setup_agent(
                ctx, contract, base_price=10_000, slope=1_000, supply=0,
            )
            buy_price = contract.calculate_buy_price(asset, UInt64(amount))

            contract.agent_supplies[asset.id] = UInt64(amount)
            sell_price = contract.calculate_sell_price(asset, UInt64(amount))

            assert buy_price > UInt64(0)
            assert sell_price > UInt64(0)
            assert sell_price < buy_price

    def test_buy_price_monotonically_increases_with_supply(self):
        """Buying the same amount should cost more at higher supply levels."""
        with algopy_testing_context() as ctx:
            contract = AgentFactory()
            amount = 1_000_000
            prices = []
            for supply in [0, 100_000_000, 500_000_000, 900_000_000]:
                asset = self._setup_agent(
                    ctx, contract, base_price=10_000, slope=1_000, supply=supply,
                )
                price = contract.calculate_buy_price(asset, UInt64(amount))
                prices.append(int(price))
            for i in range(1, len(prices)):
                assert prices[i] >= prices[i - 1]


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
