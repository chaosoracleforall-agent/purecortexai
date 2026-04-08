import pytest
from algopy import Bytes, UInt64
from algopy_testing import algopy_testing_context
from algosdk import encoding

from smart_contracts.governance.contract import GovernanceContract


def _proposal_bytes(
    proposer_address: str,
    *,
    created_round: int,
    proposal_type: int,
    yes_votes: int,
    no_votes: int,
    status: int,
    total_voters: int,
) -> Bytes:
    return Bytes(
        encoding.decode_address(proposer_address)
        + created_round.to_bytes(8, "big")
        + proposal_type.to_bytes(8, "big")
        + yes_votes.to_bytes(8, "big")
        + no_votes.to_bytes(8, "big")
        + status.to_bytes(8, "big")
        + total_voters.to_bytes(8, "big")
    )


def _proposal_params_bytes(
    *,
    discussion_period: int,
    voting_period: int,
    timelock_period: int,
    quorum_bps: int,
    supermajority_bps: int,
) -> Bytes:
    return Bytes(
        discussion_period.to_bytes(8, "big")
        + voting_period.to_bytes(8, "big")
        + timelock_period.to_bytes(8, "big")
        + quorum_bps.to_bytes(8, "big")
        + supermajority_bps.to_bytes(8, "big")
    )


def test_governance_initial_state():
    with algopy_testing_context():
        contract = GovernanceContract()
        assert contract.proposal_count == UInt64(0)
        assert contract.DISCUSSION_PERIOD == UInt64(8640)
        assert contract.VOTING_PERIOD == UInt64(21600)
        assert contract.TIMELOCK_PERIOD == UInt64(30240)
        assert contract.QUORUM_BPS == UInt64(2500)
        assert contract.SUPERMAJORITY_BPS == UInt64(6700)


def test_governance_read_only_queries_from_box_state():
    with algopy_testing_context() as ctx:
        contract = GovernanceContract()
        proposer = str(ctx.any.account())
        proposal_id = UInt64(1)
        proposal_data = _proposal_bytes(
            proposer,
            created_round=123,
            proposal_type=2,
            yes_votes=42,
            no_votes=7,
            status=1,
            total_voters=5,
        )

        contract.proposal_count = proposal_id
        contract.proposals[proposal_id] = proposal_data

        assert contract.get_proposal(proposal_id) == proposal_data
        assert contract.get_proposal_status(proposal_id) == UInt64(1)
        assert contract.get_vote_tally(proposal_id) == Bytes(
            (42).to_bytes(8, "big") + (7).to_bytes(8, "big")
        )
        assert contract.get_proposal_count() == proposal_id


def test_has_voted_uses_composite_vote_box_key():
    with algopy_testing_context() as ctx:
        contract = GovernanceContract()
        voter = ctx.any.account()
        proposal_id = UInt64(3)
        vote_key = Bytes((3).to_bytes(8, "big") + encoding.decode_address(str(voter)))
        contract.votes[vote_key] = Bytes((1).to_bytes(8, "big") + (25).to_bytes(8, "big"))

        assert contract.has_voted(proposal_id, voter) is True
        assert contract.has_voted(UInt64(4), voter) is False


def test_finalize_uses_snapshot_quorum_bps():
    with algopy_testing_context() as ctx:
        contract = GovernanceContract()
        proposal_id = UInt64(7)
        proposer = str(ctx.any.account())
        proposal_data = _proposal_bytes(
            proposer,
            created_round=1,
            proposal_type=0,
            yes_votes=24,
            no_votes=0,
            status=1,  # voting
            total_voters=1,
        )
        # 25 bps of baseline 1_000_000_000_000 = 2_500_000_000, so this should fail.
        params = _proposal_params_bytes(
            discussion_period=0,
            voting_period=0,
            timelock_period=0,
            quorum_bps=25,
            supermajority_bps=6700,
        )
        contract.proposals[proposal_id] = proposal_data
        contract.proposal_params[proposal_id] = params

        ctx.ledger.patch_global_fields(round=2)
        with pytest.raises(AssertionError):
            contract.finalize_proposal(proposal_id)


def test_finalize_supermajority_large_vote_path():
    with algopy_testing_context() as ctx:
        contract = GovernanceContract()
        proposal_id = UInt64(8)
        proposer = str(ctx.any.account())
        large_yes = 1_900_000_000_000_000
        proposal_data = _proposal_bytes(
            proposer,
            created_round=1,
            proposal_type=0,
            yes_votes=large_yes,
            no_votes=0,
            status=1,  # voting
            total_voters=1,
        )
        # Keep quorum permissive so we specifically exercise supermajority branch.
        params = _proposal_params_bytes(
            discussion_period=0,
            voting_period=0,
            timelock_period=0,
            quorum_bps=1,
            supermajority_bps=6700,
        )
        contract.proposals[proposal_id] = proposal_data
        contract.proposal_params[proposal_id] = params

        ctx.ledger.patch_global_fields(round=2)
        contract.finalize_proposal(proposal_id)
        assert contract.get_proposal_status(proposal_id) == UInt64(2)
