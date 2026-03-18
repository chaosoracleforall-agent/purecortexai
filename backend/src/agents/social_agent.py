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
from src.services.social_campaign import get_seed_targets, score_target_tweet

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
            limits = {"date": today, "follow_count": 0, "reply_count": 0}
            await self.memory.remember_long(CAMPAIGN_LIMITS_KEY, limits)
        return limits

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

    async def get_campaign_targets(self) -> list[dict[str, Any]]:
        return await self._ensure_campaign_targets()

    async def get_campaign_status(self) -> dict[str, Any]:
        targets = await self._ensure_campaign_targets()
        history = await self._load_campaign_history()
        limits = await self._load_daily_limits()
        recent_posts = await self.memory.get_recent_episodes(limit=10)

        return {
            "account": "@purecortexai",
            "official_token_ticker": OFFICIAL_TOKEN_TICKER,
            "twitter_ready": self.twitter_client is not None,
            "target_count": len(targets),
            "high_priority_targets": [t["handle"] for t in sorted(targets, key=lambda item: item.get("priority", 0), reverse=True)[:5]],
            "daily_limits": {
                "date": limits["date"],
                "follow_count": limits["follow_count"],
                "reply_count": limits["reply_count"],
                "max_follows_per_day": MAX_FOLLOWS_PER_DAY,
                "max_replies_per_day": MAX_REPLIES_PER_DAY,
            },
            "recent_reply_events": history.get("reply_events", [])[-5:],
            "recent_follow_events": history.get("follow_events", [])[-5:],
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

        await self.memory.log_episode(
            action="CAMPAIGN",
            context={
                "auto_follow_enabled": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_FOLLOW", "1"),
                "auto_reply_enabled": self._env_enabled("SOCIAL_CAMPAIGN_AUTO_REPLY", "1"),
                "candidates_scanned": result["candidates_scanned"],
            },
            outcome=result,
            score=1.0 if result.get("reply_action") or result.get("follow_action") else 0.2,
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

        campaign_result = await self._autonomous_campaign_cycle()

        # 5. Log outcome
        score = 1.0 if posted else 0.5  # 0.5 = generated but not posted (no client)
        await self.memory.log_episode(
            action="POST",
            context={"content_type": content_type, "content": content[:200]},
            outcome={
                "posted": posted,
                "content_type": content_type,
                "campaign": campaign_result,
            },
            score=score,
        )

        # Track content type distribution in long-term memory
        await self._update_content_stats(content_type)

        decision["campaign"] = campaign_result
        return decision

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

        Includes recent posting history, content type distribution, and
        any protocol events from memory.
        """
        # Recent episodes to avoid repeating topics
        recent = await self.memory.get_recent_episodes(limit=5)
        recent_types = [
            ep.get("context", {}).get("content_type", "unknown")
            for ep in recent
        ]

        # Content type distribution from long-term memory
        stats = await self.memory.recall_long("content_stats") or {}

        # Any pending protocol events (could be set by Senator or external triggers)
        pending_events = await self.memory.recall_short("protocol_events") or []

        return {
            "recent_content_types": recent_types,
            "content_distribution": stats,
            "pending_events": pending_events,
            "timestamp": time.time(),
        }

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
