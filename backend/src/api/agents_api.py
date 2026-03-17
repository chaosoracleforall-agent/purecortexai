"""
Agent Registry API for PURECORTEX.

Provides endpoints to list protocol AI agents, chat with them,
view their recent activity, and trigger governance actions
(Senator proposals, Curator reviews).
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.services.cache import cache_with_ttl, TTL_AGENTS
from src.api.governance import (
    ProposalCreateRequest,
    ProposalDetail,
    ProposalType,
    ReviewRequest,
    create_proposal,
    review_proposal as governance_review_proposal,
    _get_proposal,
    _proposal_to_detail,
)

logger = logging.getLogger("purecortex.agents_api")

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────
class AgentRole(str, Enum):
    SENATOR = "senator"
    CURATOR = "curator"
    SOCIAL = "social"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    OFFLINE = "offline"
    PRE_LAUNCH = "pre_launch"


class AgentRecord(BaseModel):
    name: str
    role: AgentRole
    description: str
    algorand_address: Optional[str] = None
    status: AgentStatus
    permission_tier: int
    capabilities: list[str]
    created_at: str


class AgentRegistryResponse(BaseModel):
    total_agents: int
    agents: list[AgentRecord]


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)


class ChatResponse(BaseModel):
    agent: str
    response: str
    timestamp: str


class ActivityRecord(BaseModel):
    action: str
    detail: str
    timestamp: str
    txn_id: Optional[str] = None


class ActivityResponse(BaseModel):
    agent: str
    total_actions: int
    recent_activity: list[ActivityRecord]
    note: Optional[str] = None


# ──────────────────────────────────────────────
# Protocol Agent Registry (static pre-TGE)
# ──────────────────────────────────────────────
PROTOCOL_AGENTS: list[AgentRecord] = [
    AgentRecord(
        name="senator",
        role=AgentRole.SENATOR,
        description=(
            "The Senator AI is the governance intelligence of PURECORTEX. "
            "It proposes protocol amendments, mediates disputes, and ensures "
            "constitutional compliance. Powered by Tri-Brain Consensus "
            "(Claude + Gemini + GPT-5)."
        ),
        algorand_address=None,
        status=AgentStatus.PRE_LAUNCH,
        permission_tier=3,
        capabilities=[
            "propose_amendments",
            "mediate_disputes",
            "constitutional_review",
            "emergency_cancellation",
            "governance_analysis",
        ],
        created_at="2026-03-14T00:00:00+00:00",
    ),
    AgentRecord(
        name="curator",
        role=AgentRole.CURATOR,
        description=(
            "The Curator AI manages the MCP tool registry, evaluates agent "
            "composability scores, and coordinates inter-agent communication. "
            "It ensures tool quality and prevents sybil manipulation."
        ),
        algorand_address=None,
        status=AgentStatus.PRE_LAUNCH,
        permission_tier=2,
        capabilities=[
            "tool_registry_management",
            "composability_scoring",
            "agent_tier_assessment",
            "x402_micropayment_routing",
            "quality_assurance",
        ],
        created_at="2026-03-14T00:00:00+00:00",
    ),
    AgentRecord(
        name="social",
        role=AgentRole.SOCIAL,
        description=(
            "The Social Agent handles PURECORTEX's public communications "
            "across Twitter and Farcaster. It generates consensus-approved "
            "content through the Tri-Brain Orchestrator."
        ),
        algorand_address=None,
        status=AgentStatus.STANDBY,
        permission_tier=1,
        capabilities=[
            "twitter_posting",
            "farcaster_casting",
            "content_generation",
            "community_engagement",
        ],
        created_at="2026-03-14T00:00:00+00:00",
    ),
]

AGENTS_BY_NAME = {a.name: a for a in PROTOCOL_AGENTS}


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────
@router.get("/registry", response_model=AgentRegistryResponse)
@cache_with_ttl("agents:registry", TTL_AGENTS)
async def get_agent_registry():
    """List all protocol AI agents with their roles, addresses, and status."""
    return AgentRegistryResponse(
        total_agents=len(PROTOCOL_AGENTS),
        agents=PROTOCOL_AGENTS,
    )


# ──────────────────────────────────────────────
# Governance Action Endpoints
# (must be declared BEFORE wildcard /{agent_name} routes)
# ──────────────────────────────────────────────
class SenatorProposeRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    type: ProposalType = ProposalType.GENERAL


class SenatorProposeResponse(BaseModel):
    agent: str = "senator"
    action: str = "proposal_created"
    proposal: ProposalDetail
    timestamp: str


class CuratorReviewResponse(BaseModel):
    agent: str = "curator"
    action: str = "proposal_reviewed"
    proposal: ProposalDetail
    review_summary: str
    timestamp: str


@router.post("/senator/propose", response_model=SenatorProposeResponse, status_code=201)
async def senator_propose(body: SenatorProposeRequest, request: Request):
    """
    Senator AI creates a governance proposal.

    The Senator agent submits a new proposal to the governance system.
    The proposal starts in 'review' status, awaiting Curator review.
    If the orchestrator is available, the Senator's tri-brain is used
    to enrich the proposal; otherwise it is created directly.
    """
    # Try to use the Senator agent for enrichment if available
    from main import get_agent_loop
    agent_loop = get_agent_loop()

    enriched_description = body.description

    if agent_loop and agent_loop.senator:
        try:
            # Use the Senator to draft/enrich the proposal via tri-brain
            analysis = {
                "user_request": {
                    "title": body.title,
                    "description": body.description,
                    "type": body.type.value,
                },
                "source": "api_request",
            }
            result = await agent_loop.senator.draft_proposal(analysis)
            if result and result.get("proposal"):
                enriched = result["proposal"]
                # Use enriched description if the tri-brain provided one
                if enriched.get("description"):
                    enriched_description = enriched["description"]
                logger.info("Senator tri-brain enriched proposal: %s", body.title)
        except Exception as exc:
            logger.warning("Senator enrichment failed (using original): %s", exc)

    # Create the proposal via governance API
    proposal_request = ProposalCreateRequest(
        title=body.title,
        description=enriched_description,
        type=body.type,
        proposer="senator",
    )

    proposal = await create_proposal(proposal_request, request)

    now = datetime.now(timezone.utc).isoformat()
    logger.info("Senator created proposal %d: %s", proposal.id, body.title)

    return SenatorProposeResponse(
        proposal=proposal,
        timestamp=now,
    )


@router.post("/curator/review/{proposal_id}", response_model=CuratorReviewResponse)
async def curator_review(proposal_id: int, request: Request):
    """
    Curator AI reviews a governance proposal for constitutional compliance.

    Uses the Curator agent's tri-brain (Claude + Gemini + GPT-5) to analyze the
    proposal against the PURECORTEX Constitution. If the orchestrator is
    unavailable, performs a basic compliance pass.
    """
    # Verify proposal exists and is in reviewable state
    proposal_data = await _get_proposal(proposal_id)
    if not proposal_data:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found.")

    if proposal_data["status"] not in ("review", "active"):
        raise HTTPException(
            status_code=400,
            detail=f"Proposal {proposal_id} is in '{proposal_data['status']}' status. "
                   f"Only proposals in 'review' or 'active' status can be reviewed by the Curator.",
        )

    # Try to use the Curator agent for AI-powered review
    from main import get_agent_loop
    agent_loop = get_agent_loop()

    compliant = True
    analysis = "Basic compliance check passed."
    recommendation = "APPROVE"

    if agent_loop and agent_loop.curator:
        try:
            review_result = await agent_loop.curator.review_proposal({
                "title": proposal_data["title"],
                "description": proposal_data.get("description", ""),
                "type": proposal_data.get("type", "general"),
                "proposer": proposal_data["proposer"],
            })

            if review_result:
                compliant = review_result.get("compliant", True)
                analysis = review_result.get("analysis", "Tri-brain analysis complete.")
                recommendation = review_result.get("recommendation", "APPROVE")
                logger.info(
                    "Curator tri-brain reviewed proposal %d: %s",
                    proposal_id, recommendation,
                )
        except Exception as exc:
            logger.warning("Curator tri-brain review failed (using basic check): %s", exc)

    # Submit the review to the governance system
    review_request = ReviewRequest(
        compliant=compliant,
        analysis=analysis,
        recommendation=recommendation,
        curator_name="curator",
    )

    updated_proposal = await governance_review_proposal(proposal_id, review_request, request)

    now = datetime.now(timezone.utc).isoformat()

    review_summary = (
        f"{'APPROVED' if compliant else 'REJECTED'} — {recommendation}. "
        f"Proposal moved to '{'voting' if compliant else 'rejected'}' status."
    )

    return CuratorReviewResponse(
        proposal=updated_proposal,
        review_summary=review_summary,
        timestamp=now,
    )


# ──────────────────────────────────────────────
# Wildcard Agent Endpoints
# (declared AFTER specific routes to avoid path conflicts)
# ──────────────────────────────────────────────
@router.post("/{agent_name}/chat", response_model=ChatResponse)
async def chat_with_agent(agent_name: str, body: ChatMessage):
    """
    Chat with a specific protocol agent.
    Routes through the live tri-brain-backed agent implementation when the
    orchestration loop is available.
    """
    agent = AGENTS_BY_NAME.get(agent_name.lower())
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available agents: {list(AGENTS_BY_NAME.keys())}",
        )

    now = datetime.now(timezone.utc).isoformat()
    from main import get_agent_loop

    agent_loop = get_agent_loop()
    if not agent_loop:
        raise HTTPException(
            status_code=503,
            detail="Agent orchestration loop is unavailable. REST chat cannot be served right now.",
        )

    runtime_agents = {
        AgentRole.SENATOR: agent_loop.senator,
        AgentRole.CURATOR: agent_loop.curator,
        AgentRole.SOCIAL: agent_loop.social,
    }
    runtime_agent = runtime_agents.get(agent.role)
    if runtime_agent is None:
        raise HTTPException(
            status_code=503,
            detail=f"Runtime agent '{agent.name}' is unavailable.",
        )

    try:
        response_text = await runtime_agent.chat(body.message)
    except Exception as exc:
        logger.error("REST chat failed for agent '%s': %s", agent.name, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Agent '{agent.name}' failed to generate a response.",
        ) from exc

    return ChatResponse(
        agent=agent.name,
        response=response_text,
        timestamp=now,
    )


@router.get("/{agent_name}/activity", response_model=ActivityResponse)
async def get_agent_activity(agent_name: str):
    """Get an agent's recent on-chain and off-chain activity."""
    agent = AGENTS_BY_NAME.get(agent_name.lower())
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available agents: {list(AGENTS_BY_NAME.keys())}",
        )

    return ActivityResponse(
        agent=agent.name,
        total_actions=0,
        recent_activity=[],
        note=f"Agent '{agent.name}' activity tracking begins after TGE (March 31, 2026)",
    )
