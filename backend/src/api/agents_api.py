"""
Agent Registry API for PureCortex.

Provides endpoints to list protocol AI agents, chat with them,
and view their recent activity.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.cache import cache_with_ttl, TTL_AGENTS

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
    message: str


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
            "The Senator AI is the governance intelligence of PureCortex. "
            "It proposes protocol amendments, mediates disputes, and ensures "
            "constitutional compliance. Powered by Dual-Brain Consensus "
            "(Claude + Gemini)."
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
            "The Social Agent handles PureCortex's public communications "
            "across Twitter and Farcaster. It generates consensus-approved "
            "content through the Dual-Brain Orchestrator."
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


@router.post("/{agent_name}/chat", response_model=ChatResponse)
async def chat_with_agent(agent_name: str, body: ChatMessage):
    """
    Chat with a specific protocol agent.
    Currently returns a placeholder response. Post-TGE, this will route
    through the Dual-Brain Orchestrator with agent-specific system prompts.
    """
    agent = AGENTS_BY_NAME.get(agent_name.lower())
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available agents: {list(AGENTS_BY_NAME.keys())}",
        )

    now = datetime.now(timezone.utc).isoformat()

    # Placeholder responses per agent role
    responses = {
        AgentRole.SENATOR: (
            f"[Senator AI] I acknowledge your message: \"{body.message}\". "
            "Full conversational capabilities will be available after TGE "
            "(March 31, 2026). I will then be able to discuss governance proposals, "
            "constitutional interpretations, and protocol policy."
        ),
        AgentRole.CURATOR: (
            f"[Curator AI] Message received: \"{body.message}\". "
            "The MCP tool registry and composability scoring system activates "
            "at TGE. I will then assist with tool discovery, agent interoperability, "
            "and quality assessments."
        ),
        AgentRole.SOCIAL: (
            f"[Social Agent] Noted: \"{body.message}\". "
            "Social broadcasting capabilities are in standby mode. "
            "Post-TGE, I will generate and publish consensus-approved content "
            "across connected platforms."
        ),
    }

    return ChatResponse(
        agent=agent.name,
        response=responses.get(agent.role, "Agent response unavailable."),
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
