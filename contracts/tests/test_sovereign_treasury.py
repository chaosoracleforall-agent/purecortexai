from algopy import Bytes, UInt64
from algopy_testing import algopy_testing_context

from smart_contracts.sovereign_treasury.contract import SovereignTreasury


def test_treasury_initial_state():
    with algopy_testing_context():
        contract = SovereignTreasury()
        assert contract.cortex_token == UInt64(0)
        assert contract.total_burned == UInt64(0)
        assert contract.total_revenue == UInt64(0)
        assert contract.buyback_balance == UInt64(0)
        assert contract.buyback_pct == UInt64(90)


def test_treasury_read_only_stats_are_encoded_consistently():
    with algopy_testing_context():
        contract = SovereignTreasury()
        contract.total_revenue = UInt64(1_250_000)
        contract.total_burned = UInt64(12_000_000)
        contract.buyback_balance = UInt64(900_000)
        contract.buyback_pct = UInt64(92)

        assert contract.get_total_revenue() == UInt64(1_250_000)
        assert contract.get_total_burned() == UInt64(12_000_000)
        assert contract.get_buyback_balance() == UInt64(900_000)
        assert contract.get_treasury_stats() == Bytes(
            (1_250_000).to_bytes(8, "big")
            + (12_000_000).to_bytes(8, "big")
            + (900_000).to_bytes(8, "big")
            + (92).to_bytes(8, "big")
        )
