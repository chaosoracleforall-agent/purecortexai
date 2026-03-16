"""
Governance API for PURECORTEX.

Serves the PURECORTEX Constitution (Preamble + Articles) and provides
the canonical backend-governed proposal, review, and voting flow for testnet.
Proposal storage lives in Redis while vote weight is derived from the live
staking/delegation contract state.
"""

import base64
import json
import logging
import os
import struct
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.services.cache import get_cache_service, cache_with_ttl, TTL_GOVERNANCE
from src.services.algorand import GOVERNANCE_APP_ID, get_algorand_service
from src.services.governance_voting import (
    calculate_live_tally,
    calculate_voter_power,
    normalize_proposal,
    verify_signed_vote,
)

logger = logging.getLogger("purecortex.governance")

router = APIRouter(prefix="/api/governance", tags=["governance"])

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
# Constitution files: in Docker mounted at /app/docs, locally at ../docs relative to backend/
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DOCKER_DOCS = os.path.join(_BACKEND_DIR, "docs", "tokenomics", "constitution")
_LOCAL_DOCS = os.path.join(os.path.dirname(_BACKEND_DIR), "docs", "tokenomics", "constitution")
_CONSTITUTION_DIR = _DOCKER_DOCS if os.path.isdir(_DOCKER_DOCS) else _LOCAL_DOCS

PREAMBLE_PATH = os.path.join(_CONSTITUTION_DIR, "PREAMBLE.md")
ARTICLES_PATH = os.path.join(_CONSTITUTION_DIR, "ARTICLES.md")

# Redis key constants
PROPOSAL_PREFIX = "governance:proposal"
PROPOSAL_COUNTER_KEY = "governance:proposal_counter"
PROPOSAL_INDEX_KEY = "governance:proposal_ids"

# Proposal TTL — 90 days (seconds)
PROPOSAL_TTL = 90 * 24 * 3600


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────
class ConstitutionResponse(BaseModel):
    preamble: str
    articles: str
    preamble_status: str = "IMMUTABLE"
    articles_status: str = "AMENDABLE"


class ProposalStatus(str, Enum):
    ACTIVE = "active"
    REVIEW = "review"
    VOTING = "voting"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class ProposalType(str, Enum):
    AMENDMENT = "amendment"
    PARAMETER = "parameter"
    TREASURY = "treasury"
    EMERGENCY = "emergency"
    GENERAL = "general"


class CuratorReview(BaseModel):
    compliant: bool
    analysis: str
    recommendation: str
    curator_name: str
    reviewed_at: str


class ProposalCreateRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    type: ProposalType = ProposalType.GENERAL
    proposer: str = Field(..., min_length=1, max_length=100)


class ProposalSummary(BaseModel):
    id: int
    title: str
    type: str
    status: ProposalStatus
    proposer: str
    created_at: str
    votes_for: int = 0
    votes_against: int = 0
    voter_count: int = 0
    curator_reviewed: bool = False


class ProposalDetail(BaseModel):
    id: int
    title: str
    description: str
    type: str
    status: ProposalStatus
    proposer: str
    created_at: str
    votes_for: int = 0
    votes_against: int = 0
    voters: list[str] = []
    curator_review: Optional[CuratorReview] = None


class ReviewRequest(BaseModel):
    compliant: bool
    analysis: str = Field(..., min_length=5, max_length=5000)
    recommendation: str = Field(..., min_length=3, max_length=200)
    curator_name: str = Field(..., min_length=1, max_length=100)


class VoteRequest(BaseModel):
    voter: str = Field(..., min_length=1, max_length=100)
    vote: str = Field(..., pattern="^(for|against)$")
    weight: int = Field(default=1, ge=1, le=1000)


class SignedVoteRequest(BaseModel):
    voter: str = Field(..., min_length=32, max_length=64)
    vote: str = Field(..., pattern="^(for|against)$")
    issued_at: str = Field(..., min_length=10, max_length=64)
    nonce: str = Field(..., min_length=8, max_length=128)
    signature: str = Field(..., min_length=16, max_length=2048)


class VoteResponse(BaseModel):
    proposal_id: int
    voter: str
    vote: str
    weight: int
    votes_for: int
    votes_against: int
    direct_weight: int = 0
    delegated_weight: int = 0
    auth_method: str = "api_key"


