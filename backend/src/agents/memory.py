"""
Agent Memory & Feedback Loop for PURECORTEX.

Provides three memory tiers backed by Redis:
  - Short-term memory (1 h TTL) — current context, scratchpad
  - Long-term memory (permanent) — learned preferences, patterns, strategies
  - Episodic memory — timestamped action logs used for the feedback loop

Agents learn from their own history: ``get_learning_context`` retrieves the
most relevant past episodes as few-shot examples that are injected into the
system prompt before each decision.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

logger = logging.getLogger("purecortex.agents.memory")

# Redis command timeout (seconds)
REDIS_CMD_TIMEOUT = int(os.getenv("REDIS_CMD_TIMEOUT", "5"))

# TTL constants (configurable via env vars)
SHORT_TERM_TTL = int(os.getenv("AGENT_SHORT_TERM_TTL", "3600"))       # 1 hour
EPISODE_TTL = int(os.getenv("AGENT_EPISODE_TTL", str(90 * 24 * 3600)))  # 90 days

# Maximum number of episodes kept per agent (ring buffer via LTRIM)
MAX_EPISODES = int(os.getenv("AGENT_MAX_EPISODES", "1000"))


class AgentMemory:
    """Redis-backed persistent memory with feedback loop for agent learning."""

    def __init__(
        self,
        agent_name: str,
        redis_url: str = "redis://redis:6379/0",
    ):
        self.agent_name = agent_name
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None

        # Key prefixes scoped to the agent
        self._short_prefix = f"purecortex:{agent_name}:short"
        self._long_prefix = f"purecortex:{agent_name}:long"
        self._episode_key = f"purecortex:{agent_name}:episodes"
        self._metrics_key = f"purecortex:{agent_name}:metrics"

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        """Establish connection to Redis (idempotent)."""
        if self._redis is not None:
            return
        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=REDIS_CMD_TIMEOUT,
        )
        try:
            await asyncio.wait_for(self._redis.ping(), timeout=REDIS_CMD_TIMEOUT)
            logger.info("Memory connected for agent '%s'", self.agent_name)
        except Exception as exc:
            logger.warning(
                "Redis unavailable at %s for agent '%s': %s — running with memory disabled",
                self.redis_url,
                self.agent_name,
                exc,
            )
            self._redis = None

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    # ------------------------------------------------------------------
    # Short-term memory (1 h TTL) — current context / scratchpad
    # ------------------------------------------------------------------

    async def remember_short(self, key: str, value: Any) -> None:
        """Store a short-lived value (expires after SHORT_TERM_TTL)."""
        if not self._redis:
            return
        try:
            full_key = f"{self._short_prefix}:{key}"
            await asyncio.wait_for(
                self._redis.setex(full_key, SHORT_TERM_TTL, json.dumps(value, default=str)),
                timeout=REDIS_CMD_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("remember_short timed out for key: %s", key)
        except Exception as exc:
            logger.error("remember_short failed: %s", exc)

    async def recall_short(self, key: str) -> Optional[Any]:
        """Retrieve a short-term value, or ``None`` if expired / missing."""
        if not self._redis:
            return None
        try:
            full_key = f"{self._short_prefix}:{key}"
            raw = await asyncio.wait_for(
                self._redis.get(full_key), timeout=REDIS_CMD_TIMEOUT
            )
            return json.loads(raw) if raw else None
        except asyncio.TimeoutError:
            logger.error("recall_short timed out for key: %s", key)
            return None
        except Exception as exc:
            logger.error("recall_short failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Long-term memory (permanent) — learned preferences, patterns
    # ------------------------------------------------------------------

    async def remember_long(self, key: str, value: Any) -> None:
        """Persist a value permanently (no TTL)."""
        if not self._redis:
            return
        try:
            full_key = f"{self._long_prefix}:{key}"
            await asyncio.wait_for(
                self._redis.set(full_key, json.dumps(value, default=str)),
                timeout=REDIS_CMD_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("remember_long timed out for key: %s", key)
        except Exception as exc:
            logger.error("remember_long failed: %s", exc)

    async def recall_long(self, key: str) -> Optional[Any]:
        """Retrieve a long-term value."""
        if not self._redis:
            return None
        try:
            full_key = f"{self._long_prefix}:{key}"
            raw = await asyncio.wait_for(
                self._redis.get(full_key), timeout=REDIS_CMD_TIMEOUT
            )
            return json.loads(raw) if raw else None
        except asyncio.TimeoutError:
            logger.error("recall_long timed out for key: %s", key)
            return None
        except Exception as exc:
            logger.error("recall_long failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Episodic memory — action logs for the feedback loop
    # ------------------------------------------------------------------

    async def log_episode(
        self,
        action: str,
        context: Dict[str, Any],
        outcome: Dict[str, Any],
        score: float,
    ) -> None:
        """Record an episode (action + context + outcome + reward score).

        Episodes are stored as a Redis list (newest first) and trimmed to
        ``MAX_EPISODES`` to prevent unbounded growth.
        """
        if not self._redis:
            return
        episode = {
            "timestamp": time.time(),
            "action": action,
            "context": context,
            "outcome": outcome,
            "score": score,
        }
        try:
            await asyncio.wait_for(
                self._redis.lpush(self._episode_key, json.dumps(episode, default=str)),
                timeout=REDIS_CMD_TIMEOUT,
            )
            await asyncio.wait_for(
                self._redis.ltrim(self._episode_key, 0, MAX_EPISODES - 1),
                timeout=REDIS_CMD_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("log_episode timed out for agent: %s", self.agent_name)
        except Exception as exc:
            logger.error("log_episode failed: %s", exc)

    async def get_recent_episodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the *limit* most recent episodes (newest first)."""
        if not self._redis:
            return []
        try:
            raw_list = await asyncio.wait_for(
                self._redis.lrange(self._episode_key, 0, limit - 1),
                timeout=REDIS_CMD_TIMEOUT,
            )
            return [json.loads(r) for r in raw_list]
        except asyncio.TimeoutError:
            logger.error("get_recent_episodes timed out for agent: %s", self.agent_name)
            return []
        except Exception as exc:
            logger.error("get_recent_episodes failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Feedback loop — performance metrics & learning context
    # ------------------------------------------------------------------

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Compute success rate, action counts, and average score from episodes.

        Returns a dict like::

            {
                "total_episodes": 42,
                "success_rate": 0.85,
                "avg_score": 0.78,
                "action_counts": {"PROPOSE": 5, "REPLY": 30, ...},
                "recent_avg_score": 0.90,  # last 10
            }
        """
        episodes = await self.get_recent_episodes(limit=MAX_EPISODES)
        if not episodes:
            return {
                "total_episodes": 0,
                "success_rate": 0.0,
                "avg_score": 0.0,
                "action_counts": {},
                "recent_avg_score": 0.0,
            }

        total = len(episodes)
        scores = [e.get("score", 0.0) for e in episodes]
        successes = sum(1 for s in scores if s > 0)
        action_counts: Dict[str, int] = {}
        for ep in episodes:
            act = ep.get("action", "UNKNOWN")
            action_counts[act] = action_counts.get(act, 0) + 1

        recent_scores = scores[: min(10, total)]

        return {
            "total_episodes": total,
            "success_rate": successes / total if total else 0.0,
            "avg_score": sum(scores) / total if total else 0.0,
            "action_counts": action_counts,
            "recent_avg_score": (
                sum(recent_scores) / len(recent_scores) if recent_scores else 0.0
            ),
        }

    async def get_learning_context(self, task_type: str) -> str:
        """Retrieve relevant past episodes formatted as few-shot examples.

        Filters episodes whose action matches *task_type* (case-insensitive)
        and formats the top results as a concise text block the agent can
        use for in-context learning.

        If *task_type* is ``"chat"`` it returns the most recent successful
        chat episodes regardless of action name.
        """
        episodes = await self.get_recent_episodes(limit=50)
        if not episodes:
            return ""

        # Filter relevant episodes
        if task_type.lower() == "chat":
            relevant = [
                e for e in episodes
                if e.get("score", 0) > 0 and e.get("action") in ("REPLY", "RESPOND")
            ]
        else:
            relevant = [
                e for e in episodes
                if e.get("score", 0) > 0
                and task_type.lower() in e.get("action", "").lower()
            ]

        # Fall back to all successful episodes
        if not relevant:
            relevant = [e for e in episodes if e.get("score", 0) > 0]

        # Take the top 5
        relevant = relevant[:5]
        if not relevant:
            return ""

        lines = ["Here are relevant past episodes to learn from:\n"]
        for i, ep in enumerate(relevant, 1):
            outcome_summary = ep.get("outcome", {})
            # Truncate large outcomes
            outcome_str = json.dumps(outcome_summary, default=str)
            if len(outcome_str) > 300:
                outcome_str = outcome_str[:300] + "..."
            lines.append(
                f"Episode {i} (score={ep.get('score', 0):.2f}):\n"
                f"  Action: {ep.get('action')}\n"
                f"  Outcome: {outcome_str}\n"
            )

        return "\n".join(lines)
