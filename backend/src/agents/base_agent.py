"""
Base Agent Framework for PureCortex.

Every PureCortex AI agent inherits from BaseAgent, which wires up:
  - Dual-brain consensus (Claude Opus 4.6 + Gemini 2.5 Pro) via ConsensusOrchestrator
  - Permission sandboxing via PermissionProxy
  - Persistent memory with feedback loops via AgentMemory
  - A conversational chat interface scoped to the agent's domain
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# Imports from existing backend root modules
from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionProxy, PermissionTier

from .memory import AgentMemory

logger = logging.getLogger("purecortex.agents")


class BaseAgent(ABC):
    """Abstract base for all PureCortex AI agents."""

    # Subclasses must override
    SYSTEM_PROMPT: str = ""
    CHAT_PROMPT: str = ""

    def __init__(
        self,
        name: str,
        role: str,
        orchestrator: ConsensusOrchestrator,
        memory: AgentMemory,
        algorand_address: str = "",
        permission_tier: PermissionTier = PermissionTier.READ_ONLY,
    ):
        self.name = name
        self.role = role
        self.orchestrator = orchestrator
        self.memory = memory
        self.algorand_address = algorand_address
        self.permission_tier = permission_tier

        # Each agent gets its own sandboxed proxy at its declared tier
        self.proxy = PermissionProxy(current_tier=permission_tier)

        logger.info(
            "Agent '%s' initialised  role=%s  tier=%s  algo=%s",
            self.name,
            self.role,
            self.permission_tier.name,
            self.algorand_address or "UNSET",
        )

    # ------------------------------------------------------------------
    # Core: dual-brain decision making
    # ------------------------------------------------------------------

    async def think(
        self,
        system_prompt: str,
        user_input: str,
        *,
        task_type: str = "general",
    ) -> Optional[Dict[str, Any]]:
        """Use dual-brain consensus to make a validated decision.

        Steps:
          1. Optionally enrich the prompt with learning context from memory.
          2. Run parallel Claude + Gemini inference via ConsensusOrchestrator.
          3. Validate the consensus result through the PermissionProxy.
          4. Log the episode to memory for future learning.

        Returns the decision dict on success, or ``None`` when consensus
        fails or the action is blocked by the sandbox.
        """
        # Enrich prompt with relevant past episodes (few-shot learning)
        learning_ctx = await self.memory.get_learning_context(task_type)
        if learning_ctx:
            system_prompt = (
                f"{system_prompt}\n\n"
                f"### RELEVANT PAST EXPERIENCE\n{learning_ctx}"
            )

        decision = await self.orchestrator.decide_action(system_prompt, user_input)

        if decision is None:
            logger.warning("[%s] Dual-brain consensus failed.", self.name)
            await self.memory.log_episode(
                action="CONSENSUS_FAIL",
                context={"system_prompt": system_prompt[:200], "user_input": user_input[:200]},
                outcome={"error": "consensus_failed"},
                score=0.0,
            )
            return None

        if not self.proxy.validate_action(decision):
            logger.warning(
                "[%s] Action '%s' blocked by sandbox (tier=%s).",
                self.name,
                decision.get("action"),
                self.permission_tier.name,
            )
            await self.memory.log_episode(
                action=decision.get("action", "UNKNOWN"),
                context={"system_prompt": system_prompt[:200], "user_input": user_input[:200]},
                outcome={"error": "permission_denied"},
                score=0.0,
            )
            return None

        # Successful decision — log as positive episode
        await self.memory.log_episode(
            action=decision.get("action", "UNKNOWN"),
            context={"system_prompt": system_prompt[:200], "user_input": user_input[:200]},
            outcome=decision,
            score=1.0,
        )

        return decision

    # ------------------------------------------------------------------
    # Conversational chat
    # ------------------------------------------------------------------

    async def chat(self, user_message: str) -> str:
        """Conversational AI — each agent can chat with users about its domain.

        Uses the agent's ``CHAT_PROMPT`` as the system prompt and enriches it
        with recent episodic memory so the agent can reference past actions.
        """
        learning_ctx = await self.memory.get_learning_context("chat")

        system = self.CHAT_PROMPT
        if learning_ctx:
            system = f"{system}\n\n### RECENT CONTEXT\n{learning_ctx}"

        # For chat we still go through dual-brain but expect a conversational
        # response rather than a structured action.
        chat_system = (
            f"{system}\n\n"
            "Respond in valid JSON with fields: "
            "'action' (always 'REPLY'), 'message' (your conversational response)."
        )

        decision = await self.orchestrator.decide_action(chat_system, user_message)

        if decision and decision.get("message"):
            return decision["message"]

        # Fallback: if consensus fails, use a graceful degradation message
        return (
            f"I'm the {self.name} agent. I wasn't able to reach an internal consensus "
            f"on that question — could you rephrase or try again shortly?"
        )

    # ------------------------------------------------------------------
    # Abstract: autonomous action
    # ------------------------------------------------------------------

    @abstractmethod
    async def act(self) -> Optional[Dict[str, Any]]:
        """Agent's primary autonomous action.

        Called by the orchestration loop on the agent's schedule. Must be
        implemented by every concrete agent subclass.
        """
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def get_status(self) -> Dict[str, Any]:
        """Return a summary of the agent's current state and performance."""
        metrics = await self.memory.get_performance_metrics()
        return {
            "name": self.name,
            "role": self.role,
            "algorand_address": self.algorand_address,
            "permission_tier": self.permission_tier.name,
            "metrics": metrics,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} tier={self.permission_tier.name}>"
