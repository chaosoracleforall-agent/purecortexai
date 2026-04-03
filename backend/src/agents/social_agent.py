"""
Social Media AI Agent for PURECORTEX.

Manages the @purecortexai presence on X (Twitter) using tri-brain consensus
(Claude Opus 4.6 + Gemini 2.5 Pro + GPT-5) for content generation and engagement decisions.

Capabilities:
  - Generate and post content about PURECORTEX (protocol updates, metrics, education)
  - Engage with community (reply to mentions, quote tweets)
  - Coordinate messaging with protocol events (proposals, burns, milestones)
  - Learn from engagement metrics to improve content strategy via episodic memory

Content types: protocol updates, tokenomics education, governance highlights,
agent ecosystem news, community engagement, memes/viral content.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import tweepy

from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionTier
from src.services.protocol_config import CORTEX_ASSET_ID, CORTEX_NAME, CORTEX_UNIT_NAME
from src.services.social_campaign import (
    get_search_queries,
    get_search_queries_for_cycle,
    get_seed_targets,
    score_engagement_candidate,
    score_target_tweet,
)
from src.services.launch_campaign import get_launch_prompt_for_day
from src.services.engagement_scheduler import (
    CYCLE_MAX_FOLLOWS,
    CYCLE_MAX_LIKES,
    CYCLE_MAX_MENTION_REPLIES,
    CYCLE_MAX_QUOTE_TWEETS,
    CYCLE_MAX_REPLIES,
    CYCLE_MAX_RETWEETS,
    MAX_CAMPAIGN_TARGETS,
    MAX_TOTAL_WRITES_PER_DAY,
    EngagementScheduler,
)

from .base_agent import BaseAgent
from .memory import AgentMemory

logger = logging.getLogger("purecortex.agents.social")


# Content type labels used for strategy selection and memory tagging
CONTENT_TYPES = [
    "protocol_update",
    "tokenomics_education",
    "governance_highlight",
    "agent_ecosystem",
    "community_engagement",
    "metrics_report",
    "thread",
]

OFFICIAL_TOKEN_TICKER = f"${CORTEX_UNIT_NAME}"
FORBIDDEN_TOKEN_PATTERNS = (
    re.compile(r"\$PRCX\b", re.IGNORECASE),
    re.compile(r"\bPRCX\b", re.IGNORECASE),
)
CAMPAIGN_TARGETS_KEY = "campaign_targets"
CAMPAIGN_HISTORY_KEY = "campaign_history"
CAMPAIGN_CANDIDATES_KEY = "campaign_candidates"
CAMPAIGN_LIMITS_KEY = "campaign_daily_limits"
MAX_FOLLOWS_PER_DAY = 5
MAX_REPLIES_PER_DAY = 8
AUTO_CAMPAIGN_MAX_TARGETS = int(os.getenv("SOCIAL_CAMPAIGN_MAX_TARGETS", "8"))
AUTO_CAMPAIGN_TWEETS_PER_TARGET = int(os.getenv("SOCIAL_CAMPAIGN_TWEETS_PER_TARGET", "5"))
AUTO_CAMPAIGN_MAX_CANDIDATES = int(os.getenv("SOCIAL_CAMPAIGN_MAX_CANDIDATES", "8"))
AUTO_REPLY_SCORE_THRESHOLD = int(os.getenv("SOCIAL_CAMPAIGN_REPLY_SCORE_THRESHOLD", "6"))
AUTO_FOLLOW_PRIORITY_THRESHOLD = int(os.getenv("SOCIAL_CAMPAIGN_FOLLOW_PRIORITY_THRESHOLD", "9"))

# Community engagement limits
MAX_RETWEETS_PER_DAY = int(os.getenv("SOCIAL_MAX_RETWEETS_PER_DAY", "5"))
MAX_LIKES_PER_DAY = int(os.getenv("SOCIAL_MAX_LIKES_PER_DAY", "10"))
MAX_QUOTE_TWEETS_PER_DAY = int(os.getenv("SOCIAL_MAX_QUOTE_TWEETS_PER_DAY", "3"))
MAX_MENTION_REPLIES_PER_DAY = int(os.getenv("SOCIAL_MAX_MENTION_REPLIES_PER_DAY", "5"))

# Score thresholds for engagement decisions
AUTO_RETWEET_SCORE_THRESHOLD = int(os.getenv("SOCIAL_RETWEET_SCORE_THRESHOLD", "7"))
AUTO_LIKE_SCORE_THRESHOLD = int(os.getenv("SOCIAL_LIKE_SCORE_THRESHOLD", "5"))
AUTO_QUOTE_TWEET_SCORE_THRESHOLD = int(os.getenv("SOCIAL_QUOTE_TWEET_SCORE_THRESHOLD", "8"))

# Memory keys for engagement tracking
ENGAGEMENT_HISTORY_KEY = "engagement_history"
MENTION_CHECKPOINT_KEY = "mention_last_seen_id"
COMMUNITY_CANDIDATES_KEY = "community_candidates"
CONVERSATION_CHECKPOINTS_KEY = "conversation_checkpoints"
THREAD_PARTICIPATION_KEY = "thread_participation"
HOME_TIMELINE_CANDIDATES_KEY = "home_timeline_candidates"


class SocialAgent(BaseAgent):
    """Social Media Intelligence for PURECORTEX (@purecortexai on X)."""

    SYSTEM_PROMPT = (
        "You are the Social Media Intelligence of PURECORTEX (@purecortexai on X).\n"
        "Your role is to build awareness, educate, and engage the community about PURECORTEX.\n\n"
        "Brand voice: Authoritative but accessible. Technical but not jargon-heavy.\n"
        "Focus on: sovereignty, AI agents, Algorand, tokenomics (buyback-burn), governance.\n"
        f"Protocol facts: the official token is {CORTEX_NAME} with ticker {OFFICIAL_TOKEN_TICKER} "
        f"on Algorand (asset id {CORTEX_ASSET_ID}). Never refer to the token as PRCX or any other ticker.\n"
        "Never: make price predictions, financial advice, misleading claims, or hype.\n\n"
        "Keep tweets concise, impactful, and informative. Use threads for complex topics.\n"
        "Reference on-chain data when possible for credibility.\n\n"
        "Respond ONLY in valid JSON with fields:\n"
        "  'action': 'POST',\n"
        "  'content_type': one of 'protocol_update' | 'tokenomics_education' | "
        "'governance_highlight' | 'agent_ecosystem' | 'community_engagement' | "
        "'metrics_report' | 'thread',\n"
        "  'message': <the tweet text, max 280 chars>,\n"
        "  'thread': [<array of tweet texts>] or null (only if content_type is 'thread'),\n"
        "  'rationale': <why this content was chosen>"
    )

    CHAT_PROMPT = (
        "You are the Social Media agent of PURECORTEX. You manage the @purecortexai X account.\n"
        f"The official protocol token ticker is {OFFICIAL_TOKEN_TICKER}. Never describe it as PRCX.\n"
        "You can discuss: content strategy, recent posts, engagement metrics, and upcoming campaigns.\n"
        "Respond conversationally."
    )

    def __init__(
        self,
        orchestrator: ConsensusOrchestrator,
        memory: AgentMemory,
        algorand_address: str = "SOCIAL_ALGO_ADDRESS_TBD",
    ):
        super().__init__(
            name="Social",
            role="Social media content generation and community engagement",
            orchestrator=orchestrator,
            memory=memory,
            algorand_address=algorand_address,
            permission_tier=PermissionTier.SOCIAL_POST,
        )

        # Initialize Twitter/X client from environment variables
        self.twitter_client = self._init_twitter()
        self._own_user_id: int | None = None
        self._engagement_scheduler = EngagementScheduler()

    @staticmethod
    def _env_enabled(name: str, default: str = "1") -> bool:
        return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}

    async def _ensure_campaign_targets(self) -> list[dict[str, Any]]:
        targets = await self.memory.recall_long(CAMPAIGN_TARGETS_KEY)
        if targets:
            return targets

        targets = get_seed_targets()
        await self.memory.remember_long(CAMPAIGN_TARGETS_KEY, targets)
        return targets

    async def _load_campaign_history(self) -> dict[str, Any]:
        history = await self.memory.recall_long(CAMPAIGN_HISTORY_KEY)
        if history:
            return history

        history = {
            "replied_tweet_ids": [],
            "followed_handles": [],
            "reply_events": [],
            "follow_events": [],
        }
        await self.memory.remember_long(CAMPAIGN_HISTORY_KEY, history)
        return history

    async def _save_campaign_history(self, history: dict[str, Any]) -> None:
        history["replied_tweet_ids"] = history.get("replied_tweet_ids", [])[-500:]
        history["followed_handles"] = history.get("followed_handles", [])[-200:]
        history["reply_events"] = history.get("reply_events", [])[-100:]
        history["follow_events"] = history.get("follow_events", [])[-100:]
        await self.memory.remember_long(CAMPAIGN_HISTORY_KEY, history)

    async def _load_daily_limits(self) -> dict[str, Any]:
        limits = await self.memory.recall_long(CAMPAIGN_LIMITS_KEY)
        today = time.strftime("%Y-%m-%d", time.gmtime())
        if not limits or limits.get("date") != today:
            limits = {
                "date": today,
                "follow_count": 0,
                "reply_count": 0,
                "retweet_count": 0,
                "like_count": 0,
                "quote_tweet_count": 0,
                "mention_reply_count": 0,
                "total_write_count": 0,
            }
            await self.memory.remember_long(CAMPAIGN_LIMITS_KEY, limits)
        # Backfill total_write_count for existing limits dicts
        if "total_write_count" not in limits:
            limits["total_write_count"] = 0
        return limits

    async def _check_write_budget(self) -> bool:
        """Return True if there is remaining daily write budget."""
        limits = await self._load_daily_limits()
        return int(limits.get("total_write_count", 0)) < MAX_TOTAL_WRITES_PER_DAY

    async def _increment_write_count(self) -> None:
        """Increment the aggregate daily write counter."""
        await self._increment_daily_limit("total_write_count")

    async def _increment_daily_limit(self, key: str) -> dict[str, Any]:
        limits = await self._load_daily_limits()
        limits[key] = int(limits.get(key, 0)) + 1
        await self.memory.remember_long(CAMPAIGN_LIMITS_KEY, limits)
        return limits

    async def _record_reply_event(
        self,
        *,
        tweet_id: int,
        target_handle: str | None,
        text: str,
        response_tweet_id: int | None = None,
    ) -> None:
        history = await self._load_campaign_history()
        history.setdefault("replied_tweet_ids", []).append(str(tweet_id))
        history.setdefault("reply_events", []).append(
            {
                "tweet_id": str(tweet_id),
                "target_handle": target_handle,
                "text": text[:280],
                "response_tweet_id": str(response_tweet_id) if response_tweet_id else None,
                "timestamp": time.time(),
            }
        )
        await self._save_campaign_history(history)

        if target_handle:
            await self._update_target(handle=target_handle, last_interaction_at=time.time(), relationship_stage="engaged")

    async def _record_follow_event(self, *, handle: str, target_user_id: int) -> None:
        history = await self._load_campaign_history()
        history.setdefault("followed_handles", []).append(handle.lower())
        history.setdefault("follow_events", []).append(
            {
                "handle": handle,
                "target_user_id": str(target_user_id),
                "timestamp": time.time(),
            }
        )
        await self._save_campaign_history(history)
        await self._update_target(handle=handle, last_followed_at=time.time(), relationship_stage="followed")

    async def _update_target(self, *, handle: str, **updates: Any) -> None:
        targets = await self._ensure_campaign_targets()
        updated = False
        for target in targets:
            if target.get("handle", "").lower() == handle.lower():
                target.update(updates)
                updated = True
                break
        if updated:
            await self.memory.remember_long(CAMPAIGN_TARGETS_KEY, targets)

    # ------------------------------------------------------------------
    # Engagement tracking
    # ------------------------------------------------------------------

    async def _get_own_user_id(self) -> int:
        """Get and cache the authenticated Twitter user ID."""
        if self._own_user_id is None:
            if not self.twitter_client:
                raise RuntimeError("Twitter client is unavailable")
            response = self.twitter_client.get_me(user_auth=True)
            if response and response.data:
                self._own_user_id = response.data.id
            else:
                raise RuntimeError("Unable to resolve authenticated user")
        return self._own_user_id

    async def _load_engagement_history(self) -> dict[str, Any]:
        history = await self.memory.recall_long(ENGAGEMENT_HISTORY_KEY)
        if history:
            return history
        history = {
            "retweeted_ids": [],
            "liked_ids": [],
            "quoted_ids": [],
            "mention_replied_ids": [],
            "events": [],
        }
        await self.memory.remember_long(ENGAGEMENT_HISTORY_KEY, history)
        return history

    async def _record_engagement_event(
        self,
        *,
        action_type: str,
        tweet_id: int,
        author_handle: str | None = None,
        text: str = "",
        response_tweet_id: int | None = None,
    ) -> None:
        history = await self._load_engagement_history()

        id_str = str(tweet_id)
        list_key = {
            "retweet": "retweeted_ids",
            "like": "liked_ids",
            "quote_tweet": "quoted_ids",
            "mention_reply": "mention_replied_ids",
        }.get(action_type, "liked_ids")
        history.setdefault(list_key, []).append(id_str)

        history.setdefault("events", []).append({
            "action": action_type,
            "tweet_id": id_str,
            "author_handle": author_handle,
            "text": text[:280],
            "response_tweet_id": str(response_tweet_id) if response_tweet_id else None,
            "timestamp": time.time(),
        })

        # Trim to prevent unbounded growth
        for key in ("retweeted_ids", "liked_ids", "quoted_ids", "mention_replied_ids"):
            history[key] = history.get(key, [])[-500:]
        history["events"] = history.get("events", [])[-200:]

        await self.memory.remember_long(ENGAGEMENT_HISTORY_KEY, history)

    # ------------------------------------------------------------------
    # Core engagement methods
    # ------------------------------------------------------------------

    async def retweet(
        self,
        *,
        tweet_id: int,
        author_handle: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Retweet a tweet. User-facing action with daily limit and dedup."""
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        limits = await self._load_daily_limits()
        if limits.get("retweet_count", 0) >= MAX_RETWEETS_PER_DAY:
            raise RuntimeError("Daily retweet limit reached")

        history = await self._load_engagement_history()
        if str(tweet_id) in set(history.get("retweeted_ids", [])):
            raise RuntimeError(f"Tweet {tweet_id} already retweeted")

        if dry_run:
            return {"dry_run": True, "tweet_id": str(tweet_id), "author_handle": author_handle}

        self.twitter_client.retweet(tweet_id, user_auth=True)
        await self._increment_daily_limit("retweet_count")
        await self._record_engagement_event(
            action_type="retweet", tweet_id=tweet_id, author_handle=author_handle,
        )
        logger.info("[Social] Retweeted %s from @%s", tweet_id, author_handle or "unknown")
        return {"dry_run": False, "tweet_id": str(tweet_id), "author_handle": author_handle}

    async def like_tweet(
        self,
        *,
        tweet_id: int,
        author_handle: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Like a tweet. User-facing action with daily limit and dedup."""
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        limits = await self._load_daily_limits()
        if limits.get("like_count", 0) >= MAX_LIKES_PER_DAY:
            raise RuntimeError("Daily like limit reached")

        history = await self._load_engagement_history()
        if str(tweet_id) in set(history.get("liked_ids", [])):
            raise RuntimeError(f"Tweet {tweet_id} already liked")

        if dry_run:
            return {"dry_run": True, "tweet_id": str(tweet_id), "author_handle": author_handle}

        self.twitter_client.like(tweet_id, user_auth=True)
        await self._increment_daily_limit("like_count")
        await self._record_engagement_event(
            action_type="like", tweet_id=tweet_id, author_handle=author_handle,
        )
        logger.info("[Social] Liked %s from @%s", tweet_id, author_handle or "unknown")
        return {"dry_run": False, "tweet_id": str(tweet_id), "author_handle": author_handle}

    async def quote_tweet(
        self,
        *,
        tweet_id: int,
        text: str,
        author_handle: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Post a quote tweet with commentary. Daily limit and dedup."""
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        limits = await self._load_daily_limits()
        if limits.get("quote_tweet_count", 0) >= MAX_QUOTE_TWEETS_PER_DAY:
            raise RuntimeError("Daily quote tweet limit reached")

        history = await self._load_engagement_history()
        if str(tweet_id) in set(history.get("quoted_ids", [])):
            raise RuntimeError(f"Tweet {tweet_id} already quote-tweeted")

        normalized = self._normalize_token_terms(text.strip())
        if not normalized:
            raise RuntimeError("Quote tweet text cannot be empty")

        if dry_run:
            return {
                "dry_run": True,
                "tweet_id": str(tweet_id),
                "author_handle": author_handle,
                "text": normalized,
            }

        response = self.twitter_client.create_tweet(
            text=normalized, quote_tweet_id=tweet_id, user_auth=True,
        )
        response_tweet_id = response.data.get("id") if response and response.data else None
        await self._increment_daily_limit("quote_tweet_count")
        await self._record_engagement_event(
            action_type="quote_tweet",
            tweet_id=tweet_id,
            author_handle=author_handle,
            text=normalized,
            response_tweet_id=response_tweet_id,
        )
        logger.info("[Social] Quote-tweeted %s from @%s", tweet_id, author_handle or "unknown")
        return {
            "dry_run": False,
            "tweet_id": str(tweet_id),
            "author_handle": author_handle,
            "quote_tweet_id": str(response_tweet_id) if response_tweet_id else None,
            "text": normalized,
        }

    async def _draft_quote_comment(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Use tri-brain consensus to draft commentary for a quote tweet."""
        system_prompt = (
            "You are drafting a quote-tweet comment for @purecortexai.\n"
            "Add genuine value: a technical insight, ecosystem perspective, or thoughtful take.\n"
            f"Use {OFFICIAL_TOKEN_TICKER} if the protocol token is mentioned; never use PRCX.\n"
            "Do not be spammy, self-promotional, or make partnership claims.\n"
            "Keep commentary under 200 characters to leave room for the quoted tweet.\n\n"
            "Respond ONLY in valid JSON with fields:\n"
            "  'action': one of 'QUOTE_TWEET' | 'NONE',\n"
            "  'message': the commentary text or empty string,\n"
            "  'rationale': short explanation."
        )
        user_prompt = (
            f"AUTHOR: @{candidate.get('author_handle', 'unknown')}\n"
            f"SCORE: {candidate.get('score', 0)}\n"
            f"REASONS: {', '.join(candidate.get('reasons', []))}\n"
            f"TWEET TEXT:\n{candidate.get('text', '')}\n\n"
            "Draft commentary only if PURECORTEX can add a genuinely relevant perspective."
        )

        decision = await self.think(system_prompt, user_prompt, task_type="QUOTE_TWEET")
        if not decision:
            return {"action": "NONE", "message": "", "rationale": "Consensus unavailable"}

        action = decision.get("action", "NONE")
        message = self._normalize_token_terms(decision.get("message", ""))
        if action != "QUOTE_TWEET" or not message:
            return {
                "action": "NONE",
                "message": "",
                "rationale": decision.get("rationale", "No useful commentary drafted"),
            }

        return {
            "action": "QUOTE_TWEET",
            "message": message[:200],
            "rationale": decision.get("rationale", ""),
        }

    # ------------------------------------------------------------------
    # Community discovery
    # ------------------------------------------------------------------

    async def discover_community_content(
        self,
        *,
        max_results_per_query: int = 10,
        max_candidates: int = 15,
        use_rotation: bool = False,
    ) -> dict[str, Any]:
        """Search for Algorand community content to engage with."""
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        engagement_history = await self._load_engagement_history()
        seen_ids: set[str] = set()
        for key in ("retweeted_ids", "liked_ids", "quoted_ids", "mention_replied_ids"):
            seen_ids.update(engagement_history.get(key, []))

        # Also skip tweets we've already replied to via campaign
        campaign_history = await self._load_campaign_history()
        seen_ids.update(campaign_history.get("replied_tweet_ids", []))

        own_user_id = await self._get_own_user_id()
        candidates: list[dict[str, Any]] = []

        queries = get_search_queries_for_cycle() if use_rotation else get_search_queries()
        for query in queries:
            try:
                response = self.twitter_client.search_recent_tweets(
                    query=query,
                    max_results=max(10, min(100, max_results_per_query)),
                    tweet_fields=["created_at", "public_metrics", "author_id"],
                    expansions=["author_id"],
                    user_fields=["username", "name", "public_metrics"],
                    user_auth=True,
                )
            except Exception as exc:
                logger.warning("[Social] Search failed for query '%s': %s", query, exc)
                continue

            # Build user lookup from includes
            user_lookup: dict[int, dict[str, Any]] = {}
            if response and hasattr(response, "includes") and response.includes:
                for user in response.includes.get("users", []):
                    user_lookup[user.id] = {
                        "username": user.username,
                        "name": getattr(user, "name", user.username),
                    }

            for tweet in (response.data or []) if response else []:
                tweet_id = str(tweet.id)
                if tweet_id in seen_ids:
                    continue

                author_id = getattr(tweet, "author_id", None)
                if author_id == own_user_id:
                    continue

                author_info = user_lookup.get(author_id, {})
                author_handle = author_info.get("username", "")
                text = tweet.text or ""
                metrics = getattr(tweet, "public_metrics", None) or {}

                score, reasons, recommended_action = score_engagement_candidate(
                    text,
                    author_handle,
                    public_metrics=metrics,
                    created_at=getattr(tweet, "created_at", None),
                )

                if score < AUTO_LIKE_SCORE_THRESHOLD:
                    continue

                candidates.append({
                    "tweet_id": tweet_id,
                    "author_handle": author_handle,
                    "author_name": author_info.get("name", author_handle),
                    "text": text,
                    "score": score,
                    "reasons": reasons,
                    "recommended_action": recommended_action,
                    "public_metrics": metrics,
                    "created_at": str(getattr(tweet, "created_at", "")),
                    "source_query": query,
                })
                seen_ids.add(tweet_id)

        candidates.sort(key=lambda c: int(c.get("score", 0)), reverse=True)
        candidates = candidates[:max_candidates]

        # Draft quote comments for top candidates
        for candidate in candidates:
            if candidate.get("recommended_action") == "quote_tweet":
                candidate["draft"] = await self._draft_quote_comment(candidate)

        payload = {
            "scanned_at": time.time(),
            "queries_used": len(get_search_queries()),
            "candidates": candidates,
        }
        await self.memory.remember_short(COMMUNITY_CANDIDATES_KEY, payload)
        return payload

    async def check_mentions(self, *, max_results: int = 20) -> dict[str, Any]:
        """Check for new @purecortexai mentions and score them for reply."""
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        own_user_id = await self._get_own_user_id()

        last_seen_id = await self.memory.recall_long(MENTION_CHECKPOINT_KEY)
        kwargs: dict[str, Any] = {
            "max_results": max(5, min(100, max_results)),
            "tweet_fields": ["created_at", "public_metrics", "author_id", "conversation_id"],
            "expansions": ["author_id"],
            "user_fields": ["username", "name"],
            "user_auth": True,
        }
        if last_seen_id:
            kwargs["since_id"] = int(last_seen_id)

        try:
            response = self.twitter_client.get_users_mentions(own_user_id, **kwargs)
        except Exception as exc:
            logger.warning("[Social] Mention check failed: %s", exc)
            return {"candidates": [], "error": str(exc)}

        user_lookup: dict[int, dict[str, Any]] = {}
        if response and hasattr(response, "includes") and response.includes:
            for user in response.includes.get("users", []):
                user_lookup[user.id] = {
                    "username": user.username,
                    "name": getattr(user, "name", user.username),
                }

        engagement_history = await self._load_engagement_history()
        replied_mention_ids = set(engagement_history.get("mention_replied_ids", []))

        candidates: list[dict[str, Any]] = []
        max_seen_id = int(last_seen_id) if last_seen_id else 0

        synthetic_target = {
            "category": "community",
            "priority": 7,
            "engage_topics": ["algorand", "ecosystem", "ai", "governance", "defi"],
        }

        for tweet in (response.data or []) if response else []:
            tweet_id = str(tweet.id)
            if tweet_id in replied_mention_ids:
                continue

            author_id = getattr(tweet, "author_id", None)
            if author_id == own_user_id:
                if tweet.id > max_seen_id:
                    max_seen_id = tweet.id
                continue

            author_info = user_lookup.get(author_id, {})
            text = tweet.text or ""

            score, reasons = score_target_tweet(text, synthetic_target, getattr(tweet, "created_at", None))

            candidate = {
                "tweet_id": tweet_id,
                "author_handle": author_info.get("username", ""),
                "author_name": author_info.get("name", ""),
                "text": text,
                "score": score,
                "reasons": reasons,
                "target_handle": author_info.get("username", ""),
                "target_category": "community",
                "created_at": str(getattr(tweet, "created_at", "")),
            }

            if score >= AUTO_REPLY_SCORE_THRESHOLD:
                candidate["draft"] = await self._draft_reply(candidate)

            candidates.append(candidate)
            if tweet.id > max_seen_id:
                max_seen_id = tweet.id

        if max_seen_id and max_seen_id > (int(last_seen_id) if last_seen_id else 0):
            await self.memory.remember_long(MENTION_CHECKPOINT_KEY, str(max_seen_id))

        candidates.sort(key=lambda c: int(c.get("score", 0)), reverse=True)
        return {"candidates": candidates}

    async def get_campaign_targets(self) -> list[dict[str, Any]]:
        return await self._ensure_campaign_targets()

    async def get_campaign_status(self) -> dict[str, Any]:
        targets = await self._ensure_campaign_targets()
        history = await self._load_campaign_history()
        limits = await self._load_daily_limits()
        engagement = await self._load_engagement_history()
        recent_posts = await self.memory.get_recent_episodes(limit=10)

        return {
            "account": "@purecortexai",
            "official_token_ticker": OFFICIAL_TOKEN_TICKER,
            "twitter_ready": self.twitter_client is not None,
            "target_count": len(targets),
            "high_priority_targets": [t["handle"] for t in sorted(targets, key=lambda item: item.get("priority", 0), reverse=True)[:5]],
            "daily_limits": {
                "date": limits["date"],
                "follow_count": limits.get("follow_count", 0),
                "reply_count": limits.get("reply_count", 0),
                "retweet_count": limits.get("retweet_count", 0),
                "like_count": limits.get("like_count", 0),
                "quote_tweet_count": limits.get("quote_tweet_count", 0),
                "mention_reply_count": limits.get("mention_reply_count", 0),
                "max_follows_per_day": MAX_FOLLOWS_PER_DAY,
                "max_replies_per_day": MAX_REPLIES_PER_DAY,
                "max_retweets_per_day": MAX_RETWEETS_PER_DAY,
                "max_likes_per_day": MAX_LIKES_PER_DAY,
                "max_quote_tweets_per_day": MAX_QUOTE_TWEETS_PER_DAY,
                "max_mention_replies_per_day": MAX_MENTION_REPLIES_PER_DAY,
            },
            "engagement_features": {
                "retweet": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_RETWEET", "1"),
                "like": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_LIKE", "1"),
                "quote_tweet": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_QUOTE_TWEET", "1"),
                "mention_reply": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_MENTION_REPLY", "1"),
                "search_discovery": self._env_enabled("SOCIAL_CAMPAIGN_SEARCH_DISCOVERY", "1"),
            },
            "recent_reply_events": history.get("reply_events", [])[-5:],
            "recent_follow_events": history.get("follow_events", [])[-5:],
            "recent_engagement_events": engagement.get("events", [])[-5:],
            "recent_social_cycles": recent_posts[:5],
        }

    async def _draft_reply(self, candidate: dict[str, Any]) -> dict[str, Any]:
        system_prompt = (
            "You are drafting a reply for @purecortexai to an Algorand ecosystem post.\n"
            "Reply only when PURECORTEX can add real value.\n"
            f"Use {OFFICIAL_TOKEN_TICKER} if the protocol token is mentioned; never use PRCX.\n"
            "Do not sound spammy. Do not over-tag people. Do not make partnership claims or price claims.\n"
            "Prefer concise, technical, high-signal replies.\n\n"
            "Respond ONLY in valid JSON with fields:\n"
            "  'action': one of 'REPLY' | 'NONE',\n"
            "  'message': the reply text or empty string,\n"
            "  'rationale': short explanation of why this is worth posting."
        )
        user_prompt = (
            f"TARGET HANDLE: @{candidate['target_handle']}\n"
            f"TARGET CATEGORY: {candidate['target_category']}\n"
            f"CANDIDATE SCORE: {candidate['score']}\n"
            f"REASONS: {', '.join(candidate.get('reasons', []))}\n"
            f"POST TEXT:\n{candidate['text']}\n\n"
            "Draft a reply only if PURECORTEX has a genuinely relevant contribution."
        )

        decision = await self.think(system_prompt, user_prompt, task_type="REPLY")
        if not decision:
            return {"action": "NONE", "message": "", "rationale": "Consensus unavailable"}

        action = decision.get("action", "NONE")
        message = self._normalize_token_terms(decision.get("message", ""))
        if action != "REPLY" or not message:
            return {
                "action": "NONE",
                "message": "",
                "rationale": decision.get("rationale", "No useful reply drafted"),
            }

        return {
            "action": "REPLY",
            "message": message[:280],
            "rationale": decision.get("rationale", ""),
        }

    async def discover_campaign_candidates(
        self,
        *,
        max_targets: int = 8,
        tweets_per_target: int = 5,
        max_candidates: int = 8,
        include_reply_drafts: bool = True,
    ) -> dict[str, Any]:
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        targets = sorted(
            await self._ensure_campaign_targets(),
            key=lambda item: item.get("priority", 0),
            reverse=True,
        )
        history = await self._load_campaign_history()
        replied_ids = {tweet_id for tweet_id in history.get("replied_tweet_ids", [])}
        candidates: list[dict[str, Any]] = []
        scanned_targets: list[dict[str, Any]] = []

        for target in targets[:max_targets]:
            handle = target.get("handle")
            if not handle:
                continue

            try:
                user_response = self.twitter_client.get_user(
                    username=handle,
                    user_auth=True,
                    user_fields=["description", "public_metrics"],
                )
            except Exception as exc:
                scanned_targets.append({"handle": handle, "status": "resolve_failed", "detail": str(exc)})
                continue

            user = user_response.data if user_response else None
            if user is None:
                scanned_targets.append({"handle": handle, "status": "not_found"})
                continue

            scanned_targets.append({"handle": handle, "status": "resolved", "user_id": str(user.id)})

            try:
                tweet_response = self.twitter_client.get_users_tweets(
                    user.id,
                    max_results=max(5, min(100, tweets_per_target)),
                    tweet_fields=["created_at", "public_metrics"],
                    exclude=["replies", "retweets"],
                    user_auth=True,
                )
            except Exception as exc:
                scanned_targets.append({"handle": handle, "status": "timeline_failed", "detail": str(exc)})
                continue

            for tweet in tweet_response.data or []:
                tweet_id = str(tweet.id)
                if tweet_id in replied_ids:
                    continue

                text = tweet.text or ""
                score, reasons = score_target_tweet(
                    text,
                    target,
                    getattr(tweet, "created_at", None),
                )
                if score < 4:
                    continue

                metrics = getattr(tweet, "public_metrics", None) or {}
                candidate = {
                    "tweet_id": tweet_id,
                    "target_handle": handle,
                    "target_name": getattr(user, "name", handle),
                    "target_category": target.get("category"),
                    "score": score,
                    "reasons": reasons,
                    "created_at": str(getattr(tweet, "created_at", "")),
                    "text": text,
                    "public_metrics": metrics,
                }
                candidates.append(candidate)

        def sort_key(item: dict[str, Any]) -> tuple[int, int, int]:
            metrics = item.get("public_metrics") or {}
            return (
                int(item.get("score", 0)),
                int(metrics.get("like_count", 0)),
                int(metrics.get("retweet_count", 0)),
            )

        candidates.sort(key=sort_key, reverse=True)
        candidates = candidates[:max_candidates]

        if include_reply_drafts:
            for candidate in candidates:
                candidate["draft"] = await self._draft_reply(candidate)

        recommended_follows = [
            {
                "handle": target["handle"],
                "priority": target.get("priority", 0),
                "category": target.get("category"),
                "rationale": target.get("rationale"),
            }
            for target in targets
            if not target.get("last_followed_at")
        ][:5]

        payload = {
            "scanned_at": time.time(),
            "scanned_targets": scanned_targets,
            "candidates": candidates,
            "recommended_follows": recommended_follows,
        }
        await self.memory.remember_short(CAMPAIGN_CANDIDATES_KEY, payload)
        return payload

    async def _autonomous_campaign_cycle(self) -> dict[str, Any]:
        if not self.twitter_client:
            return {"enabled": False, "reason": "twitter_client_unavailable"}

        if not self._env_enabled("SOCIAL_CAMPAIGN_ENABLED", "1"):
            return {"enabled": False, "reason": "campaign_disabled"}

        limits = await self._load_daily_limits()
        payload = await self.discover_campaign_candidates(
            max_targets=AUTO_CAMPAIGN_MAX_TARGETS,
            tweets_per_target=AUTO_CAMPAIGN_TWEETS_PER_TARGET,
            max_candidates=AUTO_CAMPAIGN_MAX_CANDIDATES,
            include_reply_drafts=True,
        )

        result: dict[str, Any] = {
            "enabled": True,
            "candidates_scanned": len(payload.get("candidates", [])),
            "reply_action": None,
            "follow_action": None,
            "daily_limits": limits,
        }

        if self._env_enabled("SOCIAL_CAMPAIGN_AUTO_FOLLOW", "1") and limits.get("follow_count", 0) < MAX_FOLLOWS_PER_DAY:
            history = await self._load_campaign_history()
            followed = {handle.lower() for handle in history.get("followed_handles", [])}
            for candidate in payload.get("recommended_follows", []):
                handle = candidate.get("handle")
                if not handle or handle.lower() in followed:
                    continue
                if int(candidate.get("priority", 0)) < AUTO_FOLLOW_PRIORITY_THRESHOLD:
                    continue
                try:
                    follow_result = await self.follow_account(handle=handle, dry_run=False)
                    result["follow_action"] = follow_result
                except RuntimeError as exc:
                    result["follow_action"] = {"handle": handle, "error": str(exc)}
                break

        limits = await self._load_daily_limits()
        if self._env_enabled("SOCIAL_CAMPAIGN_AUTO_REPLY", "1") and limits.get("reply_count", 0) < MAX_REPLIES_PER_DAY:
            for candidate in payload.get("candidates", []):
                draft = candidate.get("draft") or {}
                if draft.get("action") != "REPLY":
                    continue
                if int(candidate.get("score", 0)) < AUTO_REPLY_SCORE_THRESHOLD:
                    continue
                try:
                    reply_result = await self.reply_to_tweet(
                        tweet_id=int(candidate["tweet_id"]),
                        text=draft["message"],
                        target_handle=candidate.get("target_handle"),
                        dry_run=False,
                    )
                    result["reply_action"] = reply_result
                except RuntimeError as exc:
                    result["reply_action"] = {
                        "tweet_id": candidate.get("tweet_id"),
                        "target_handle": candidate.get("target_handle"),
                        "error": str(exc),
                    }
                break

        # ---- Community engagement: search discovery ----
        community_payload: dict[str, Any] = {"candidates": []}
        if self._env_enabled("SOCIAL_CAMPAIGN_SEARCH_DISCOVERY", "1"):
            try:
                community_payload = await self.discover_community_content(
                    max_results_per_query=int(os.getenv("SOCIAL_SEARCH_MAX_RESULTS", "10")),
                )
                result["community_candidates_scanned"] = len(community_payload.get("candidates", []))
            except Exception as exc:
                logger.error("[Social] Community discovery failed: %s", exc)
                result["community_discovery_error"] = str(exc)

        # ---- Auto quote tweet (1 per cycle) ----
        limits = await self._load_daily_limits()
        if (
            self._env_enabled("SOCIAL_CAMPAIGN_AUTO_QUOTE_TWEET", "1")
            and limits.get("quote_tweet_count", 0) < MAX_QUOTE_TWEETS_PER_DAY
        ):
            for candidate in community_payload.get("candidates", []):
                if candidate.get("recommended_action") != "quote_tweet":
                    continue
                draft = candidate.get("draft") or {}
                if draft.get("action") != "QUOTE_TWEET":
                    continue
                if int(candidate.get("score", 0)) < AUTO_QUOTE_TWEET_SCORE_THRESHOLD:
                    continue
                try:
                    qt_result = await self.quote_tweet(
                        tweet_id=int(candidate["tweet_id"]),
                        text=draft["message"],
                        author_handle=candidate.get("author_handle"),
                        dry_run=False,
                    )
                    result["quote_tweet_action"] = qt_result
                except RuntimeError as exc:
                    result["quote_tweet_action"] = {"error": str(exc)}
                break

        # ---- Auto retweet (1 per cycle) ----
        limits = await self._load_daily_limits()
        if (
            self._env_enabled("SOCIAL_CAMPAIGN_AUTO_RETWEET", "1")
            and limits.get("retweet_count", 0) < MAX_RETWEETS_PER_DAY
        ):
            for candidate in community_payload.get("candidates", []):
                if candidate.get("recommended_action") != "retweet":
                    continue
                if int(candidate.get("score", 0)) < AUTO_RETWEET_SCORE_THRESHOLD:
                    continue
                try:
                    rt_result = await self.retweet(
                        tweet_id=int(candidate["tweet_id"]),
                        author_handle=candidate.get("author_handle"),
                        dry_run=False,
                    )
                    result["retweet_action"] = rt_result
                except RuntimeError as exc:
                    result["retweet_action"] = {"error": str(exc)}
                break

        # ---- Auto like (up to 3 per cycle) ----
        limits = await self._load_daily_limits()
        if (
            self._env_enabled("SOCIAL_CAMPAIGN_AUTO_LIKE", "1")
            and limits.get("like_count", 0) < MAX_LIKES_PER_DAY
        ):
            liked_this_cycle = 0
            for candidate in community_payload.get("candidates", []):
                if int(candidate.get("score", 0)) < AUTO_LIKE_SCORE_THRESHOLD:
                    continue
                try:
                    like_result = await self.like_tweet(
                        tweet_id=int(candidate["tweet_id"]),
                        author_handle=candidate.get("author_handle"),
                        dry_run=False,
                    )
                    result.setdefault("like_actions", []).append(like_result)
                    liked_this_cycle += 1
                    if liked_this_cycle >= 3:
                        break
                except RuntimeError:
                    break

        # ---- Mention monitoring and reply ----
        if self._env_enabled("SOCIAL_CAMPAIGN_AUTO_MENTION_REPLY", "1"):
            limits = await self._load_daily_limits()
            if limits.get("mention_reply_count", 0) < MAX_MENTION_REPLIES_PER_DAY:
                try:
                    mentions = await self.check_mentions()
                    result["mentions_checked"] = len(mentions.get("candidates", []))
                    for mention in mentions.get("candidates", []):
                        draft = mention.get("draft") or {}
                        if draft.get("action") != "REPLY":
                            continue
                        try:
                            mr_result = await self.reply_to_tweet(
                                tweet_id=int(mention["tweet_id"]),
                                text=draft["message"],
                                target_handle=mention.get("author_handle"),
                                dry_run=False,
                            )
                            await self._increment_daily_limit("mention_reply_count")
                            await self._record_engagement_event(
                                action_type="mention_reply",
                                tweet_id=int(mention["tweet_id"]),
                                author_handle=mention.get("author_handle"),
                                text=draft["message"],
                            )
                            result["mention_reply_action"] = mr_result
                        except RuntimeError as exc:
                            result["mention_reply_action"] = {"error": str(exc)}
                        break
                except Exception as exc:
                    result["mention_monitoring_error"] = str(exc)

        # ---- Log cycle with all engagement results ----
        actions_taken = sum(1 for key in (
            "reply_action", "follow_action", "retweet_action",
            "quote_tweet_action", "mention_reply_action",
        ) if result.get(key) and not (isinstance(result[key], dict) and result[key].get("error")))
        actions_taken += len([a for a in result.get("like_actions", []) if not a.get("error")])

        await self.memory.log_episode(
            action="CAMPAIGN",
            context={
                "auto_follow_enabled": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_FOLLOW", "1"),
                "auto_reply_enabled": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_REPLY", "1"),
                "auto_retweet_enabled": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_RETWEET", "1"),
                "auto_like_enabled": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_LIKE", "1"),
                "auto_quote_tweet_enabled": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_QUOTE_TWEET", "1"),
                "mention_reply_enabled": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_MENTION_REPLY", "1"),
                "search_discovery_enabled": self._env_enabled("SOCIAL_CAMPAIGN_SEARCH_DISCOVERY", "1"),
                "candidates_scanned": result["candidates_scanned"],
                "community_candidates_scanned": result.get("community_candidates_scanned", 0),
            },
            outcome=result,
            score=1.0 if actions_taken >= 3 else (0.7 if actions_taken >= 1 else 0.2),
        )

        return result

    async def follow_account(self, handle: str, *, dry_run: bool = False) -> dict[str, Any]:
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        limits = await self._load_daily_limits()
        if limits.get("follow_count", 0) >= MAX_FOLLOWS_PER_DAY:
            raise RuntimeError("Daily follow limit reached")

        history = await self._load_campaign_history()
        if handle.lower() in {value.lower() for value in history.get("followed_handles", [])}:
            raise RuntimeError(f"@{handle} has already been followed by this campaign")

        response = self.twitter_client.get_user(username=handle, user_auth=True)
        user = response.data if response else None
        if user is None:
            raise RuntimeError(f"Unable to resolve @{handle}")

        if dry_run:
            return {
                "dry_run": True,
                "handle": handle,
                "target_user_id": str(user.id),
            }

        follow_response = self.twitter_client.follow_user(user.id, user_auth=True)
        await self._increment_daily_limit("follow_count")
        await self._record_follow_event(handle=handle, target_user_id=user.id)
        return {
            "dry_run": False,
            "handle": handle,
            "target_user_id": str(user.id),
            "response": getattr(follow_response, "data", None),
        }

    async def reply_to_tweet(
        self,
        *,
        tweet_id: int,
        text: str,
        target_handle: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        limits = await self._load_daily_limits()
        if limits.get("reply_count", 0) >= MAX_REPLIES_PER_DAY:
            raise RuntimeError("Daily reply limit reached")

        normalized = self._normalize_token_terms(text.strip())
        if not normalized:
            raise RuntimeError("Reply text cannot be empty")

        if dry_run:
            return {
                "dry_run": True,
                "tweet_id": str(tweet_id),
                "target_handle": target_handle,
                "text": normalized,
            }

        response = self.twitter_client.create_tweet(
            text=normalized,
            in_reply_to_tweet_id=tweet_id,
            user_auth=True,
        )
        response_tweet_id = response.data.get("id") if response and response.data else None
        await self._increment_daily_limit("reply_count")
        await self._record_reply_event(
            tweet_id=tweet_id,
            target_handle=target_handle,
            text=normalized,
            response_tweet_id=response_tweet_id,
        )
        return {
            "dry_run": False,
            "tweet_id": str(tweet_id),
            "target_handle": target_handle,
            "reply_tweet_id": str(response_tweet_id) if response_tweet_id else None,
            "text": normalized,
        }

    # ------------------------------------------------------------------
    # Twitter client setup
    # ------------------------------------------------------------------

    @staticmethod
    def _init_twitter() -> Optional[tweepy.Client]:
        """Initialize the tweepy v2 Client from environment variables.

        Required env vars:
          TWITTER_BEARER_TOKEN, TWITTER_API_KEY, TWITTER_API_SECRET,
          TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
        """
        bearer = os.getenv("TWITTER_BEARER_TOKEN")
        api_key = os.getenv("TWITTER_API_KEY")
        api_secret = os.getenv("TWITTER_API_SECRET")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_secret = os.getenv("TWITTER_ACCESS_SECRET")

        if all([bearer, api_key, api_secret, access_token, access_secret]):
            try:
                client = tweepy.Client(
                    bearer_token=bearer,
                    consumer_key=api_key,
                    consumer_secret=api_secret,
                    access_token=access_token,
                    access_token_secret=access_secret,
                )
                logger.info("[Social] Twitter client initialised.")
                return client
            except Exception as exc:
                logger.error("[Social] Twitter client init failed: %s", exc)
                return None

        logger.warning("[Social] Twitter credentials not fully configured — posting disabled.")
        return None

    # ------------------------------------------------------------------
    # Autonomous action
    # ------------------------------------------------------------------

    async def act(self) -> Optional[Dict[str, Any]]:
        """Generate and post social content.

        1. Gather protocol metrics and recent events
        2. Decide content type based on recent activity and past posting history
        3. Generate content via tri-brain
        4. Post to X via tweepy
        5. Log episode with engagement metrics
        """
        logger.info("[Social] Starting content generation cycle.")

        # 1. Gather context
        context = await self._gather_posting_context()

        # 2. Build prompt
        user_prompt = (
            "Generate a tweet for @purecortexai based on the following context.\n\n"
            f"CONTEXT:\n{json.dumps(context, indent=2)}\n\n"
            "Choose the most appropriate content type and craft an engaging tweet. "
            "If the topic warrants it, create a thread instead."
        )

        # 3. Tri-brain decision
        decision = await self.think(
            self.SYSTEM_PROMPT,
            user_prompt,
            task_type="POST",
        )

        if not decision:
            logger.warning("[Social] No content generated this cycle.")
            return None

        content = decision.get("message", "")
        content_type = decision.get("content_type", "protocol_update")
        thread = decision.get("thread")

        content = self._normalize_token_terms(content)
        thread = [self._normalize_token_terms(tweet) for tweet in thread] if thread else thread

        if not content and not thread:
            logger.warning("[Social] Empty content — skipping post.")
            return None

        # 4. Post to X
        posted = False
        if content_type == "thread" and thread:
            posted = await self._post_thread(thread)
        elif content:
            posted = await self._post_tweet(content)

        if posted:
            await self._increment_write_count()

        # 5. Log outcome
        score = 1.0 if posted else 0.5  # 0.5 = generated but not posted (no client)
        await self.memory.log_episode(
            action="POST",
            context={"content_type": content_type, "content": content[:200]},
            outcome={
                "posted": posted,
                "content_type": content_type,
            },
            score=score,
        )

        # Track content type distribution in long-term memory
        await self._update_content_stats(content_type)

        # Track campaign post offsets for catch-up logic
        if posted:
            campaign_ctx = context.get("launch_campaign") or context.get("launch_campaign_catchup")
            if campaign_ctx:
                day_offset = campaign_ctx.get("priority_day_offset") or campaign_ctx.get("days_until_tge")
                if day_offset is not None:
                    posted_offsets_raw = await self.memory.recall_long("campaign_posted_offsets") or []
                    if isinstance(day_offset, int) and day_offset <= 0:
                        day_offset = -day_offset  # Convert to positive offset
                    if day_offset not in posted_offsets_raw:
                        posted_offsets_raw.append(day_offset)
                        await self.memory.remember_long("campaign_posted_offsets", posted_offsets_raw)
                        logger.info("[Social] Marked campaign Day %+d as posted.", day_offset)

        return decision

    # ------------------------------------------------------------------
    # Autonomous engagement (independent from posting)
    # ------------------------------------------------------------------

    async def engage(self) -> Optional[Dict[str, Any]]:
        """Autonomous community engagement cycle.

        Called by the engagement loop every ~45 minutes, independently from
        the content-posting loop.  Discovers community content, monitors
        mentions, browses the home timeline, follows up on conversations,
        and executes engagement actions (reply, retweet, like, quote, follow).
        """
        if not self.twitter_client:
            return {"enabled": False, "reason": "twitter_client_unavailable"}

        if not self._env_enabled("SOCIAL_ENGAGEMENT_ENABLED", "1"):
            return {"enabled": False, "reason": "engagement_disabled"}

        scheduler = self._engagement_scheduler
        cycle = scheduler.advance_cycle()
        logger.info("[Social] Engagement cycle %d starting.", cycle)

        all_candidates: list[dict[str, Any]] = []
        result: dict[str, Any] = {
            "enabled": True,
            "cycle": cycle,
            "actions_taken": 0,
        }

        # ---- 1. Mention monitoring (every cycle) ----
        if scheduler.should_run("mentions"):
            try:
                mentions = await self.check_mentions()
                mention_candidates = mentions.get("candidates", [])
                for mc in mention_candidates:
                    mc["_source"] = "mention"
                all_candidates.extend(mention_candidates)
                result["mentions_checked"] = len(mention_candidates)
            except Exception as exc:
                logger.error("[Social] Mention check failed in engage(): %s", exc)
                result["mentions_error"] = str(exc)

        # ---- 2. Search-based community discovery (every cycle, rotating queries) ----
        if scheduler.should_run("search"):
            try:
                community = await self.discover_community_content(
                    max_results_per_query=int(os.getenv("SOCIAL_SEARCH_MAX_RESULTS", "10")),
                    use_rotation=True,
                )
                community_candidates = community.get("candidates", [])
                for cc in community_candidates:
                    cc["_source"] = "search"
                all_candidates.extend(community_candidates)
                result["community_candidates"] = len(community_candidates)
            except Exception as exc:
                logger.error("[Social] Community discovery failed in engage(): %s", exc)
                result["community_error"] = str(exc)

        # ---- 3. Home timeline browsing (every 2nd cycle) ----
        if scheduler.should_run("home_timeline") and self._env_enabled("SOCIAL_HOME_TIMELINE_ENABLED", "1"):
            try:
                timeline = await self.browse_home_timeline()
                timeline_candidates = timeline.get("candidates", [])
                for tc in timeline_candidates:
                    tc["_source"] = "timeline"
                all_candidates.extend(timeline_candidates)
                result["timeline_candidates"] = len(timeline_candidates)
            except Exception as exc:
                logger.error("[Social] Home timeline browse failed: %s", exc)
                result["timeline_error"] = str(exc)

        # ---- 4. Conversation follow-up (every 3rd cycle) ----
        if scheduler.should_run("conversation_threads") and self._env_enabled("SOCIAL_CONVERSATION_FOLLOWUP_ENABLED", "1"):
            try:
                threads = await self.check_conversation_threads()
                thread_candidates = threads.get("candidates", [])
                for tc in thread_candidates:
                    tc["_source"] = "conversation"
                all_candidates.extend(thread_candidates)
                result["conversation_candidates"] = len(thread_candidates)
            except Exception as exc:
                logger.error("[Social] Conversation follow-up failed: %s", exc)
                result["conversation_error"] = str(exc)

        # ---- 5. Campaign target scanning (every 4th cycle) ----
        if scheduler.should_run("campaign_targets"):
            try:
                payload = await self.discover_campaign_candidates(
                    max_targets=AUTO_CAMPAIGN_MAX_TARGETS,
                    tweets_per_target=AUTO_CAMPAIGN_TWEETS_PER_TARGET,
                    max_candidates=AUTO_CAMPAIGN_MAX_CANDIDATES,
                    include_reply_drafts=True,
                )
                target_candidates = payload.get("candidates", [])
                for tc in target_candidates:
                    tc["_source"] = "campaign_target"
                all_candidates.extend(target_candidates)
                result["target_candidates"] = len(target_candidates)

                # Auto-follow from recommended_follows
                if self._env_enabled("SOCIAL_CAMPAIGN_AUTO_FOLLOW", "1"):
                    await self._execute_follows(payload.get("recommended_follows", []), result)
            except Exception as exc:
                logger.error("[Social] Campaign target scan failed: %s", exc)
                result["target_error"] = str(exc)

        # ---- 6. Dynamic target discovery (every 8th cycle) ----
        if scheduler.should_run("dynamic_discovery") and self._env_enabled("SOCIAL_CAMPAIGN_DYNAMIC_DISCOVERY", "1"):
            try:
                new_targets = await self.discover_new_targets(all_candidates)
                result["new_targets_added"] = len(new_targets)
            except Exception as exc:
                logger.error("[Social] Dynamic discovery failed: %s", exc)
                result["discovery_error"] = str(exc)

        # ---- 7. Execute engagement actions from merged candidates ----
        # De-duplicate by tweet_id and sort by score descending
        seen_ids: set[str] = set()
        unique_candidates: list[dict[str, Any]] = []
        for c in all_candidates:
            tid = c.get("tweet_id")
            if tid and tid not in seen_ids:
                seen_ids.add(tid)
                unique_candidates.append(c)
        unique_candidates.sort(key=lambda c: int(c.get("score", 0)), reverse=True)

        actions = await self._execute_engagement_actions(unique_candidates, result)
        result["actions_taken"] = actions

        # ---- 8. Log engagement episode ----
        await self.memory.log_episode(
            action="ENGAGE",
            context={
                "cycle": cycle,
                "candidates_total": len(unique_candidates),
                "operations": {
                    "mentions": scheduler.should_run("mentions"),
                    "search": scheduler.should_run("search"),
                    "home_timeline": scheduler.should_run("home_timeline"),
                    "conversation_threads": scheduler.should_run("conversation_threads"),
                    "campaign_targets": scheduler.should_run("campaign_targets"),
                    "dynamic_discovery": scheduler.should_run("dynamic_discovery"),
                },
            },
            outcome=result,
            score=1.0 if actions >= 3 else (0.7 if actions >= 1 else 0.2),
        )

        return result

    async def _execute_follows(
        self,
        recommended_follows: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> None:
        """Execute auto-follow actions from recommended follows list."""
        limits = await self._load_daily_limits()
        if limits.get("follow_count", 0) >= MAX_FOLLOWS_PER_DAY:
            return

        history = await self._load_campaign_history()
        followed = {handle.lower() for handle in history.get("followed_handles", [])}
        follows_this_cycle = 0

        for candidate in recommended_follows:
            if follows_this_cycle >= CYCLE_MAX_FOLLOWS:
                break
            handle = candidate.get("handle")
            if not handle or handle.lower() in followed:
                continue
            if int(candidate.get("priority", 0)) < AUTO_FOLLOW_PRIORITY_THRESHOLD:
                continue
            try:
                follow_result = await self.follow_account(handle=handle, dry_run=False)
                result.setdefault("follow_actions", []).append(follow_result)
                follows_this_cycle += 1
            except RuntimeError as exc:
                result.setdefault("follow_actions", []).append({"handle": handle, "error": str(exc)})
            break  # One follow attempt per cycle to be conservative

    async def _execute_engagement_actions(
        self,
        candidates: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> int:
        """Execute engagement actions on a scored, de-duplicated candidate list.

        Uses per-cycle caps from EngagementScheduler and respects daily limits.
        Returns the total number of actions successfully taken.
        """
        caps = self._engagement_scheduler.get_cycle_caps()
        remaining = dict(caps)  # mutable copy
        actions_taken = 0

        for candidate in candidates:
            if all(v <= 0 for v in remaining.values()):
                break  # All caps exhausted

            score = int(candidate.get("score", 0))
            source = candidate.get("_source", "")
            tweet_id = candidate.get("tweet_id")
            if not tweet_id:
                continue

            # ---- Reply (from mentions or conversations) ----
            if source in ("mention", "conversation") and remaining.get("mention_replies", 0) > 0:
                draft = candidate.get("draft") or {}
                if draft.get("action") == "REPLY" and score >= AUTO_REPLY_SCORE_THRESHOLD:
                    if not await self._check_write_budget():
                        break
                    try:
                        reply_result = await self.reply_to_tweet(
                            tweet_id=int(tweet_id),
                            text=draft["message"],
                            target_handle=candidate.get("author_handle") or candidate.get("target_handle"),
                            dry_run=False,
                        )
                        await self._increment_write_count()
                        if source == "mention":
                            await self._increment_daily_limit("mention_reply_count")
                            await self._record_engagement_event(
                                action_type="mention_reply",
                                tweet_id=int(tweet_id),
                                author_handle=candidate.get("author_handle"),
                                text=draft["message"],
                                response_tweet_id=reply_result.get("response_tweet_id"),
                            )
                        result.setdefault("reply_actions", []).append(reply_result)
                        remaining["mention_replies"] -= 1
                        actions_taken += 1
                    except RuntimeError as exc:
                        result.setdefault("reply_actions", []).append({"error": str(exc)})
                    continue

            # ---- Reply (from campaign targets) ----
            if source == "campaign_target" and remaining.get("replies", 0) > 0:
                draft = candidate.get("draft") or {}
                if draft.get("action") == "REPLY" and score >= AUTO_REPLY_SCORE_THRESHOLD:
                    if not await self._check_write_budget():
                        break
                    try:
                        reply_result = await self.reply_to_tweet(
                            tweet_id=int(tweet_id),
                            text=draft["message"],
                            target_handle=candidate.get("target_handle"),
                            dry_run=False,
                        )
                        await self._increment_write_count()
                        result.setdefault("reply_actions", []).append(reply_result)
                        remaining["replies"] -= 1
                        actions_taken += 1
                    except RuntimeError as exc:
                        result.setdefault("reply_actions", []).append({"error": str(exc)})
                    continue

            # ---- Quote tweet ----
            recommended = candidate.get("recommended_action", "")
            if recommended == "quote_tweet" and remaining.get("quote_tweets", 0) > 0:
                draft = candidate.get("draft") or {}
                if draft.get("action") == "QUOTE_TWEET" and score >= AUTO_QUOTE_TWEET_SCORE_THRESHOLD:
                    if not await self._check_write_budget():
                        break
                    try:
                        qt_result = await self.quote_tweet(
                            tweet_id=int(tweet_id),
                            text=draft["message"],
                            author_handle=candidate.get("author_handle"),
                            dry_run=False,
                        )
                        await self._increment_write_count()
                        result.setdefault("quote_tweet_actions", []).append(qt_result)
                        remaining["quote_tweets"] -= 1
                        actions_taken += 1
                    except RuntimeError as exc:
                        result.setdefault("quote_tweet_actions", []).append({"error": str(exc)})
                    continue

            # ---- Retweet ----
            if recommended == "retweet" and remaining.get("retweets", 0) > 0:
                if score >= AUTO_RETWEET_SCORE_THRESHOLD:
                    try:
                        rt_result = await self.retweet(
                            tweet_id=int(tweet_id),
                            author_handle=candidate.get("author_handle"),
                            dry_run=False,
                        )
                        result.setdefault("retweet_actions", []).append(rt_result)
                        remaining["retweets"] -= 1
                        actions_taken += 1
                    except RuntimeError:
                        pass
                    continue

            # ---- Like (catch-all for anything scoring above threshold) ----
            if remaining.get("likes", 0) > 0 and score >= AUTO_LIKE_SCORE_THRESHOLD:
                try:
                    like_result = await self.like_tweet(
                        tweet_id=int(tweet_id),
                        author_handle=candidate.get("author_handle"),
                        dry_run=False,
                    )
                    result.setdefault("like_actions", []).append(like_result)
                    remaining["likes"] -= 1
                    actions_taken += 1
                except RuntimeError:
                    pass

        return actions_taken

    # ------------------------------------------------------------------
    # Home timeline browsing
    # ------------------------------------------------------------------

    async def browse_home_timeline(
        self,
        *,
        max_results: int = 50,
        max_candidates: int = 10,
    ) -> dict[str, Any]:
        """Scan the home timeline for organic engagement opportunities."""
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        engagement_history = await self._load_engagement_history()
        seen_ids: set[str] = set()
        for key in ("retweeted_ids", "liked_ids", "quoted_ids", "mention_replied_ids"):
            seen_ids.update(engagement_history.get(key, []))

        campaign_history = await self._load_campaign_history()
        seen_ids.update(campaign_history.get("replied_tweet_ids", []))

        own_user_id = await self._get_own_user_id()
        candidates: list[dict[str, Any]] = []

        try:
            response = self.twitter_client.get_home_timeline(
                max_results=max(10, min(100, max_results)),
                tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id"],
                expansions=["author_id"],
                user_fields=["username", "name", "public_metrics"],
                user_auth=True,
            )
        except Exception as exc:
            logger.warning("[Social] Home timeline fetch failed: %s", exc)
            return {"candidates": [], "error": str(exc)}

        user_lookup: dict[int, dict[str, Any]] = {}
        if response and hasattr(response, "includes") and response.includes:
            for user in response.includes.get("users", []):
                user_lookup[user.id] = {
                    "username": user.username,
                    "name": getattr(user, "name", user.username),
                }

        for tweet in (response.data or []) if response else []:
            tweet_id = str(tweet.id)
            if tweet_id in seen_ids:
                continue

            author_id = getattr(tweet, "author_id", None)
            if author_id == own_user_id:
                continue

            author_info = user_lookup.get(author_id, {})
            author_handle = author_info.get("username", "")
            text = tweet.text or ""
            metrics = getattr(tweet, "public_metrics", None) or {}

            score, reasons, recommended_action = score_engagement_candidate(
                text,
                author_handle,
                public_metrics=metrics,
                created_at=getattr(tweet, "created_at", None),
            )

            if score < AUTO_LIKE_SCORE_THRESHOLD:
                continue

            candidates.append({
                "tweet_id": tweet_id,
                "author_handle": author_handle,
                "author_name": author_info.get("name", author_handle),
                "text": text,
                "score": score,
                "reasons": reasons,
                "recommended_action": recommended_action,
                "public_metrics": metrics,
                "created_at": str(getattr(tweet, "created_at", "")),
                "conversation_id": str(getattr(tweet, "conversation_id", "")),
            })
            seen_ids.add(tweet_id)

        candidates.sort(key=lambda c: int(c.get("score", 0)), reverse=True)
        candidates = candidates[:max_candidates]

        # Draft quote comments for top candidates
        for candidate in candidates:
            if candidate.get("recommended_action") == "quote_tweet":
                candidate["draft"] = await self._draft_quote_comment(candidate)

        payload = {
            "scanned_at": time.time(),
            "candidates": candidates,
        }
        await self.memory.remember_short(HOME_TIMELINE_CANDIDATES_KEY, payload)
        return payload

    # ------------------------------------------------------------------
    # Conversation follow-up
    # ------------------------------------------------------------------

    async def check_conversation_threads(
        self,
        *,
        max_threads: int = 5,
        max_results_per_thread: int = 10,
    ) -> dict[str, Any]:
        """Check for new replies in conversations we've participated in."""
        if not self.twitter_client:
            raise RuntimeError("Twitter client is unavailable")

        # Collect recent response_tweet_ids from our engagement history
        engagement = await self._load_engagement_history()
        campaign = await self._load_campaign_history()

        our_tweets: list[dict[str, Any]] = []
        for event in reversed(engagement.get("events", [])):
            if event.get("response_tweet_id") and event.get("tweet_id"):
                our_tweets.append(event)
                if len(our_tweets) >= max_threads * 2:
                    break
        for event in reversed(campaign.get("reply_events", [])):
            if event.get("response_tweet_id") and event.get("tweet_id"):
                our_tweets.append(event)
                if len(our_tweets) >= max_threads * 2:
                    break

        if not our_tweets:
            return {"candidates": []}

        # Load conversation checkpoints
        checkpoints = await self.memory.recall_long(CONVERSATION_CHECKPOINTS_KEY) or {}
        own_user_id = await self._get_own_user_id()

        candidates: list[dict[str, Any]] = []
        threads_checked = 0
        updated_checkpoints: dict[str, str] = dict(checkpoints)

        for event in our_tweets[:max_threads]:
            response_id = str(event["response_tweet_id"])

            try:
                # Search for replies to our tweet
                query = f"conversation_id:{response_id} -from:{own_user_id}"
                since_id = checkpoints.get(response_id)
                kwargs: dict[str, Any] = {
                    "query": query,
                    "max_results": max(10, min(100, max_results_per_thread)),
                    "tweet_fields": ["created_at", "public_metrics", "author_id"],
                    "expansions": ["author_id"],
                    "user_fields": ["username", "name"],
                    "user_auth": True,
                }
                if since_id:
                    kwargs["since_id"] = int(since_id)

                response = self.twitter_client.search_recent_tweets(**kwargs)
            except Exception as exc:
                logger.warning("[Social] Conversation thread check failed for %s: %s", response_id, exc)
                continue

            user_lookup: dict[int, dict[str, Any]] = {}
            if response and hasattr(response, "includes") and response.includes:
                for user in response.includes.get("users", []):
                    user_lookup[user.id] = {
                        "username": user.username,
                        "name": getattr(user, "name", user.username),
                    }

            max_seen_id = int(since_id) if since_id else 0

            for tweet in (response.data or []) if response else []:
                author_id = getattr(tweet, "author_id", None)
                if author_id == own_user_id:
                    if tweet.id > max_seen_id:
                        max_seen_id = tweet.id
                    continue

                author_info = user_lookup.get(author_id, {})
                text = tweet.text or ""

                candidate = {
                    "tweet_id": str(tweet.id),
                    "author_handle": author_info.get("username", ""),
                    "author_name": author_info.get("name", ""),
                    "text": text,
                    "score": 7,  # Conversation replies get a baseline score
                    "reasons": ["conversation_followup"],
                    "target_handle": author_info.get("username", ""),
                    "target_category": "community",
                    "created_at": str(getattr(tweet, "created_at", "")),
                    "thread_context": {
                        "our_previous_text": event.get("text", ""),
                        "original_tweet_id": event.get("tweet_id"),
                    },
                }

                # Draft a contextual reply
                candidate["draft"] = await self._draft_conversation_reply(candidate)

                candidates.append(candidate)
                if tweet.id > max_seen_id:
                    max_seen_id = tweet.id

            if max_seen_id > (int(since_id) if since_id else 0):
                updated_checkpoints[response_id] = str(max_seen_id)

            threads_checked += 1

        # Save updated checkpoints (keep most recent 50)
        if updated_checkpoints:
            # Trim to 50 most recent entries
            entries = list(updated_checkpoints.items())
            if len(entries) > 50:
                entries = entries[-50:]
            await self.memory.remember_long(CONVERSATION_CHECKPOINTS_KEY, dict(entries))

        # Track participation
        participation = await self.memory.recall_long(THREAD_PARTICIPATION_KEY) or []
        for event in our_tweets[:max_threads]:
            rid = str(event["response_tweet_id"])
            if not any(p.get("response_tweet_id") == rid for p in participation):
                participation.append({
                    "response_tweet_id": rid,
                    "original_tweet_id": event.get("tweet_id"),
                    "timestamp": event.get("timestamp", time.time()),
                })
        participation = participation[-50:]  # Cap at 50
        await self.memory.remember_long(THREAD_PARTICIPATION_KEY, participation)

        candidates.sort(key=lambda c: int(c.get("score", 0)), reverse=True)
        return {"candidates": candidates, "threads_checked": threads_checked}

    async def _draft_conversation_reply(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Draft a reply that continues a conversation we're already in."""
        thread_ctx = candidate.get("thread_context", {})
        system_prompt = (
            "You are continuing a conversation as @purecortexai.\n"
            "You previously replied in this thread. Now someone has responded.\n"
            "Continue the conversation naturally: acknowledge their point, add value.\n"
            "Do not repeat yourself. Do not be promotional or pushy.\n"
            f"Use {OFFICIAL_TOKEN_TICKER} if the protocol token is mentioned; never use PRCX.\n\n"
            "Respond ONLY in valid JSON with fields:\n"
            "  'action': 'REPLY' | 'NONE',\n"
            "  'message': the reply text or empty string,\n"
            "  'rationale': short explanation."
        )
        user_prompt = (
            f"YOUR PREVIOUS MESSAGE: {thread_ctx.get('our_previous_text', 'N/A')}\n"
            f"THEIR REPLY: {candidate.get('text', '')}\n"
            f"AUTHOR: @{candidate.get('author_handle', 'unknown')}\n\n"
            "Reply only if you can meaningfully continue this conversation."
        )

        decision = await self.think(system_prompt, user_prompt, task_type="REPLY")
        if not decision:
            return {"action": "NONE", "message": "", "rationale": "Consensus unavailable"}

        action = decision.get("action", "NONE")
        message = self._normalize_token_terms(decision.get("message", ""))
        if action != "REPLY" or not message:
            return {
                "action": "NONE",
                "message": "",
                "rationale": decision.get("rationale", "No useful follow-up"),
            }

        return {
            "action": "REPLY",
            "message": message[:280],
            "rationale": decision.get("rationale", ""),
        }

    # ------------------------------------------------------------------
    # Dynamic target discovery
    # ------------------------------------------------------------------

    async def discover_new_targets(
        self,
        candidates: list[dict[str, Any]],
        *,
        max_new_targets: int = 3,
    ) -> list[dict[str, Any]]:
        """Discover new accounts to add to the campaign target list.

        Examines high-scoring engagement candidates and adds their authors
        as campaign targets if they aren't already tracked.
        """
        targets = await self._ensure_campaign_targets()
        if len(targets) >= MAX_CAMPAIGN_TARGETS:
            return []

        existing_handles = {t.get("handle", "").lower() for t in targets}
        new_targets: list[dict[str, Any]] = []

        for candidate in candidates:
            if len(new_targets) >= max_new_targets:
                break
            if len(targets) + len(new_targets) >= MAX_CAMPAIGN_TARGETS:
                break

            score = int(candidate.get("score", 0))
            if score < 8:
                continue

            handle = candidate.get("author_handle", "")
            if not handle or handle.lower() in existing_handles:
                continue

            # Infer topics from scoring reasons
            inferred_topics = []
            for reason in candidate.get("reasons", []):
                if reason.startswith("topic:"):
                    inferred_topics.append(reason.split(":", 1)[1])
            if not inferred_topics:
                inferred_topics = ["ecosystem"]

            new_target = {
                "handle": handle,
                "category": "discovered",
                "priority": min(8, max(6, score - 2)),
                "tag_worthy": False,
                "relationship_stage": "discovered",
                "engage_topics": inferred_topics[:4],
                "rationale": f"Discovered via engagement scan (score {score})",
                "discovered_at": time.time(),
            }
            new_targets.append(new_target)
            existing_handles.add(handle.lower())

        if new_targets:
            targets.extend(new_targets)
            await self.memory.remember_long(CAMPAIGN_TARGETS_KEY, targets)
            for t in new_targets:
                logger.info("[Social] Discovered new target: @%s (priority %d)", t["handle"], t["priority"])

        return new_targets

    @staticmethod
    def _normalize_token_terms(text: str) -> str:
        """Correct known ticker hallucinations before content is published."""
        if not text:
            return text

        normalized = text
        for pattern in FORBIDDEN_TOKEN_PATTERNS:
            normalized = pattern.sub(OFFICIAL_TOKEN_TICKER, normalized)

        if normalized != text:
            logger.warning("[Social] Corrected token ticker in generated content before posting.")

        return normalized

    # ------------------------------------------------------------------
    # Content generation helpers
    # ------------------------------------------------------------------

    async def generate_tweet(self, topic: Optional[str] = None) -> str:
        """Generate a single tweet about PURECORTEX.

        Can be called directly (e.g. from an API endpoint) with an optional
        topic override. Returns the tweet text.
        """
        user_prompt = (
            f"Generate a single tweet for @purecortexai.\n"
            f"Topic: {topic or 'general PURECORTEX update'}\n"
            f"Keep it under 280 characters. Use the official ticker {OFFICIAL_TOKEN_TICKER}. "
            "Set content_type appropriately."
        )

        decision = await self.think(
            self.SYSTEM_PROMPT,
            user_prompt,
            task_type="POST",
        )

        if decision and decision.get("message"):
            return self._normalize_token_terms(decision["message"])

        return ""

    async def generate_thread(self, topic: str) -> List[str]:
        """Generate a tweet thread for a complex topic.

        Returns a list of tweet texts (each under 280 chars).
        """
        user_prompt = (
            f"Generate a tweet thread (3-6 tweets) for @purecortexai.\n"
            f"Topic: {topic}\n"
            "Set content_type to 'thread' and populate the 'thread' array. "
            "Each tweet must be under 280 characters. "
            f"The first tweet should hook readers, and the last should have a call-to-action. "
            f"Use the official ticker {OFFICIAL_TOKEN_TICKER} whenever the token is mentioned."
        )

        decision = await self.think(
            self.SYSTEM_PROMPT,
            user_prompt,
            task_type="POST",
        )

        if decision and decision.get("thread"):
            return [self._normalize_token_terms(tweet) for tweet in decision["thread"]]

        return []

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    async def _post_tweet(self, text: str) -> bool:
        """Post a single tweet to X. Returns True on success."""
        if not self.twitter_client:
            logger.info("[Social] No Twitter client — tweet not posted: %s", text[:80])
            return False

        try:
            response = self.twitter_client.create_tweet(text=text)
            tweet_id = response.data.get("id") if response.data else "unknown"
            logger.info("[Social] Posted tweet %s: %s", tweet_id, text[:80])
            return True
        except Exception as exc:
            logger.error("[Social] Tweet posting failed: %s", exc)
            return False

    async def _post_thread(self, tweets: List[str]) -> bool:
        """Post a tweet thread to X. Returns True if all tweets succeed."""
        if not self.twitter_client:
            logger.info("[Social] No Twitter client — thread not posted (%d tweets).", len(tweets))
            return False

        if not tweets:
            return False

        try:
            # Post the first tweet
            response = self.twitter_client.create_tweet(text=tweets[0])
            previous_id = response.data.get("id") if response.data else None

            if not previous_id:
                logger.error("[Social] First tweet in thread failed.")
                return False

            # Chain replies
            for tweet_text in tweets[1:]:
                response = self.twitter_client.create_tweet(
                    text=tweet_text,
                    in_reply_to_tweet_id=previous_id,
                )
                previous_id = response.data.get("id") if response.data else None
                if not previous_id:
                    logger.error("[Social] Thread broke at: %s", tweet_text[:60])
                    return False

            logger.info("[Social] Thread posted (%d tweets).", len(tweets))
            return True
        except Exception as exc:
            logger.error("[Social] Thread posting failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Context gathering
    # ------------------------------------------------------------------

    async def _gather_posting_context(self) -> Dict[str, Any]:
        """Gather context to inform content strategy.

        Includes recent posting history, content type distribution,
        protocol events, and launch campaign prompts when close to TGE.
        """
        recent = await self.memory.get_recent_episodes(limit=5)
        recent_types = [
            ep.get("context", {}).get("content_type", "unknown")
            for ep in recent
        ]

        stats = await self.memory.recall_long("content_stats") or {}
        pending_events = await self.memory.recall_short("protocol_events") or []

        ctx: Dict[str, Any] = {
            "recent_content_types": recent_types,
            "content_distribution": stats,
            "pending_events": pending_events,
            "timestamp": time.time(),
        }

        tge_iso = os.getenv("PURECORTEX_TGE_DATE", "2026-03-31T00:00:00Z")
        try:
            from datetime import datetime, timezone
            from src.services.launch_campaign import get_missed_prompts

            tge = datetime.fromisoformat(tge_iso.replace("Z", "+00:00"))
            days_until = (tge - datetime.now(timezone.utc)).days
            launch_prompt = get_launch_prompt_for_day(days_until)
            if launch_prompt:
                ctx["launch_campaign"] = {
                    "days_until_tge": days_until,
                    "scheduled_topic": launch_prompt["topic"],
                    "content_type": launch_prompt["content_type"],
                    "seed": launch_prompt["seed"],
                }

            # Detect missed campaign posts and flag for catch-up
            posted_offsets_raw = await self.memory.recall_long("campaign_posted_offsets")
            posted_offsets = set(posted_offsets_raw) if posted_offsets_raw else set()
            missed = get_missed_prompts(days_until, posted_offsets)
            if missed:
                # Prioritize the earliest missed post (Day 0 launch is highest priority)
                catchup = missed[0]
                ctx["launch_campaign_catchup"] = {
                    "missed_count": len(missed),
                    "priority_topic": catchup["topic"],
                    "priority_content_type": catchup["content_type"],
                    "priority_seed": catchup["seed"],
                    "priority_day_offset": catchup["day_offset"],
                }
                logger.warning(
                    "[Social] %d missed campaign posts detected. Priority catch-up: Day %+d '%s'",
                    len(missed), catchup["day_offset"], catchup["topic"],
                )
        except Exception as exc:
            logger.warning("[Social] Launch campaign context failed: %s", exc)

        return ctx

    async def _update_content_stats(self, content_type: str) -> None:
        """Track content type distribution in long-term memory."""
        stats = await self.memory.recall_long("content_stats") or {}
        stats[content_type] = stats.get(content_type, 0) + 1
        await self.memory.remember_long("content_stats", stats)

    # ------------------------------------------------------------------
    # Chat override
    # ------------------------------------------------------------------

    async def chat(self, user_message: str) -> str:
        """Chat about content strategy, recent posts, and campaigns."""
        extra_ctx_parts: list[str] = []

        # Include recent posting history
        recent = await self.memory.get_recent_episodes(limit=5)
        if recent:
            post_summary = [
                f"- {ep.get('context', {}).get('content_type', '?')}: "
                f"{ep.get('context', {}).get('content', '?')[:100]}"
                for ep in recent
            ]
            extra_ctx_parts.append("Recent posts:\n" + "\n".join(post_summary))

        # Content distribution
        stats = await self.memory.recall_long("content_stats")
        if stats:
            extra_ctx_parts.append(f"Content distribution: {json.dumps(stats)}")

        learning_ctx = await self.memory.get_learning_context("chat")

        system = self.CHAT_PROMPT
        if extra_ctx_parts:
            system += "\n\n### CURRENT STATE\n" + "\n\n".join(extra_ctx_parts)
        if learning_ctx:
            system += f"\n\n### RECENT CONTEXT\n{learning_ctx}"

        chat_system = (
            f"{system}\n\n"
            "Respond in valid JSON with fields: "
            "'action' (always 'REPLY'), 'message' (your conversational response)."
        )

        decision = await self.orchestrator.decide_action(chat_system, user_message)

        if decision and decision.get("message"):
            return decision["message"]

        return (
            "I'm the Social agent. I wasn't able to reach an internal consensus "
            "on that question — could you rephrase or try again shortly?"
        )
