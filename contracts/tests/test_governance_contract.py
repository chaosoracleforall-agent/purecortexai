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
