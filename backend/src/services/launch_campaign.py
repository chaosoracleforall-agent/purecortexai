"""
MainNet Launch Campaign content templates for the Social Agent.

Provides structured, pre-approved content seeds that the tri-brain consensus
engine can adapt and personalize. These are NOT posted directly — they go
through the Social Agent's full think() pipeline.
"""

from __future__ import annotations

from typing import Any

LAUNCH_COUNTDOWN_PROMPTS: list[dict[str, Any]] = [
    {
        "day_offset": -9,
        "content_type": "thread",
        "topic": "What is PURECORTEX?",
        "seed": (
            "Introduce PURECORTEX to the Algorand community. "
            "Explain: sovereign AI agent launchpad, bonding curves for agents, "
            "tri-brain consensus (Claude + Gemini + GPT-5), on-chain constitution. "
            "Tone: authoritative, not hype. End with: 'Testnet is live. Explore it.'"
        ),
    },
    {
        "day_offset": -8,
        "content_type": "protocol_update",
        "topic": "Why Algorand?",
        "seed": (
            "Explain why PURECORTEX chose Algorand over Solana, Base, or Ethereum. "
            "Key points: instant finality for agent settlements, sub-cent fees for "
            "micropayments, AVM prevents reentrancy by design, Puya contracts in Python. "
            "No chain tribalism — just technical merit."
        ),
    },
    {
        "day_offset": -7,
        "content_type": "tokenomics_education",
        "topic": "Tokenomics: 0% VC, 90% to holders",
        "seed": (
            "Break down CORTEX tokenomics. 0% VC. 0% team. 10% creator with 180-day vest. "
            "90% of ALL protocol revenue goes to Assistance Fund for continuous buyback-burn. "
            "31% genesis airdrop to community. Compare: most protocols give 20%+ to insiders."
        ),
    },
    {
        "day_offset": -6,
        "content_type": "governance_highlight",
        "topic": "The PURECORTEX Constitution",
        "seed": (
            "Introduce the on-chain Constitution: immutable Preamble, 7 amendable Articles. "
            "Agent sovereignty, fail-closed safety, 90/10 revenue split is constitutionally protected. "
            "Senator proposes, Lawmakers decide, veCORTEX holders have final say. "
            "Quote one principle from the Preamble."
        ),
    },
    {
        "day_offset": -5,
        "content_type": "agent_ecosystem",
        "topic": "Tri-Brain Consensus explained",
        "seed": (
            "Explain how tri-brain consensus works: Claude Opus 4.6 + Gemini 2.5 Pro + GPT-5 "
            "run in parallel. 2-of-3 majority for high-risk actions. Fail-closed when no "
            "consensus. No single AI model has unilateral control. This is how you make AI "
            "agents safe enough for real economic activity."
        ),
    },
    {
        "day_offset": -4,
        "content_type": "community_engagement",
        "topic": "Genesis Airdrop preview",
        "seed": (
            "Announce the Genesis Airdrop structure: 31% of CORTEX supply. "
            "7 eligibility tiers: testnet pioneers, Algorand DeFi users, governors, "
            "NFD holders, developers, social campaign, community tasks. "
            "Registration opens March 31. No purchase necessary."
        ),
    },
    {
        "day_offset": -3,
        "content_type": "thread",
        "topic": "Developer stack overview",
        "seed": (
            "Show what developers get: Python SDK, TypeScript SDK, CLI (pcx), "
            "MCP server for AI tool integration, REST API with WebSocket chat. "
            "All open source. Deploy an agent, give it a bonding curve, let it earn. "
            "Link to testnet."
        ),
    },
    {
        "day_offset": -2,
        "content_type": "metrics_report",
        "topic": "Testnet milestone recap",
        "seed": (
            "Share testnet activity metrics: contracts deployed, agents created, "
            "governance proposals processed, tri-brain consensus decisions made. "
            "Frame as: 'Built in public. Verified on testnet. Ready for mainnet.'"
        ),
    },
    {
        "day_offset": -1,
        "content_type": "protocol_update",
        "topic": "Tomorrow: Genesis",
        "seed": (
            "Final pre-launch post. GitHub repo goes public. Airdrop registration opens. "
            "Contracts audited. Constitution ratified. The sovereign operating surface "
            "for AI agents on Algorand launches in 24 hours."
        ),
    },
    {
        "day_offset": 0,
        "content_type": "thread",
        "topic": "LAUNCH: PURECORTEX is live on Algorand MainNet",
        "seed": (
            "Major announcement thread. PURECORTEX is now live on Algorand MainNet. "
            "Cover: MainNet contracts deployed, CORTEX token live, airdrop claims open, "
            "staking available, governance active, Assistance Fund operational. "
            "Include on-chain IDs. End with call-to-action: check your airdrop eligibility."
        ),
    },
    {
        "day_offset": 1,
        "content_type": "metrics_report",
        "topic": "First 24 hours of PURECORTEX",
        "seed": (
            "Share Day 1 metrics: wallets connected, airdrop registrations, "
            "first governance proposal, first agent created on mainnet. "
            "Transparent data, no inflated vanity numbers."
        ),
    },
]


PARTNERSHIP_ANNOUNCEMENT_TEMPLATES: list[dict[str, Any]] = [
    {
        "partner": "tinyman",
        "content_type": "protocol_update",
        "seed": (
            "CORTEX/ALGO liquidity is now live on @Tinymanorg. "
            "The first sovereign AI agent token pair on Algorand's primary AMM."
        ),
    },
    {
        "partner": "pact",
        "content_type": "protocol_update",
        "seed": (
            "CORTEX/ALGO pool is live on @paboracle (Pact). "
            "Dual DEX liquidity from day one."
        ),
    },
]


def get_launch_prompt_for_day(days_until_tge: int) -> dict[str, Any] | None:
    """Return the campaign prompt for the given day offset from TGE."""
    for prompt in LAUNCH_COUNTDOWN_PROMPTS:
        if prompt["day_offset"] == -days_until_tge:
            return prompt
    return None


def get_all_launch_prompts() -> list[dict[str, Any]]:
    """Return all launch campaign prompts in chronological order."""
    return sorted(LAUNCH_COUNTDOWN_PROMPTS, key=lambda p: p["day_offset"])
