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
    {
        "day_offset": 2,
        "content_type": "protocol_update",
        "topic": "CORTEX liquidity is live on Tinyman and Pact",
        "seed": (
            "Announce dual-DEX liquidity: CORTEX/ALGO pools live on @Tinymanorg (60%) "
            "and @paboracle Pact (40%). 15% of total supply seeded as liquidity. "
            "Share pool addresses. Link to both DEXs. Transparent launch — no hidden "
            "pre-mine, no insider allocations."
        ),
    },
    {
        "day_offset": 3,
        "content_type": "tokenomics_education",
        "topic": "How the Assistance Fund buyback-burn works",
        "seed": (
            "Explain the 90/10 revenue model now live on mainnet. 90% of ALL protocol "
            "fees flow to the Assistance Fund for continuous CORTEX buyback-and-burn. "
            "This is constitutionally protected — cannot be changed without supermajority. "
            "Share the Sovereign Treasury contract address for on-chain verification."
        ),
    },
    {
        "day_offset": 4,
        "content_type": "governance_highlight",
        "topic": "Governance is open: first proposals live",
        "seed": (
            "Announce governance is active. Proposal 0: Ratify the Constitution on-chain. "
            "Explain how to participate: stake CORTEX → get veCORTEX → vote. "
            "Senator Agent drafts proposals, community decides. Link to governance page."
        ),
    },
    {
        "day_offset": 5,
        "content_type": "community_engagement",
        "topic": "Airdrop claims countdown",
        "seed": (
            "Remind community: airdrop claims open April 21. 950 wallets eligible across "
            "3 active tiers so far. Registration still open for social campaign tier. "
            "Check eligibility at purecortex.ai/airdrop. 90-day claim window."
        ),
    },
    {
        "day_offset": 6,
        "content_type": "agent_ecosystem",
        "topic": "Create your first AI agent on PURECORTEX",
        "seed": (
            "Tutorial thread: how to create an AI agent on PURECORTEX. "
            "Each agent gets its own bonding curve token. Agents operate autonomously "
            "with tri-brain consensus. Walk through the marketplace creation flow. "
            "End with: 'Your agent, your economy.'"
        ),
    },
    {
        "day_offset": 7,
        "content_type": "metrics_report",
        "topic": "Week 1 protocol health report",
        "seed": (
            "Share Week 1 on-chain metrics: total agents created, CORTEX burned via "
            "Assistance Fund, governance participation rate, staking TVL, DEX volume. "
            "Transparent weekly cadence — the Senator Agent will publish these ongoing."
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
    """Return the campaign prompt for the given day offset from TGE.

    If an exact match is not found and we are post-TGE (days_until_tge < 0),
    returns the highest-offset prompt that hasn't been surpassed yet — this
    enables catch-up when previous days' content was missed.
    """
    target_offset = -days_until_tge

    # Exact match first
    for prompt in LAUNCH_COUNTDOWN_PROMPTS:
        if prompt["day_offset"] == target_offset:
            return prompt

    # Catch-up: if post-TGE and no exact match, find the latest undelivered prompt
    if target_offset > 0:
        candidates = [
            p for p in LAUNCH_COUNTDOWN_PROMPTS
            if 0 <= p["day_offset"] <= target_offset
        ]
        if candidates:
            return max(candidates, key=lambda p: p["day_offset"])

    return None


def get_missed_prompts(days_until_tge: int, posted_offsets: set[int] | None = None) -> list[dict[str, Any]]:
    """Return launch prompts that should have been posted but were missed.

    Args:
        days_until_tge: Current days until TGE (negative = post-TGE).
        posted_offsets: Set of day_offset values already posted (from memory).
                        If None, returns all post-TGE prompts up to today.
    """
    if days_until_tge >= 0:
        return []

    current_offset = -days_until_tge
    posted = posted_offsets or set()

    return sorted(
        [
            p for p in LAUNCH_COUNTDOWN_PROMPTS
            if 0 <= p["day_offset"] <= current_offset and p["day_offset"] not in posted
        ],
        key=lambda p: p["day_offset"],
    )


def get_all_launch_prompts() -> list[dict[str, Any]]:
    """Return all launch campaign prompts in chronological order."""
    return sorted(LAUNCH_COUNTDOWN_PROMPTS, key=lambda p: p["day_offset"])