class VotePowerResponse(BaseModel):
    proposal_id: int
    voter: str
    direct_weight: int
    delegated_weight: int
    effective_weight: int


class GovernanceOverview(BaseModel):
    total_proposals: int
    active_proposals: int
    voting_proposals: int
    passed_proposals: int
    rejected_proposals: int
    total_votes: int


class ProposalsListResponse(BaseModel):
    total: int
    proposals: list[ProposalSummary]


# ──────────────────────────────────────────────
# Redis helpers
# ──────────────────────────────────────────────
def _read_file(path: str) -> str:
    """Read a text file, returning empty string if not found."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


async def _redis_get(key: str) -> Optional[str]:
    """Get a raw string value from Redis via the CacheService's internal client."""
    cache = get_cache_service()
    if not cache._redis:
        return None
    try:
        return await cache._redis.get(key)
    except Exception as exc:
        logger.warning("Redis GET failed for %s: %s", key, exc)
        return None


async def _redis_set(key: str, value: str, ttl: int = PROPOSAL_TTL) -> None:
    """Set a raw string value in Redis."""
    cache = get_cache_service()
    if not cache._redis:
        return
    try:
        await cache._redis.setex(key, ttl, value)
    except Exception as exc:
        logger.warning("Redis SET failed for %s: %s", key, exc)


async def _redis_set_no_ttl(key: str, value: str) -> None:
    """Set a value in Redis without TTL."""
    cache = get_cache_service()
    if not cache._redis:
        return
    try:
        await cache._redis.set(key, value)
    except Exception as exc:
        logger.warning("Redis SET failed for %s: %s", key, exc)


async def _redis_incr(key: str) -> int:
    """Increment a counter in Redis and return the new value."""
    cache = get_cache_service()
    if not cache._redis:
        raise HTTPException(status_code=503, detail="Redis unavailable — governance storage offline.")
    try:
        return await cache._redis.incr(key)
    except Exception as exc:
        logger.error("Redis INCR failed for %s: %s", key, exc)
        raise HTTPException(status_code=503, detail="Redis unavailable — governance storage offline.")


async def _redis_sadd(key: str, value: str) -> None:
    """Add a member to a Redis set."""
    cache = get_cache_service()
    if not cache._redis:
        return
    try:
        await cache._redis.sadd(key, value)
    except Exception as exc:
        logger.warning("Redis SADD failed for %s: %s", key, exc)


async def _redis_smembers(key: str) -> set:
    """Get all members of a Redis set."""
    cache = get_cache_service()
    if not cache._redis:
        return set()
    try:
        return await cache._redis.smembers(key)
    except Exception as exc:
        logger.warning("Redis SMEMBERS failed for %s: %s", key, exc)
        return set()


async def _get_proposal(proposal_id: int) -> Optional[Dict[str, Any]]:
    """Load a proposal from Redis by ID."""
    raw = await _redis_get(f"{PROPOSAL_PREFIX}:{proposal_id}")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to decode proposal %d from Redis", proposal_id)
        return None


async def _save_proposal(proposal: Dict[str, Any]) -> None:
    """Save a proposal dict to Redis."""
    proposal_id = proposal["id"]
    await _redis_set(f"{PROPOSAL_PREFIX}:{proposal_id}", json.dumps(proposal, default=str))
    # Also track this ID in the index set
    await _redis_sadd(PROPOSAL_INDEX_KEY, str(proposal_id))


async def _get_all_proposals() -> List[Dict[str, Any]]:
    """Load all proposals from Redis."""
    proposal_ids = await _redis_smembers(PROPOSAL_INDEX_KEY)
    if not proposal_ids:
        return []

    proposals = []
    for pid_str in sorted(proposal_ids, key=lambda x: int(x)):
        p = await _get_proposal(int(pid_str))
        if p:
            proposals.append(p)
    return proposals


async def _invalidate_governance_cache() -> None:
    cache = get_cache_service()
    await cache.delete("governance:overview")
    await cache.delete("governance:proposals")


async def _hydrate_live_tally(proposal: Dict[str, Any]) -> Dict[str, Any]:
    algo = get_algorand_service()
    stake_snapshots = await algo.list_stake_snapshots()
    return calculate_live_tally(proposal, stake_snapshots=stake_snapshots)


