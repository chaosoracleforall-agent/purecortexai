"""
Engagement cycle scheduler for the PURECORTEX Social Agent.

Manages operation rotation across engagement cycles to stay within
Twitter API rate limits while maximizing community interaction coverage.

Rate budget (Twitter Basic tier):
  - 10,000 read requests/month
  - 500 write requests/month (posts, replies, quote tweets)

At 45-minute intervals (~960 cycles/month), rotation keeps reads at
~5,760/month and writes at ~450/month.
"""

from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# Per-cycle engagement caps
# ---------------------------------------------------------------------------

CYCLE_MAX_REPLIES: int = int(os.getenv("SOCIAL_CYCLE_MAX_REPLIES", "3"))
CYCLE_MAX_RETWEETS: int = int(os.getenv("SOCIAL_CYCLE_MAX_RETWEETS", "3"))
CYCLE_MAX_LIKES: int = int(os.getenv("SOCIAL_CYCLE_MAX_LIKES", "8"))
CYCLE_MAX_QUOTE_TWEETS: int = int(os.getenv("SOCIAL_CYCLE_MAX_QUOTE_TWEETS", "2"))
CYCLE_MAX_FOLLOWS: int = int(os.getenv("SOCIAL_CYCLE_MAX_FOLLOWS", "2"))
CYCLE_MAX_MENTION_REPLIES: int = int(os.getenv("SOCIAL_CYCLE_MAX_MENTION_REPLIES", "3"))
CYCLE_MAX_FOLLOWER_ENGAGEMENTS: int = int(os.getenv("SOCIAL_CYCLE_MAX_FOLLOWER_ENGAGEMENTS", "3"))

# Aggregate daily write limit (posts + replies + quote tweets combined)
MAX_TOTAL_WRITES_PER_DAY: int = int(os.getenv("SOCIAL_MAX_TOTAL_WRITES_PER_DAY", "30"))

# Dynamic target discovery
MAX_CAMPAIGN_TARGETS: int = int(os.getenv("SOCIAL_MAX_CAMPAIGN_TARGETS", "30"))

# ---------------------------------------------------------------------------
# Operation rotation schedule
#   key: operation name
#   value: run every Nth cycle (1 = every cycle, 2 = every other, etc.)
# ---------------------------------------------------------------------------

OPERATION_SCHEDULE: dict[str, int] = {
    "mentions": 1,
    "search": 1,
    "home_timeline": 2,
    "conversation_threads": 3,
    "follower_scan": 4,
    "campaign_targets": 4,
    "dynamic_discovery": 8,
}


class EngagementScheduler:
    """Determines which operations to run each cycle and provides per-cycle caps."""

    def __init__(self) -> None:
        self._cycle_counter: int = 0

    def advance_cycle(self) -> int:
        """Increment and return the new cycle number."""
        self._cycle_counter += 1
        return self._cycle_counter

    @property
    def cycle(self) -> int:
        return self._cycle_counter

    def should_run(self, operation: str) -> bool:
        """Return True if *operation* should execute in the current cycle."""
        interval = OPERATION_SCHEDULE.get(operation, 1)
        return self._cycle_counter % interval == 0

    @staticmethod
    def get_cycle_caps() -> dict[str, int]:
        """Return per-cycle engagement caps (re-read from module-level constants)."""
        return {
            "replies": CYCLE_MAX_REPLIES,
            "retweets": CYCLE_MAX_RETWEETS,
            "likes": CYCLE_MAX_LIKES,
            "quote_tweets": CYCLE_MAX_QUOTE_TWEETS,
            "follows": CYCLE_MAX_FOLLOWS,
            "mention_replies": CYCLE_MAX_MENTION_REPLIES,
            "follower_engagements": CYCLE_MAX_FOLLOWER_ENGAGEMENTS,
        }
