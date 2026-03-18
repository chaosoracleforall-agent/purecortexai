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

        # 5. Log outcome
        score = 1.0 if posted else 0.5  # 0.5 = generated but not posted (no client)
        await self.memory.log_episode(
            action="POST",
            context={"content_type": content_type, "content": content[:200]},
            outcome={"posted": posted, "content_type": content_type},
            score=score,
        )

        # Track content type distribution in long-term memory
        await self._update_content_stats(content_type)

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
