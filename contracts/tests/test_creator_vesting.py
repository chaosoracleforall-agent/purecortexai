import pytest
from algopy import Bytes, UInt64
from algopy_testing import algopy_testing_context

from smart_contracts.creator_vesting.contract import CreatorVesting


TOTAL_ALLOCATION = 1_000_000_000_000_000  # 10% of 10Q = 1Q CORTEX
TGE_RELEASE_BPS = 1_000  # 10%
VESTING_DAYS = 180
SECONDS_PER_DAY = 86_400


def _setup_vesting(ctx, *, tge_timestamp: int = 1_000_000):
    contract = CreatorVesting()
    mock_asset = ctx.any.asset()
    beneficiary = ctx.any.account()

    contract.cortex_token = mock_asset.id
    contract.beneficiary = beneficiary.bytes
    contract.tge_timestamp = UInt64(tge_timestamp)
    contract.total_allocation = UInt64(TOTAL_ALLOCATION)
    contract.tge_release_bps = UInt64(TGE_RELEASE_BPS)
    contract.vesting_days = UInt64(VESTING_DAYS)
    contract.total_claimed = UInt64(0)
    contract.initialized = UInt64(1)

    return contract, mock_asset, beneficiary


class TestCreatorVestingInitialState:
    def test_defaults(self):
        with algopy_testing_context():
            contract = CreatorVesting()
            assert contract.cortex_token == UInt64(0)
            assert contract.tge_release_bps == UInt64(1000)
            assert contract.vesting_days == UInt64(180)
            assert contract.total_claimed == UInt64(0)
            assert contract.initialized == UInt64(0)


class TestVestedAmountCalculation:
    def test_before_tge_returns_zero(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=2_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000)
            assert contract.get_vested_amount() == UInt64(0)

    def test_at_tge_returns_10_percent(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=1_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000)
            tge_amount = (TOTAL_ALLOCATION * TGE_RELEASE_BPS) // 10_000
            assert contract.get_vested_amount() == UInt64(tge_amount)

    def test_one_day_after_tge(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=1_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000 + SECONDS_PER_DAY)

            tge_amount = (TOTAL_ALLOCATION * TGE_RELEASE_BPS) // 10_000
            remaining = TOTAL_ALLOCATION - tge_amount
            daily = remaining // VESTING_DAYS
            expected = tge_amount + daily

            assert contract.get_vested_amount() == UInt64(expected)

    def test_halfway_through_vesting(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=1_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000 + (90 * SECONDS_PER_DAY))

            tge_amount = (TOTAL_ALLOCATION * TGE_RELEASE_BPS) // 10_000
            remaining = TOTAL_ALLOCATION - tge_amount
            daily = remaining // VESTING_DAYS
            expected = tge_amount + (daily * 90)

            assert contract.get_vested_amount() == UInt64(expected)

    def test_full_vesting_at_180_days(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=1_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000 + (180 * SECONDS_PER_DAY))
            assert contract.get_vested_amount() == UInt64(TOTAL_ALLOCATION)

    def test_past_vesting_period_caps_at_total(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=1_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000 + (365 * SECONDS_PER_DAY))
            assert contract.get_vested_amount() == UInt64(TOTAL_ALLOCATION)


class TestClaimable:
    def test_claimable_equals_vested_when_nothing_claimed(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=1_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000 + (30 * SECONDS_PER_DAY))
            vested = contract.get_vested_amount()
            claimable = contract.get_claimable()
            assert claimable == vested

    def test_claimable_reduces_after_partial_claim(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=1_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000 + (60 * SECONDS_PER_DAY))
            vested = int(contract.get_vested_amount())

            partial_claim = vested // 2
            contract.total_claimed = UInt64(partial_claim)

            claimable = contract.get_claimable()
            assert claimable == UInt64(vested - partial_claim)

    def test_claimable_zero_when_fully_claimed(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=1_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000 + (180 * SECONDS_PER_DAY))
            contract.total_claimed = UInt64(TOTAL_ALLOCATION)
            assert contract.get_claimable() == UInt64(0)

    def test_claimable_zero_before_tge(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=2_000_000)
            ctx.ledger.patch_global_fields(latest_timestamp=1_000_000)
            assert contract.get_claimable() == UInt64(0)


class TestVestingInfo:
    def test_returns_packed_state(self):
        with algopy_testing_context() as ctx:
            contract, _, _ = _setup_vesting(ctx, tge_timestamp=1_000_000)
            contract.total_claimed = UInt64(500_000_000)

            info = contract.get_vesting_info()
            assert info == Bytes(
                TOTAL_ALLOCATION.to_bytes(8, "big")
                + (500_000_000).to_bytes(8, "big")
                + (1_000_000).to_bytes(8, "big")
                + VESTING_DAYS.to_bytes(8, "big")
                + TGE_RELEASE_BPS.to_bytes(8, "big")
            )
