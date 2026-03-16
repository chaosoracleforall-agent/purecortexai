from __future__ import annotations
from datetime import datetime, timedelta, timezone

from algosdk import account
from algosdk.util import sign_bytes

from src.services.governance_voting import (
    build_signed_vote_message,
    calculate_live_tally,
    calculate_voter_power,
    verify_signed_vote,
)


def test_verify_signed_vote_accepts_valid_signature():
    private_key, voter = account.generate_account()
    issued_at = datetime.now(timezone.utc).isoformat()
    nonce = "pytest-nonce"
    message = build_signed_vote_message(
        proposal_id=7,
        voter=voter,
        vote="for",
        issued_at=issued_at,
        nonce=nonce,
    )
    signature = sign_bytes(message.encode("utf-8"), private_key)

    verify_signed_vote(
        proposal_id=7,
        voter=voter,
        vote="for",
        issued_at=issued_at,
        nonce=nonce,
        signature_b64=signature,
    )


def test_verify_signed_vote_rejects_expired_signature():
    private_key, voter = account.generate_account()
    issued_at = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
    message = build_signed_vote_message(
        proposal_id=9,
        voter=voter,
        vote="against",
        issued_at=issued_at,
        nonce="expired",
    )
    signature = sign_bytes(message.encode("utf-8"), private_key)

    try:
        verify_signed_vote(
            proposal_id=9,
            voter=voter,
            vote="against",
            issued_at=issued_at,
            nonce="expired",
            signature_b64=signature,
        )
    except ValueError as exc:
        assert "expired" in str(exc).lower()
    else:  # pragma: no cover - safety net
        raise AssertionError("Expected expired vote signature to be rejected")


def test_verify_signed_vote_rejects_future_timestamp():
    private_key, voter = account.generate_account()
    issued_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    message = build_signed_vote_message(
        proposal_id=11,
        voter=voter,
        vote="for",
        issued_at=issued_at,
        nonce="future",
    )
    signature = sign_bytes(message.encode("utf-8"), private_key)

    try:
        verify_signed_vote(
            proposal_id=11,
            voter=voter,
            vote="for",
            issued_at=issued_at,
            nonce="future",
            signature_b64=signature,
        )
    except ValueError as exc:
        assert "future" in str(exc).lower()
    else:  # pragma: no cover - safety net
        raise AssertionError("Expected future-dated vote signature to be rejected")


def test_calculate_live_tally_moves_power_from_delegate_to_direct_vote():
    proposal = {
        "id": 1,
        "votes_for": 0,
        "votes_against": 0,
        "voters": [],
        "vote_records": {
            "DELEGATE": {"vote": "for", "source": "signed_wallet", "recorded_at": "2026-03-16T00:00:00+00:00"},
            "ALICE": {"vote": "against", "source": "signed_wallet", "recorded_at": "2026-03-16T00:05:00+00:00"},
        },
    }
    snapshots = [
        {"address": "ALICE", "ve_power": 100_000_000, "delegate": "DELEGATE"},
        {"address": "BOB", "ve_power": 50_000_000, "delegate": "DELEGATE"},
        {"address": "DELEGATE", "ve_power": 25_000_000, "delegate": None},
    ]

    tally = calculate_live_tally(proposal, stake_snapshots=snapshots)

    assert tally["votes_for"] == 75_000_000
    assert tally["votes_against"] == 100_000_000
    assert tally["voter_count"] == 3


def test_calculate_voter_power_excludes_delegators_who_already_voted_directly():
    proposal = {
        "id": 2,
        "votes_for": 0,
        "votes_against": 0,
        "voters": [],
        "vote_records": {
            "DELEGATE": {"vote": "for", "source": "signed_wallet", "recorded_at": "2026-03-16T00:00:00+00:00"},
            "ALICE": {"vote": "against", "source": "signed_wallet", "recorded_at": "2026-03-16T00:05:00+00:00"},
        },
    }
    snapshots = [
        {"address": "ALICE", "ve_power": 100_000_000, "delegate": "DELEGATE"},
        {"address": "BOB", "ve_power": 50_000_000, "delegate": "DELEGATE"},
        {"address": "DELEGATE", "ve_power": 25_000_000, "delegate": None},
    ]

    summary = calculate_voter_power("DELEGATE", proposal=proposal, stake_snapshots=snapshots)

    assert summary["direct_weight"] == 25_000_000
    assert summary["delegated_weight"] == 50_000_000
    assert summary["effective_weight"] == 75_000_000