async def _hydrate_live_tallies(proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not proposals:
        return []
    algo = get_algorand_service()
    stake_snapshots = await algo.list_stake_snapshots()
    return [calculate_live_tally(proposal, stake_snapshots=stake_snapshots) for proposal in proposals]


async def _record_vote(
    proposal_id: int,
    *,
    voter: str,
    vote: str,
    source: str,
    weight_override: int | None = None,
) -> tuple[Dict[str, Any], Dict[str, int]]:
    cache = get_cache_service()
    if not cache._redis:
        raise HTTPException(status_code=503, detail="Redis unavailable — governance storage offline.")

    redis_key = f"{PROPOSAL_PREFIX}:{proposal_id}"
    max_retries = 3

    for attempt in range(max_retries):
        try:
            async with cache._redis.pipeline(transaction=True) as pipe:
                await pipe.watch(redis_key)
                raw = await pipe.get(redis_key)
                if raw is None:
                    raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found.")

                try:
                    proposal = normalize_proposal(json.loads(raw))
                except json.JSONDecodeError as exc:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Corrupted proposal data for {proposal_id}.",
                    ) from exc

                if proposal["status"] != ProposalStatus.VOTING.value:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Proposal {proposal_id} is in '{proposal['status']}' status. "
                        f"Only proposals in 'voting' status accept votes.",
                    )

                if voter in proposal.get("vote_records", {}) or voter in proposal.get("legacy_voters", []):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Voter '{voter}' has already voted on proposal {proposal_id}.",
                    )

                algo = get_algorand_service()
                stake_snapshots = await algo.list_stake_snapshots()

                if source == "signed_wallet":
                    power_summary = calculate_voter_power(
                        voter,
                        proposal=proposal,
                        stake_snapshots=stake_snapshots,
                    )
                    if power_summary["effective_weight"] <= 0:
                        raise HTTPException(
                            status_code=400,
                            detail="Connected wallet has no active veCORTEX or delegated voting power.",
                        )
                else:
                    power_summary = {
                        "direct_weight": int(weight_override or 0),
                        "delegated_weight": 0,
                        "effective_weight": int(weight_override or 0),
                    }

                proposal.setdefault("vote_records", {})[voter] = {
                    "vote": vote,
                    "source": source,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "weight_override": weight_override,
                }
                proposal = calculate_live_tally(proposal, stake_snapshots=stake_snapshots)

                pipe.multi()
                pipe.setex(redis_key, PROPOSAL_TTL, json.dumps(proposal, default=str))
                await pipe.execute()

                await _invalidate_governance_cache()
                return proposal, power_summary
        except HTTPException:
            raise
        except Exception as exc:
            if "WATCH" in str(type(exc).__name__).upper() or "watch" in str(exc).lower():
                logger.warning(
                    "Vote race condition on proposal %d, retry %d/%d",
                    proposal_id,
                    attempt + 1,
                    max_retries,
                )
                continue
            raise

    raise HTTPException(status_code=409, detail="Vote conflict — please retry.")


def _require_governance_write_access(request: Request) -> None:
    api_key_data = getattr(request.state, "api_key_data", None)
    if not api_key_data:
        raise HTTPException(status_code=401, detail="API key required")

    raw_scopes = api_key_data.get("scopes") or []
    if isinstance(raw_scopes, str):
        scopes = {scope.strip() for scope in raw_scopes.split(",") if scope.strip()}
    else:
        scopes = {str(scope).strip() for scope in raw_scopes if str(scope).strip()}

    if "governance.write" in scopes:
        return

    runtime_tier = api_key_data.get("runtime_tier") or api_key_data.get("tier")
    if not scopes and runtime_tier == "admin":
        return

    raise HTTPException(status_code=403, detail="API key lacks governance.write scope")


def _proposal_to_summary(p: Dict[str, Any]) -> ProposalSummary:
    """Convert a raw proposal dict to a ProposalSummary."""
    return ProposalSummary(
        id=p["id"],
        title=p["title"],
        type=p.get("type", "general"),
        status=p["status"],
        proposer=p["proposer"],
        created_at=p["created_at"],
        votes_for=p.get("votes_for", 0),
        votes_against=p.get("votes_against", 0),
        voter_count=p.get("voter_count", len(p.get("voters", []))),
        curator_reviewed=p.get("curator_review") is not None,
    )


