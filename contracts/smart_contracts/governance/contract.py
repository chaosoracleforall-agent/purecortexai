from algopy import (
    ARC4Contract,
    String,
    UInt64,
    Account,
    Txn,
    Global,
    BoxMap,
    Bytes,
    op,
    gtxn,
    itxn,
)
from algopy.arc4 import abimethod


class GovernanceContract(ARC4Contract):
    """
    On-chain governance for PURECORTEX.

    Proposal lifecycle:
      propose -> discuss (48h) -> vote (5 days) -> timelock (7 days) -> execute

    Proposals are created by authorized addresses (initially creator only,
    later Senator agents). Votes are weighted by veCORTEX power from the
    staking contract.

    Proposal status codes:
      0 = discussion
      1 = voting
      2 = passed
      3 = rejected
      4 = executed
      5 = cancelled

    Proposal data encoding (80 bytes):
      proposer(32) + created_round(8) + type(8) + yes_votes(8) +
      no_votes(8) + status(8) + total_voters(8)
    """

    def __init__(self) -> None:
        self.staking_app = UInt64(0)  # Reference to VeCortexStaking app ID
        self.cortex_asset_id = UInt64(0)  # CORTEX ASA ID for vote-weight transfers
        self.proposal_count = UInt64(0)

        # Proposals: proposal_id -> ProposalData (80 bytes)
        self.proposals = BoxMap(UInt64, Bytes, key_prefix=b"p")

        # Votes: composite key (proposal_id_bytes + voter_bytes) -> vote_data
        # vote_data: vote(8) + ve_power(8) = 16 bytes
        self.votes = BoxMap(Bytes, Bytes, key_prefix=b"v")
        # Snapshot governance parameters at proposal creation time so active
        # proposals are not affected by later admin parameter updates.
        self.proposal_params = BoxMap(UInt64, Bytes, key_prefix=b"g")

        # Governance timing parameters (in rounds, ~3 rounds/minute)
        self.DISCUSSION_PERIOD = UInt64(8640)  # 48 hours (48 * 60 * 3)
        self.VOTING_PERIOD = UInt64(21600)  # 5 days (5 * 24 * 60 * 3)
        self.TIMELOCK_PERIOD = UInt64(30240)  # 7 days (7 * 24 * 60 * 3)

        # Quorum and majority thresholds (basis points)
        self.QUORUM_BPS = UInt64(2500)  # 25% of total veCORTEX must participate
        self.SUPERMAJORITY_BPS = UInt64(6700)  # 67% yes votes required to pass

    # ------------------------------------------------------------------ #
    #  Initialization
    # ------------------------------------------------------------------ #

    @abimethod()
    def initialize(self, staking_app: UInt64, cortex_asset_id: UInt64) -> None:
        """
        Set reference to the staking contract app ID and CORTEX ASA ID.
        Only callable by the application creator.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert self.staking_app == UInt64(0), "Already initialized"
        self.staking_app = staking_app
        self.cortex_asset_id = cortex_asset_id

    # ------------------------------------------------------------------ #
    #  Proposal creation
    # ------------------------------------------------------------------ #

    @abimethod()
    def create_proposal(
        self,
        title: String,
        description: String,
        proposal_type: UInt64,
    ) -> UInt64:
        """
        Create a new governance proposal.

        proposal_type values:
          0 = parameter change
          1 = treasury allocation
          2 = protocol upgrade
          3 = emergency action

        Currently restricted to the application creator.
        In production, Senator agents will be authorized to propose.
        Returns the new proposal ID.
        """
        assert Txn.sender == Global.creator_address, "Only Senator can propose"
        assert proposal_type <= UInt64(3), "Invalid proposal type"

        proposal_id = self.proposal_count + UInt64(1)
        self.proposal_count = proposal_id

        # Encode proposal data (80 bytes):
        # proposer(32) + created_round(8) + type(8) + yes_votes(8) +
        # no_votes(8) + status(8) + total_voters(8)
        proposal_data = (
            Txn.sender.bytes
            + op.itob(Global.round)
            + op.itob(proposal_type)
            + op.itob(UInt64(0))  # yes_votes
            + op.itob(UInt64(0))  # no_votes
            + op.itob(UInt64(0))  # status: discussion
            + op.itob(UInt64(0))  # total_voters
        )
        self.proposals[proposal_id] = proposal_data
        self.proposal_params[proposal_id] = (
            op.itob(self.DISCUSSION_PERIOD)
            + op.itob(self.VOTING_PERIOD)
            + op.itob(self.TIMELOCK_PERIOD)
            + op.itob(self.QUORUM_BPS)
            + op.itob(self.SUPERMAJORITY_BPS)
        )

        return proposal_id

    # ------------------------------------------------------------------ #
    #  Proposal phase transitions
    # ------------------------------------------------------------------ #

    @abimethod()
    def advance_to_voting(self, proposal_id: UInt64) -> None:
        """
        Advance a proposal from the discussion phase to the voting phase.
        Can only be called after the discussion period (48h) has elapsed.

        NOTE: This is intentionally permissionless — any account can advance
        a proposal once the discussion period elapses. The proposer cannot
        cancel during this phase by design, ensuring governance transparency.
        """
        assert op.Box.get(Bytes(b"p") + op.itob(proposal_id))[1], "Proposal not found"
        proposal_data = self.proposals[proposal_id]

        created_round = op.btoi(op.extract(proposal_data, 32, 8))
        current_status = op.btoi(op.extract(proposal_data, 64, 8))
        assert op.Box.get(Bytes(b"g") + op.itob(proposal_id))[1], "Proposal params missing"
        params = self.proposal_params[proposal_id]
        discussion_period = op.btoi(op.extract(params, 0, 8))

        assert current_status == UInt64(0), "Not in discussion phase"
        assert (
            Global.round >= created_round + discussion_period
        ), "Discussion period not over"

        # Update status to voting (1), preserve all other fields
        new_data = (
            op.extract(proposal_data, 0, 64)
            + op.itob(UInt64(1))
            + op.extract(proposal_data, 72, 8)
        )
        self.proposals[proposal_id] = new_data

    @abimethod()
    def finalize_proposal(self, proposal_id: UInt64) -> None:
        """
        Finalize a proposal after the voting period has ended.
        Checks if quorum was met and if supermajority threshold was reached.
        Sets status to passed (2) or rejected (3).
        """
        assert op.Box.get(Bytes(b"p") + op.itob(proposal_id))[1], "Proposal not found"
        proposal_data = self.proposals[proposal_id]

        created_round = op.btoi(op.extract(proposal_data, 32, 8))
        yes_votes = op.btoi(op.extract(proposal_data, 48, 8))
        no_votes = op.btoi(op.extract(proposal_data, 56, 8))
        current_status = op.btoi(op.extract(proposal_data, 64, 8))
        assert op.Box.get(Bytes(b"g") + op.itob(proposal_id))[1], "Proposal params missing"
        params = self.proposal_params[proposal_id]
        discussion_period = op.btoi(op.extract(params, 0, 8))
        voting_period = op.btoi(op.extract(params, 8, 8))
        quorum_bps = op.btoi(op.extract(params, 24, 8))
        supermajority_bps = op.btoi(op.extract(params, 32, 8))

        assert current_status == UInt64(1), "Not in voting phase"

        voting_start = created_round + discussion_period
        assert (
            Global.round >= voting_start + voting_period
        ), "Voting period not over"

        total_votes = yes_votes + no_votes

        # Quorum check uses proposal snapshot parameters.
        # Phase 1 keeps the same baseline total vote power target, but derives
        # the required quorum from the captured QUORUM_BPS value.
        quorum_target = (UInt64(1_000_000_000_000) * quorum_bps) // UInt64(10_000)
        if quorum_target == UInt64(0):
            quorum_target = UInt64(1)
        assert total_votes >= quorum_target, "Quorum not met"

        # Determine outcome — supermajority check with overflow protection.
        # Direct multiplication overflows UInt64 when total_votes > ~1.8e15,
        # so we fall back to division-first arithmetic for large totals.
        new_status = UInt64(3)  # default: rejected
        if total_votes <= UInt64(1_844_000_000_000_000):
            passed = yes_votes * UInt64(10000) >= total_votes * supermajority_bps
        else:
            threshold = (total_votes // UInt64(10000)) * supermajority_bps
            passed = yes_votes >= threshold
        if passed:
            new_status = UInt64(2)  # passed

        new_data = (
            op.extract(proposal_data, 0, 64)
            + op.itob(new_status)
            + op.extract(proposal_data, 72, 8)
        )
        self.proposals[proposal_id] = new_data

    @abimethod()
    def execute_proposal(self, proposal_id: UInt64) -> None:
        """
        Mark a passed proposal as executed after the timelock period.
        The actual execution of the proposal action is handled off-chain
        or via a separate transaction group.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert op.Box.get(Bytes(b"p") + op.itob(proposal_id))[1], "Proposal not found"
        proposal_data = self.proposals[proposal_id]

        created_round = op.btoi(op.extract(proposal_data, 32, 8))
        current_status = op.btoi(op.extract(proposal_data, 64, 8))
        assert op.Box.get(Bytes(b"g") + op.itob(proposal_id))[1], "Proposal params missing"
        params = self.proposal_params[proposal_id]
        discussion_period = op.btoi(op.extract(params, 0, 8))
        voting_period = op.btoi(op.extract(params, 8, 8))
        timelock_period = op.btoi(op.extract(params, 16, 8))

        assert current_status == UInt64(2), "Proposal not passed"

        # Check timelock: discussion + voting + timelock
        execution_round = (
            created_round
            + discussion_period
            + voting_period
            + timelock_period
        )
        assert Global.round >= execution_round, "Timelock period not over"

        # Mark as executed (4)
        new_data = (
            op.extract(proposal_data, 0, 64)
            + op.itob(UInt64(4))
            + op.extract(proposal_data, 72, 8)
        )
        self.proposals[proposal_id] = new_data

    @abimethod()
    def cancel_proposal(self, proposal_id: UInt64) -> None:
        """
        Cancel a proposal. Only callable by the creator (emergency).
        Can only cancel proposals in discussion or voting phase.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert op.Box.get(Bytes(b"p") + op.itob(proposal_id))[1], "Proposal not found"
        proposal_data = self.proposals[proposal_id]

        current_status = op.btoi(op.extract(proposal_data, 64, 8))
        assert current_status <= UInt64(1), "Can only cancel active proposals"

        # Mark as cancelled (5)
        new_data = (
            op.extract(proposal_data, 0, 64)
            + op.itob(UInt64(5))
            + op.extract(proposal_data, 72, 8)
        )
        self.proposals[proposal_id] = new_data

    # ------------------------------------------------------------------ #
    #  Voting
    # ------------------------------------------------------------------ #

    @abimethod()
    def cast_vote(
        self,
        proposal_id: UInt64,
        vote: UInt64,
        cortex_txn: gtxn.AssetTransferTransaction,
    ) -> None:
        """
        Cast a CORTEX-weighted vote on a proposal.

        vote: 1 = yes, 0 = no

        Each address can only vote once per proposal.

        Phase 1 (current): Voter must include a CORTEX asset transfer to this
        contract in the same group transaction. The transferred amount is used
        as voting weight and remains escrowed in this contract until the
        proposal reaches a terminal state.
        Phase 2: Will implement cross-app veCORTEX reads from the staking
        contract for time-weighted voting power.
        """
        assert op.Box.get(Bytes(b"p") + op.itob(proposal_id))[1], "Proposal not found"
        proposal_data = self.proposals[proposal_id]

        current_status = op.btoi(op.extract(proposal_data, 64, 8))
        assert current_status == UInt64(1), "Not in voting phase"
        assert vote <= UInt64(1), "Vote must be 0 (no) or 1 (yes)"
        assert op.Box.get(Bytes(b"g") + op.itob(proposal_id))[1], "Proposal params missing"
        params = self.proposal_params[proposal_id]
        discussion_period = op.btoi(op.extract(params, 0, 8))
        voting_period = op.btoi(op.extract(params, 8, 8))

        # Check voting period hasn't expired
        created_round = op.btoi(op.extract(proposal_data, 32, 8))
        voting_start = created_round + discussion_period
        assert (
            Global.round <= voting_start + voting_period
        ), "Voting period expired"

        # Ensure voter hasn't already voted
        vote_key = op.itob(proposal_id) + Txn.sender.bytes
        assert not op.Box.get(Bytes(b"v") + vote_key)[1], "Already voted"

        # Phase 1: Derive voting weight from CORTEX asset transfer in group.
        # Voter sends CORTEX to this contract; amount = voting weight.
        # CORTEX is returned immediately below.
        assert self.cortex_asset_id != UInt64(0), "Contract not initialized"
        assert cortex_txn.xfer_asset.id == self.cortex_asset_id, "Wrong asset"
        assert cortex_txn.sender == Txn.sender, "CORTEX sender must match caller"
        assert (
            cortex_txn.asset_receiver == Global.current_application_address
        ), "CORTEX must be sent to governance contract"
        assert cortex_txn.asset_amount > UInt64(0), "Must transfer CORTEX to vote"
        ve_power = cortex_txn.asset_amount

        # Record the vote
        self.votes[vote_key] = op.itob(vote) + op.itob(ve_power)

        # Update tallies
        yes_votes = op.btoi(op.extract(proposal_data, 48, 8))
        no_votes = op.btoi(op.extract(proposal_data, 56, 8))
        total_voters = op.btoi(op.extract(proposal_data, 72, 8))

        if vote == UInt64(1):
            yes_votes = yes_votes + ve_power
        else:
            no_votes = no_votes + ve_power

        total_voters = total_voters + UInt64(1)

        new_data = (
            op.extract(proposal_data, 0, 48)
            + op.itob(yes_votes)
            + op.itob(no_votes)
            + op.extract(proposal_data, 64, 8)
            + op.itob(total_voters)
        )
        self.proposals[proposal_id] = new_data

    @abimethod()
    def reclaim_vote(self, proposal_id: UInt64) -> None:
        """
        Reclaim escrowed CORTEX voting weight once a proposal is terminal.

        Terminal statuses:
          2 = passed
          3 = rejected
          4 = executed
          5 = cancelled
        """
        assert self.cortex_asset_id != UInt64(0), "Contract not initialized"
        assert op.Box.get(Bytes(b"p") + op.itob(proposal_id))[1], "Proposal not found"

        proposal_data = self.proposals[proposal_id]
        status = op.btoi(op.extract(proposal_data, 64, 8))
        assert status >= UInt64(2), "Proposal is still active"

        vote_key = op.itob(proposal_id) + Txn.sender.bytes
        vote_box_key = Bytes(b"v") + vote_key
        vote_data, exists = op.Box.get(vote_box_key)
        assert exists, "No vote to reclaim"

        ve_power = op.btoi(op.extract(vote_data, 8, 8))
        assert ve_power > UInt64(0), "Nothing to reclaim"

        # Delete vote record before interaction to prevent re-claims.
        deleted = op.Box.delete(vote_box_key)
        assert deleted, "Failed to clear vote record"

        itxn.AssetTransfer(
            xfer_asset=self.cortex_asset_id,
            asset_receiver=Txn.sender,
            asset_amount=ve_power,
            fee=UInt64(0),
        ).submit()

    # ------------------------------------------------------------------ #
    #  Read-only queries
    # ------------------------------------------------------------------ #

    @abimethod(readonly=True)
    def get_proposal(self, proposal_id: UInt64) -> Bytes:
        """
        Get full proposal data (80 bytes).
        Returns empty bytes if proposal doesn't exist.
        """
        if not op.Box.get(Bytes(b"p") + op.itob(proposal_id))[1]:
            return Bytes(b"")
        return self.proposals[proposal_id]

    @abimethod(readonly=True)
    def get_proposal_status(self, proposal_id: UInt64) -> UInt64:
        """
        Get the status code of a proposal.
        Returns 99 if proposal doesn't exist.
        """
        if not op.Box.get(Bytes(b"p") + op.itob(proposal_id))[1]:
            return UInt64(99)
        proposal_data = self.proposals[proposal_id]
        return op.btoi(op.extract(proposal_data, 64, 8))

    @abimethod(readonly=True)
    def get_vote_tally(self, proposal_id: UInt64) -> Bytes:
        """
        Get yes and no vote counts for a proposal.
        Returns 16 bytes: yes_votes(8) + no_votes(8).
        Returns empty bytes if proposal doesn't exist.
        """
        if not op.Box.get(Bytes(b"p") + op.itob(proposal_id))[1]:
            return Bytes(b"")
        proposal_data = self.proposals[proposal_id]
        return op.extract(proposal_data, 48, 16)

    @abimethod(readonly=True)
    def get_proposal_count(self) -> UInt64:
        """Get the total number of proposals created."""
        return self.proposal_count

    @abimethod(readonly=True)
    def has_voted(self, proposal_id: UInt64, voter: Account) -> bool:
        """Check if an account has voted on a proposal."""
        vote_key = op.itob(proposal_id) + voter.bytes
        return op.Box.get(Bytes(b"v") + vote_key)[1]

    # ------------------------------------------------------------------ #
    #  Admin
    # ------------------------------------------------------------------ #

    @abimethod()
    def update_governance_parameters(
        self,
        discussion_period: UInt64,
        voting_period: UInt64,
        timelock_period: UInt64,
        quorum_bps: UInt64,
        supermajority_bps: UInt64,
    ) -> None:
        """
        Update governance timing and threshold parameters.
        Only callable by the creator. In production, this would
        require a governance proposal itself.
        """
        assert Txn.sender == Global.creator_address, "Unauthorized"
        assert discussion_period > UInt64(0), "Discussion period must be positive"
        assert voting_period > UInt64(0), "Voting period must be positive"
        assert timelock_period > UInt64(0), "Timelock must be positive"
        assert quorum_bps <= UInt64(10000), "Quorum cannot exceed 100%"
        assert supermajority_bps >= UInt64(5000), "Majority must be at least 50%"
        assert supermajority_bps <= UInt64(10000), "Majority cannot exceed 100%"

        self.DISCUSSION_PERIOD = discussion_period
        self.VOTING_PERIOD = voting_period
        self.TIMELOCK_PERIOD = timelock_period
        self.QUORUM_BPS = quorum_bps
        self.SUPERMAJORITY_BPS = supermajority_bps
