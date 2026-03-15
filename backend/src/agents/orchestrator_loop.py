"""
Agent Orchestration Loop for PURECORTEX.

Manages background asyncio tasks for all agents.  Designed to be integrated
with FastAPI's lifespan so that agent loops start when the server boots
and shut down cleanly when it stops.

Usage with FastAPI::

    from contextlib import asynccontextmanager
    from fastapi import FastAPI

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await loop.start()
        yield
        await loop.stop()

    app = FastAPI(lifespan=lifespan)
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from .senator_agent import SenatorAgent
from .curator_agent import CuratorAgent
from .social_agent import SocialAgent

logger = logging.getLogger("purecortex.agents.loop")


class AgentOrchestrationLoop:
    """Manages background asyncio tasks for all PURECORTEX agents."""

    # Default intervals (seconds)
    SENATOR_INTERVAL = 14 * 24 * 3600   # 2 weeks
    SOCIAL_INTERVAL = 4 * 3600           # 4 hours
    CURATOR_SWEEP_INTERVAL = 60 * 60     # 1 hour (fallback sweep for un-reviewed proposals)

    def __init__(
        self,
        senator: SenatorAgent,
        curator: CuratorAgent,
        social: SocialAgent,
        *,
        senator_interval: Optional[int] = None,
        social_interval: Optional[int] = None,
        curator_sweep_interval: Optional[int] = None,
    ):
        self.senator = senator
        self.curator = curator
        self.social = social

        self._senator_interval = senator_interval or self.SENATOR_INTERVAL
        self._social_interval = social_interval or self.SOCIAL_INTERVAL
        self._curator_sweep_interval = curator_sweep_interval or self.CURATOR_SWEEP_INTERVAL

        self._tasks: List[asyncio.Task] = []
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start all agent background loops."""
        if self._running:
            logger.warning("Orchestration loop already running — ignoring start().")
            return

        logger.info("Starting PURECORTEX agent orchestration loop.")
        self._running = True

        # Connect agent memories
        await self.senator.memory.connect()
        await self.curator.memory.connect()
        await self.social.memory.connect()

        # Initialize GPG encryption + isolated signing vaults
        await self.senator.init_crypto()
        await self.curator.init_crypto()
        await self.social.init_crypto()
        logger.info("Agent GPG + signing vaults initialized.")

        self._tasks = [
            asyncio.create_task(self._senator_loop(), name="senator_loop"),
            asyncio.create_task(self._social_loop(), name="social_loop"),
            asyncio.create_task(self._curator_sweep_loop(), name="curator_sweep_loop"),
        ]

        logger.info(
            "Agent loops started: senator (%ds), social (%ds), curator sweep (%ds).",
            self._senator_interval,
            self._social_interval,
            self._curator_sweep_interval,
        )

    async def stop(self) -> None:
        """Gracefully stop all agent loops and disconnect memories."""
        if not self._running:
            return

        logger.info("Stopping PURECORTEX agent orchestration loop.")
        self._running = False

        for task in self._tasks:
            task.cancel()

        # Wait for cancellation to propagate
        results = await asyncio.gather(*self._tasks, return_exceptions=True)
        for task, result in zip(self._tasks, results):
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                logger.error("Task %s raised during shutdown: %s", task.get_name(), result)

        self._tasks.clear()

        # Clean up GPG keyrings and signing vaults
        await self.senator.cleanup_crypto()
        await self.curator.cleanup_crypto()
        await self.social.cleanup_crypto()

        # Disconnect memories
        await self.senator.memory.disconnect()
        await self.curator.memory.disconnect()
        await self.social.memory.disconnect()

        logger.info("All agent loops stopped.")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def get_status(self) -> dict:
        """Return the status of all agents and their loops."""
        return {
            "running": self._running,
            "tasks": [
                {
                    "name": t.get_name(),
                    "done": t.done(),
                    "cancelled": t.cancelled(),
                }
                for t in self._tasks
            ],
            "agents": {
                "senator": await self.senator.get_status(),
                "curator": await self.curator.get_status(),
                "social": await self.social.get_status(),
            },
        }

    # ------------------------------------------------------------------
    # Background loops
    # ------------------------------------------------------------------

    async def _senator_loop(self) -> None:
        """Run Senator analysis on a biweekly schedule.

        When the Senator generates a proposal, the Curator is immediately
        triggered to review it (event-driven flow).
        """
        while self._running:
            try:
                logger.info("[Loop] Senator cycle starting.")
                result = await self.senator.act()

                if result and result.get("action") == "PROPOSE" and result.get("proposal"):
                    logger.info(
                        "[Loop] Senator produced proposal — triggering Curator review."
                    )
                    review = await self.curator.review_proposal(result["proposal"])
                    if review:
                        logger.info(
                            "[Loop] Curator recommendation: %s",
                            review.get("recommendation", "UNKNOWN"),
                        )
                else:
                    logger.info("[Loop] Senator cycle complete — no proposal generated.")

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("[Loop] Senator loop error: %s", exc, exc_info=True)

            await asyncio.sleep(self._senator_interval)

    async def _social_loop(self) -> None:
        """Run Social agent content generation every 4 hours."""
        while self._running:
            try:
                logger.info("[Loop] Social cycle starting.")
                result = await self.social.act()
                if result:
                    logger.info(
                        "[Loop] Social posted: %s",
                        result.get("content_type", "unknown"),
                    )
                else:
                    logger.info("[Loop] Social cycle complete — no content generated.")

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("[Loop] Social loop error: %s", exc, exc_info=True)

            await asyncio.sleep(self._social_interval)

    async def _curator_sweep_loop(self) -> None:
        """Periodically sweep for un-reviewed proposals.

        The primary path for Curator reviews is event-driven (triggered in
        ``_senator_loop`` above). This sweep loop is a safety net that checks
        memory for any proposals that slipped through — for example if a
        proposal was submitted via the API while the Senator loop was sleeping.
        """
        while self._running:
            try:
                result = await self.curator.act()
                if result:
                    logger.info(
                        "[Loop] Curator sweep found and reviewed a proposal: %s",
                        result.get("recommendation", "UNKNOWN"),
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("[Loop] Curator sweep error: %s", exc, exc_info=True)

            await asyncio.sleep(self._curator_sweep_interval)