def _proposal_to_detail(p: Dict[str, Any]) -> ProposalDetail:
    """Convert a raw proposal dict to a ProposalDetail."""
    curator_review = None
    if p.get("curator_review"):
        curator_review = CuratorReview(**p["curator_review"])

    return ProposalDetail(
        id=p["id"],
        title=p["title"],
        description=p.get("description", ""),
        type=p.get("type", "general"),
        status=p["status"],
        proposer=p["proposer"],
        created_at=p["created_at"],
        votes_for=p.get("votes_for", 0),
        votes_against=p.get("votes_against", 0),
        voters=p.get("voters", []),
        curator_review=curator_review,
    )


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────
@router.get("/constitution", response_model=ConstitutionResponse)
@cache_with_ttl("governance:constitution", TTL_GOVERNANCE)
async def get_constitution():
    """
    Returns the full PURECORTEX Constitution.
    The Preamble is immutable; the Articles are amendable via governance.
    """
    preamble = _read_file(PREAMBLE_PATH)
    articles = _read_file(ARTICLES_PATH)

    if not preamble and not articles:
        raise HTTPException(
            status_code=404,
            detail="Constitution files not found. Ensure docs/tokenomics/constitution/ exists.",
        )

    return ConstitutionResponse(
        preamble=preamble,
        articles=articles,
    )


@router.get("/overview", response_model=GovernanceOverview)
async def get_governance_overview():
    """High-level governance stats computed from canonical proposal storage."""
    proposals = await _hydrate_live_tallies(await _get_all_proposals())

    total = len(proposals)
    active = sum(1 for p in proposals if p["status"] in ("active", "review"))
    voting = sum(1 for p in proposals if p["status"] == "voting")
    passed = sum(1 for p in proposals if p["status"] == "passed")
    rejected = sum(1 for p in proposals if p["status"] == "rejected")
    total_votes = sum(p.get("votes_for", 0) + p.get("votes_against", 0) for p in proposals)

    return GovernanceOverview(
        total_proposals=total,
        active_proposals=active,
        voting_proposals=voting,
        passed_proposals=passed,
        rejected_proposals=rejected,
        total_votes=total_votes,
    )


@router.get("/proposals", response_model=ProposalsListResponse)
async def list_proposals():
    """List all governance proposals with status and vote counts."""
    proposals = await _hydrate_live_tallies(await _get_all_proposals())
    summaries = [_proposal_to_summary(p) for p in proposals]
    # Sort by ID descending (newest first)
    summaries.sort(key=lambda s: s.id, reverse=True)

    return ProposalsListResponse(
        total=len(summaries),
        proposals=summaries,
    )


@router.get("/proposals/{proposal_id}", response_model=ProposalDetail)
async def get_proposal(proposal_id: int):
    """Get a specific proposal with full details including curator review and voter list."""
    proposal = await _get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=404,
            detail=f"Proposal {proposal_id} not found.",
        )

    return _proposal_to_detail(await _hydrate_live_tally(proposal))


