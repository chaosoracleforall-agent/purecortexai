"""Seed targets and scoring helpers for the social interaction campaign."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

SOCIAL_CAMPAIGN_TARGETS: list[dict[str, Any]] = [
    {
        "handle": "Algorand",
        "category": "foundation",
        "priority": 10,
        "tag_worthy": True,
        "relationship_stage": "seeded",
        "engage_topics": ["algorand", "infrastructure", "governance"],
        "rationale": "Core chain account and highest-signal ecosystem announcements.",
    },
    {
        "handle": "AlgoFoundation",
        "category": "foundation",
        "priority": 10,
        "tag_worthy": True,
        "relationship_stage": "seeded",
        "engage_topics": ["foundation", "grants", "governance"],
        "rationale": "Foundation programs, funding, ecosystem growth, and governance visibility.",
    },
    {
        "handle": "PeraAlgoWallet",
        "category": "wallet",
        "priority": 9,
        "tag_worthy": True,
        "relationship_stage": "seeded",
        "engage_topics": ["wallet", "ux", "consumer_apps"],
        "rationale": "Most visible wallet surface in the Algorand ecosystem.",
    },
    {
        "handle": "FolksFinance",
        "category": "defi",
        "priority": 9,
        "tag_worthy": True,
        "relationship_stage": "seeded",
        "engage_topics": ["defi", "liquidity", "governance"],
        "rationale": "Major DeFi operator and source of high-context ecosystem conversations.",
    },
    {
        "handle": "Tinymanorg",
        "category": "defi",
        "priority": 9,
        "tag_worthy": True,
        "relationship_stage": "seeded",
        "engage_topics": ["defi", "liquidity", "amm"],
        "rationale": "Core AMM and launch/liquidity venue adjacent to PURECORTEX flows.",
    },
    {
        "handle": "TxnLab",
        "category": "developer_tools",
        "priority": 9,
        "tag_worthy": True,
        "relationship_stage": "seeded",
        "engage_topics": ["developer_tools", "sdk", "algokit"],
        "rationale": "Developer tooling, wallets, and app infrastructure relevant to builders.",
    },
    {
        "handle": "AlgoNode",
        "category": "infrastructure",
        "priority": 8,
        "tag_worthy": False,
        "relationship_stage": "seeded",
        "engage_topics": ["infrastructure", "rpc", "indexer"],
        "rationale": "Indexer and RPC infrastructure used by many Algorand apps.",
    },
    {
        "handle": "NFDomains",
        "category": "identity",
        "priority": 8,
        "tag_worthy": False,
        "relationship_stage": "seeded",
        "engage_topics": ["identity", "consumer_apps", "ecosystem"],
        "rationale": "Identity and naming layer with broad ecosystem reach.",
    },
    {
        "handle": "vestigefi",
        "category": "analytics",
        "priority": 8,
        "tag_worthy": False,
        "relationship_stage": "seeded",
        "engage_topics": ["analytics", "markets", "defi"],
        "rationale": "Market intelligence and ecosystem activity tracking.",
    },
    {
        "handle": "xBacked_",
        "category": "assets",
        "priority": 8,
        "tag_worthy": False,
        "relationship_stage": "seeded",
        "engage_topics": ["defi", "assets", "infrastructure"],
        "rationale": "Real-world asset and composability discussions intersect with agent commerce.",
    },
    {
        "handle": "Lofty_AI",
        "category": "consumer_apps",
        "priority": 7,
        "tag_worthy": False,
        "relationship_stage": "seeded",
        "engage_topics": ["consumer_apps", "assets", "governance"],
        "rationale": "Mainstream Algorand app with tokenized real-world asset narrative.",
    },
    {
        "handle": "TravelX__",
        "category": "consumer_apps",
        "priority": 7,
        "tag_worthy": False,
        "relationship_stage": "seeded",
        "engage_topics": ["consumer_apps", "tickets", "infrastructure"],
        "rationale": "Large-scale consumer app and strong signal for real-world adoption stories.",
    },
]

GLOBAL_KEYWORDS = {
    "algorand",
    "algo",
    "avm",
    "algokit",
    "arc",
    "indexer",
    "wallet",
    "governance",
    "validator",
    "launchpad",
    "developer",
    "builders",
    "sdk",
    "agent",
    "agents",
    "ai",
    "token",
    "protocol",
    "mcp",
}

TOPIC_KEYWORDS: dict[str, set[str]] = {
    "algorand": {"algorand", "algo", "avm", "arc"},
    "foundation": {"foundation", "grant", "ecosystem", "builders"},
    "grants": {"grant", "funding", "builders", "accelerator"},
    "governance": {"governance", "vote", "proposal", "constitutional"},
    "wallet": {"wallet", "wallets", "mobile", "payments", "consumer"},
    "ux": {"ux", "user experience", "flow", "onboarding"},
    "consumer_apps": {"consumer", "users", "adoption", "app", "apps"},
    "defi": {"defi", "liquidity", "yield", "swap", "amm", "lp"},
    "liquidity": {"liquidity", "amm", "pool", "swap"},
    "amm": {"amm", "swap", "pool", "liquidity"},
    "developer_tools": {"sdk", "tooling", "developer", "builders", "algokit"},
    "sdk": {"sdk", "typescript", "python", "api"},
    "algokit": {"algokit", "devex", "developer"},
    "infrastructure": {"infrastructure", "node", "rpc", "indexer", "throughput"},
    "rpc": {"rpc", "throughput", "latency", "node"},
    "indexer": {"indexer", "data", "query", "analytics"},
    "identity": {"identity", "domain", "naming", "profile"},
    "analytics": {"analytics", "metrics", "dashboard", "market"},
    "markets": {"market", "price", "liquidity", "trading"},
    "assets": {"asset", "rwа", "rwa", "tokenized", "tokenization"},
    "tickets": {"ticket", "travel", "commerce", "consumer"},
    "ecosystem": {"ecosystem", "builders", "launch", "community"},
}

UNSAFE_REPLY_KEYWORDS = {
    "price target",
    "moon",
    "pump",
    "giveaway",
    "airdrop",
    "buy now",
    "sell now",
    "financial advice",
}

SENSITIVE_TOPIC_KEYWORDS = {
    "layoff",
    "layoffs",
    "reduce our workforce",
    "reduction in force",
    "downturn in crypto markets",
    "macro environment",
    "bear market",
    "hack",
    "hacked",
    "exploit",
    "incident",
    "breach",
    "phishing",
    "lawsuit",
    "investigation",
    "passed away",
    "rip ",
}

LOW_SIGNAL_KEYWORDS = {
    "gm",
    "good morning",
    "good night",
    "weekend",
    "happy friday",
    "monday motivation",
}

MAX_CANDIDATE_AGE = timedelta(days=14)


def get_seed_targets() -> list[dict[str, Any]]:
    """Return a deep copy of the default campaign target registry."""
    return deepcopy(SOCIAL_CAMPAIGN_TARGETS)


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            normalized = value.replace("Z", "+00:00").replace(" ", "T")
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def score_target_tweet(text: str, target: dict[str, Any], created_at: Any = None) -> tuple[int, list[str]]:
    """Score a tweet for reply-worthiness relative to PURECORTEX's campaign."""
    normalized = (text or "").lower()
    reasons: list[str] = []

    if not normalized:
        return 0, reasons

    published_at = _coerce_datetime(created_at)
    if published_at and datetime.now(timezone.utc) - published_at > MAX_CANDIDATE_AGE:
        return 0, ["stale_post"]

    if any(sensitive in normalized for sensitive in SENSITIVE_TOPIC_KEYWORDS):
        return 0, ["sensitive_topic"]

    if any(unsafe in normalized for unsafe in UNSAFE_REPLY_KEYWORDS):
        return 0, ["unsafe_topic"]

    if any(low_signal in normalized for low_signal in LOW_SIGNAL_KEYWORDS):
        return 0, ["low_signal"]

    score = 0

    if any(keyword in normalized for keyword in GLOBAL_KEYWORDS):
        score += 2
        reasons.append("ecosystem_relevance")

    matched_topics = 0
    for topic in target.get("engage_topics", []):
        keywords = TOPIC_KEYWORDS.get(topic, set())
        if keywords and any(keyword in normalized for keyword in keywords):
            matched_topics += 1
            score += 2
            reasons.append(f"topic:{topic}")

    if "?" in text:
        score += 1
        reasons.append("conversation_hook")

    if any(token in normalized for token in ("ai", "agent", "agents", "automation", "autonomous")):
        score += 2
        reasons.append("agent_adjacency")

    priority_bonus = max(0, int(target.get("priority", 0)) - 7)
    if priority_bonus:
        score += priority_bonus
        reasons.append("priority_target")

    if matched_topics >= 2:
        score += 1
        reasons.append("multi_topic_overlap")

    # Foundation and top-level ecosystem accounts should only trigger when the
    # post also lands on concrete PURECORTEX-adjacent topics, not general brand
    # or organizational updates.
    if target.get("category") == "foundation" and matched_topics == 0:
        return 0, ["foundation_non_actionable"]

    if matched_topics == 0 and score < 5:
        return 0, ["weak_fit"]

    return score, reasons[:5]
