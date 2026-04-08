import pytest
from algopy import Application, Bytes, UInt64
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


def test_process_revenue_rejects_payment_sender_mismatch():
    with algopy_testing_context() as ctx:
        contract = SovereignTreasury()
        app_ref = Application.from_int(contract.__app_id__)
        app_sender = ctx.default_sender
        payment_sender = ctx.any.account()
        payment_receiver = ctx.any.account()
        payment = ctx.any.txn.payment(
            sender=payment_sender,
            receiver=payment_receiver,
            amount=1_000,
        )
        app_call = ctx.any.txn.application_call(sender=app_sender, app_id=app_ref)

        with ctx.txn.create_group([payment, app_call], active_txn_index=1):
            with pytest.raises(AssertionError, match="Payment sender must match caller"):
                contract.process_revenue(payment)


def test_process_revenue_rejects_non_adjacent_payment_reference():
    with algopy_testing_context() as ctx:
        contract = SovereignTreasury()
        app_ref = Application.from_int(contract.__app_id__)
        sender = ctx.default_sender
        payment = ctx.any.txn.payment(
            sender=sender,
            receiver=ctx.any.account(),
            amount=1_000,
        )
        filler = ctx.any.txn.application_call(sender=sender, app_id=app_ref)
        target = ctx.any.txn.application_call(sender=sender, app_id=app_ref)

        with ctx.txn.create_group([payment, filler, target], active_txn_index=2):
            with pytest.raises(AssertionError, match="Payment must immediately precede app call"):
                contract.process_revenue(payment)


def test_execute_burn_rejects_transfer_sender_mismatch():
    with algopy_testing_context() as ctx:
        contract = SovereignTreasury()
        app_ref = Application.from_int(contract.__app_id__)
        app_sender = ctx.default_sender
        transfer_sender = ctx.any.account()
        transfer = ctx.any.txn.asset_transfer(
            sender=transfer_sender,
            xfer_asset=ctx.any.asset(),
            asset_receiver=ctx.any.account(),
            asset_amount=1,
        )
        app_call = ctx.any.txn.application_call(sender=app_sender, app_id=app_ref)

        with ctx.txn.create_group([transfer, app_call], active_txn_index=1):
            with pytest.raises(AssertionError, match="Transfer sender must match caller"):
                contract.execute_burn(transfer)


def test_execute_burn_rejects_non_adjacent_transfer_reference():
    with algopy_testing_context() as ctx:
        contract = SovereignTreasury()
        app_ref = Application.from_int(contract.__app_id__)
        sender = ctx.default_sender
        transfer = ctx.any.txn.asset_transfer(
            sender=sender,
            xfer_asset=ctx.any.asset(),
            asset_receiver=ctx.any.account(),
            asset_amount=1,
        )
        filler = ctx.any.txn.application_call(sender=sender, app_id=app_ref)
        target = ctx.any.txn.application_call(sender=sender, app_id=app_ref)

        with ctx.txn.create_group([transfer, filler, target], active_txn_index=2):
            with pytest.raises(AssertionError, match="Transfer must immediately precede app call"):
                contract.execute_burn(transfer)