@router.get("/proposals/{proposal_id}/power/{address}", response_model=VotePowerResponse)
async def get_proposal_vote_power(proposal_id: int, address: str):
    proposal = await _get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found.")

    try:
        algo = get_algorand_service()
        stake_snapshots = await algo.list_stake_snapshots()
        power_summary = calculate_voter_power(
            address,
            proposal=normalize_proposal(proposal),
            stake_snapshots=stake_snapshots,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return VotePowerResponse(
        proposal_id=proposal_id,
        voter=address,
        direct_weight=power_summary["direct_weight"],
        delegated_weight=power_summary["delegated_weight"],
        effective_weight=power_summary["effective_weight"],
    )


@router.post("/proposals", response_model=ProposalDetail, status_code=201)
async def create_proposal(body: ProposalCreateRequest, request: Request):
    """Create a new governance proposal in the canonical governance API."""
    _require_governance_write_access(request)
    # Generate next ID
    proposal_id = await _redis_incr(PROPOSAL_COUNTER_KEY)

    now = datetime.now(timezone.utc).isoformat()

    proposal = {
        "id": proposal_id,
        "title": body.title,
        "description": body.description,
        "type": body.type.value,
        "proposer": body.proposer,
        "status": ProposalStatus.REVIEW.value,
        "created_at": now,
        "votes_for": 0,
        "votes_against": 0,
        "voters": [],
        "voter_count": 0,
        "legacy_votes_for": 0,
        "legacy_votes_against": 0,
        "legacy_voter_count": 0,
        "legacy_voters": [],
        "vote_records": {},
        "curator_review": None,
    }

    await _save_proposal(proposal)
    logger.info("Proposal %d created by %s: %s", proposal_id, body.proposer, body.title)

    await _invalidate_governance_cache()

    return _proposal_to_detail(proposal)


@router.post("/proposals/{proposal_id}/review", response_model=ProposalDetail)
async def review_proposal(proposal_id: int, body: ReviewRequest, request: Request):
    """Curator reviews a proposal. Moves status to 'voting' if compliant, 'rejected' if not."""
    _require_governance_write_access(request)
    proposal = await _get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found.")

    if proposal["status"] not in (ProposalStatus.REVIEW.value, ProposalStatus.ACTIVE.value):
        raise HTTPException(
            status_code=400,
            detail=f"Proposal {proposal_id} is in '{proposal['status']}' status and cannot be reviewed. "
                   f"Only proposals in 'review' or 'active' status can be reviewed.",
        )

    now = datetime.now(timezone.utc).isoformat()

    proposal["curator_review"] = {
        "compliant": body.compliant,
        "analysis": body.analysis,
        "recommendation": body.recommendation,
        "curator_name": body.curator_name,
        "reviewed_at": now,
    }

    if body.compliant:
        proposal["status"] = ProposalStatus.VOTING.value
        logger.info("Proposal %d approved for voting by curator %s", proposal_id, body.curator_name)
    else:
        proposal["status"] = ProposalStatus.REJECTED.value
        logger.info("Proposal %d rejected by curator %s: %s", proposal_id, body.curator_name, body.recommendation)

    await _save_proposal(proposal)

    await _invalidate_governance_cache()

    return _proposal_to_detail(proposal)


@router.post("/proposals/{proposal_id}/vote", response_model=VoteResponse)
async def vote_on_proposal(proposal_id: int, body: VoteRequest, request: Request):
    """Internal/operator vote path for smoke tests and controlled automation."""
    _require_governance_write_access(request)
    proposal, _ = await _record_vote(
        proposal_id,
        voter=body.voter,
        vote=body.vote,
        source="api_key",
        weight_override=body.weight,
    )

    logger.info(
        "Internal vote on proposal %d: %s voted '%s' (weight=%d). Tally: %d for / %d against",
        proposal_id,
        body.voter,
        body.vote,
        body.weight,
        proposal["votes_for"],
        proposal["votes_against"],
    )

    return VoteResponse(
        proposal_id=proposal_id,
        voter=body.voter,
        vote=body.vote,
        weight=body.weight,
        votes_for=proposal["votes_for"],
        votes_against=proposal["votes_against"],
        direct_weight=body.weight,
        delegated_weight=0,
        auth_method="api_key",
    )


@router.post("/proposals/{proposal_id}/vote-signed", response_model=VoteResponse)
async def vote_on_proposal_signed(proposal_id: int, body: SignedVoteRequest):
    """Public wallet-signed vote path for live token-holder governance."""
    try:
        verify_signed_vote(
            proposal_id=proposal_id,
            voter=body.voter,
            vote=body.vote,
            issued_at=body.issued_at,
            nonce=body.nonce,
            signature_b64=body.signature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    proposal, power_summary = await _record_vote(
        proposal_id,
        voter=body.voter,
        vote=body.vote,
        source="signed_wallet",
    )

    logger.info(
        "Signed vote on proposal %d: %s voted '%s' (direct=%d delegated=%d). Tally: %d for / %d against",
        proposal_id,
        body.voter,
        body.vote,
        power_summary["direct_weight"],
        power_summary["delegated_weight"],
        proposal["votes_for"],
        proposal["votes_against"],
    )

    return VoteResponse(
        proposal_id=proposal_id,
        voter=body.voter,
        vote=body.vote,
        weight=power_summary["effective_weight"],
        votes_for=proposal["votes_for"],
        votes_against=proposal["votes_against"],
        direct_weight=power_summary["direct_weight"],
        delegated_weight=power_summary["delegated_weight"],
        auth_method="wallet_signature",
    )


# ──────────────────────────────────────────────
# On-chain governance reads
# ──────────────────────────────────────────────
ALGOD_URL = "https://testnet-api.algonode.cloud"

STATUS_NAMES = {0: "Discussion", 1: "Voting", 2: "Passed", 3: "Rejected", 4: "Executed", 5: "Cancelled"}
TYPE_NAMES_ONCHAIN = {0: "Parameter Change", 1: "Treasury Action", 2: "Protocol Upgrade", 3: "Emergency Action"}


class OnChainProposal(BaseModel):
    id: int
    proposer: str
    created_round: int
    type: int
    type_name: str
    yes_votes: int
    no_votes: int
    status: int
    status_name: str
    total_voters: int


class OnChainProposalsResponse(BaseModel):
    app_id: int
    total: int
    proposals: list[OnChainProposal]


def _encode_algorand_address(raw_bytes: bytes) -> str:
    """Encode 32 raw bytes to an Algorand address (base32 + checksum)."""
    import hashlib
    checksum = hashlib.sha512_256(raw_bytes).digest()[-4:]
    return base64.b32encode(raw_bytes + checksum).decode().rstrip("=")


async def _read_proposal_box(proposal_id: int) -> Optional[OnChainProposal]:
    """Read a single proposal from the governance contract's box storage."""
    key_bytes = struct.pack(">Q", proposal_id)
    b64_key = base64.b64encode(key_bytes).decode()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{ALGOD_URL}/v2/applications/{GOVERNANCE_APP_ID}/box",
            params={"name": f"b64:{b64_key}"},
            headers={"Accept": "application/json"},
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        raw = base64.b64decode(data["value"])
        if len(raw) != 80:
            return None

        proposer_bytes = raw[0:32]
        proposer = _encode_algorand_address(proposer_bytes)
        created_round = struct.unpack(">Q", raw[32:40])[0]
        ptype = struct.unpack(">Q", raw[40:48])[0]
        yes_votes = struct.unpack(">Q", raw[48:56])[0]
        no_votes = struct.unpack(">Q", raw[56:64])[0]
        status = struct.unpack(">Q", raw[64:72])[0]
        total_voters = struct.unpack(">Q", raw[72:80])[0]

        return OnChainProposal(
            id=proposal_id,
            proposer=proposer,
            created_round=created_round,
            type=ptype,
            type_name=TYPE_NAMES_ONCHAIN.get(ptype, "Unknown"),
            yes_votes=yes_votes,
            no_votes=no_votes,
            status=status,
            status_name=STATUS_NAMES.get(status, "Unknown"),
            total_voters=total_voters,
        )


@router.get("/onchain", response_model=OnChainProposalsResponse)
async def get_onchain_proposals():
    """Read all proposals directly from the on-chain GovernanceContract."""
    # Get proposal count from global state
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{ALGOD_URL}/v2/applications/{GOVERNANCE_APP_ID}",
            headers={"Accept": "application/json"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to query governance contract")

        data = resp.json()
        count = 0
        for kv in data.get("params", {}).get("global-state", []):
            key = base64.b64decode(kv["key"]).decode(errors="ignore")
            if key == "proposal_count":
                count = kv["value"].get("uint", 0)
                break

    if count == 0:
        return OnChainProposalsResponse(app_id=GOVERNANCE_APP_ID, total=0, proposals=[])

    # Fetch all proposals in parallel
    import asyncio
    tasks = [_read_proposal_box(i) for i in range(1, count + 1)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    proposals = []
    for r in results:
        if isinstance(r, OnChainProposal):
            proposals.append(r)

    # Newest first
    proposals.sort(key=lambda p: p.id, reverse=True)

    return OnChainProposalsResponse(
        app_id=GOVERNANCE_APP_ID,
        total=len(proposals),
        proposals=proposals,
    )
