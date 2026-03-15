from algopy import Bytes, UInt64
from algopy_testing import algopy_testing_context
from algosdk import encoding

from smart_contracts.staking.contract import VeCortexStaking


def _stake_bytes(amount: int, unlock_round: int, ve_power: int, boost: int) -> Bytes:
    return Bytes(
        amount.to_bytes(8, "big")
        + unlock_round.to_bytes(8, "big")
        + ve_power.to_bytes(8, "big")
        + boost.to_bytes(8, "big")
    )


def test_staking_initial_state():
    with algopy_testing_context():
        contract = VeCortexStaking()
        assert contract.cortex_token == UInt64(0)
        assert contract.total_staked == UInt64(0)
        assert contract.reward_pool == UInt64(0)
        assert contract.MIN_LOCK_DAYS == UInt64(7)
        assert contract.MAX_LOCK_DAYS == UInt64(1460)
        assert contract.MAX_BOOST == UInt64(2500)


def test_staking_read_only_methods_use_box_state():
    with algopy_testing_context() as ctx:
        contract = VeCortexStaking()
        staker = ctx.any.account()
        delegate = ctx.any.account()

        contract.total_staked = UInt64(900_000_000)
        contract.stakes[staker.bytes] = _stake_bytes(
            amount=500_000_000,
            unlock_round=123456,
            ve_power=750_000_000,
            boost=1500,
        )
        contract.delegations[staker.bytes] = Bytes(encoding.decode_address(str(delegate)))

        assert contract.get_ve_power(staker) == UInt64(750_000_000)
        assert contract.get_stake_info(staker) == _stake_bytes(
            amount=500_000_000,
            unlock_round=123456,
            ve_power=750_000_000,
            boost=1500,
        )
        assert contract.get_delegate(staker) == Bytes(encoding.decode_address(str(delegate)))
        assert contract.get_total_staked() == UInt64(900_000_000)


def test_staking_read_only_methods_return_empty_defaults():
    with algopy_testing_context() as ctx:
        contract = VeCortexStaking()
        staker = ctx.any.account()

        assert contract.get_ve_power(staker) == UInt64(0)
        assert contract.get_stake_info(staker) == Bytes(b"")
        assert contract.get_delegate(staker) == Bytes(b"")
