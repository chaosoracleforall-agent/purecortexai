"""
Governance API for PureCortex.

Serves the PureCortex Constitution (Preamble + Articles) and provides
the proposal listing/detail endpoints for on-chain governance.
"""

import os
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.cache import cache_with_ttl, TTL_GOVERNANCE

router = APIRouter(prefix="/api/governance", tags=["governance"])

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
# Constitution files live at project root / docs / tokenomics / constitution
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
_CONSTITUTION_DIR = os.path.join(_PROJECT_ROOT, "docs", "tokenomics", "constitution")

PREAMBLE_PATH = os.path.join(_CONSTITUTION_DIR, "PREAMBLE.md")
ARTICLES_PATH = os.path.join(_CONSTITUTION_DIR, "ARTICLES.md")


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────
class ConstitutionResponse(BaseModel):
    preamble: str
    articles: str
    preamble_status: str = "IMMUTABLE"
    articles_status: str = "AMENDABLE"


class ProposalStatus(str, Enum):
    DISCUSSION = "discussion"
    VOTING = "voting"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class ProposalSummary(BaseModel):
    id: int
    title: str
    status: ProposalStatus
    proposer: str
    created_at: str
    voting_ends: Optional[str] = None
    votes_for: int = 0
    votes_against: int = 0
    quorum_reached: bool = False


class ProposalDetail(BaseModel):
    id: int
    title: str
    status: ProposalStatus
    proposer: str
    created_at: str
    voting_ends: Optional[str] = None
    votes_for: int = 0
    votes_against: int = 0
    quorum_reached: bool = False
    description: str = ""
    rationale: str = ""
    affected_articles: list[str] = []
    amendment_text: str = ""
    risk_analysis: str = ""
    discussion_url: Optional[str] = None


class GovernanceOverview(BaseModel):
    total_proposals: int
    active_proposals: list[ProposalSummary]
    participation_rate: float
    total_vecortex: int
    note: Optional[str] = None


class ProposalsListResponse(BaseModel):
    total: int
    proposals: list[ProposalSummary]
    note: Optional[str] = None


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _read_file(path: str) -> str:
    """Read a text file, returning empty string if not found."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────
@router.get("/constitution", response_model=ConstitutionResponse)
@cache_with_ttl("governance:constitution", TTL_GOVERNANCE)
async def get_constitution():
    """
    Returns the full PureCortex Constitution.
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
@cache_with_ttl("governance:overview", TTL_GOVERNANCE)
async def get_governance_overview():
    """High-level governance stats (proposals, participation, veCORTEX)."""
    return GovernanceOverview(
        total_proposals=0,
        active_proposals=[],
        participation_rate=0.0,
        total_vecortex=0,
        note="Governance launches at TGE (March 31, 2026)",
    )


@router.get("/proposals", response_model=ProposalsListResponse)
@cache_with_ttl("governance:proposals", TTL_GOVERNANCE)
async def list_proposals():
    """List all governance proposals."""
    return ProposalsListResponse(
        total=0,
        proposals=[],
        note="Governance launches at TGE (March 31, 2026)",
    )


@router.get("/proposals/{proposal_id}", response_model=ProposalDetail)
async def get_proposal(proposal_id: int):
    """Get a single proposal by ID."""
    # No proposals exist pre-TGE
    raise HTTPException(
        status_code=404,
        detail=f"Proposal {proposal_id} not found. Governance launches at TGE (March 31, 2026).",
    )
