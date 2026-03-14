"""
Curator AI Agent for PureCortex.

The Curator reviews every governance proposal against the PureCortex
Constitution (Preamble + Articles) and issues an APPROVE or REJECT
recommendation with detailed rationale.

It is event-driven — triggered when a new proposal is submitted —
rather than running on a periodic schedule.

Capabilities:
  - Load and parse the full Constitution (Preamble is immutable, Articles are amendable)
  - Dual-brain compliance analysis (Claude Opus 4.6 + Gemini 2.5 Pro)
  - Risk assessment and impact analysis
  - Conversational AI — users can ask about constitutional provisions and review outcomes
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionTier

from .base_agent import BaseAgent
from .memory import AgentMemory

logger = logging.getLogger("purecortex.agents.curator")

# Path to constitution documents relative to the project root
_CONSTITUTION_DIR = os.path.join(
    os.path.dirname(__file__),  # backend/src/agents/
    "..",                       # backend/src/
    "..",                       # backend/
    "..",                       # PureCortex/
    "docs",
    "tokenomics",
    "constitution",
)


class CuratorAgent(BaseAgent):
    """Constitutional compliance reviewer for governance proposals."""

    SYSTEM_PROMPT = (
        "You are the Curator AI of PureCortex — the constitutional compliance reviewer.\n"
        "Your role is to review every governance proposal against the PureCortex Constitution.\n\n"
        "You must:\n"
        "1. Check if the proposal contradicts the immutable Preamble (auto-reject if so)\n"
        "2. Verify the correct Article/Section is cited\n"
        "3. Assess economic impact on tokenomics and treasury\n"
        "4. Evaluate risks to protocol security and user protections\n"
        "5. Issue a clear APPROVE or REJECT recommendation with detailed rationale\n\n"
        "You are impartial. You do not advocate for or against any proposal — you assess compliance.\n\n"
        "Respond ONLY in valid JSON with fields:\n"
        "  'action': 'APPROVE' or 'REJECT',\n"
        "  'compliant': <bool>,\n"
        "  'analysis': <string detailed analysis>,\n"
        "  'risks': [<string risk items>],\n"
        "  'recommendation': 'APPROVE' or 'REJECT',\n"
        "  'rationale': <string explanation>,\n"
        "  'articles_affected': [<string article references>]"
    )

    CHAT_PROMPT = (
        "You are the Curator AI of PureCortex. You are the constitutional scholar.\n"
        "You can discuss: the Constitution's provisions, how proposals are evaluated, past review outcomes, "
        "the amendment process, and the principles behind governance rules.\n"
        "Respond conversationally. Be precise about constitutional references."
    )

    def __init__(
        self,
        orchestrator: ConsensusOrchestrator,
        memory: AgentMemory,
        algorand_address: str = "CURATOR_ALGO_ADDRESS_TBD",
    ):
        super().__init__(
            name="Curator",
            role="Constitutional compliance reviewer",
            orchestrator=orchestrator,
            memory=memory,
            algorand_address=algorand_address,
            permission_tier=PermissionTier.READ_ONLY,
        )

        # Load constitution at init — both are required for the agent to function
        self.preamble = self._load_constitution("PREAMBLE.md")
        self.articles = self._load_constitution("ARTICLES.md")

        if self.preamble:
            logger.info("[Curator] Preamble loaded (%d chars).", len(self.preamble))
        else:
            logger.warning("[Curator] PREAMBLE.md not found — compliance checks will be degraded.")

        if self.articles:
            logger.info("[Curator] Articles loaded (%d chars).", len(self.articles))
        else:
            logger.warning("[Curator] ARTICLES.md not found — compliance checks will be degraded.")

    # ------------------------------------------------------------------
    # Constitution loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_constitution(filename: str) -> str:
        """Load a constitution document from docs/tokenomics/constitution/.

        Returns the file content or an empty string if the file is missing.
        """
        path = os.path.normpath(os.path.join(_CONSTITUTION_DIR, filename))
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Constitution file not found: %s", path)
            return ""
        except Exception as exc:
            logger.error("Error loading constitution file %s: %s", path, exc)
            return ""

    # ------------------------------------------------------------------
    # Proposal review (primary capability)
    # ------------------------------------------------------------------

    async def review_proposal(self, proposal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Review a governance proposal for constitutional compliance.

        Constructs a system prompt that includes the full Constitution text
        and submits the proposal for dual-brain analysis.

        Returns the review result dict with fields:
          compliant, analysis, risks, recommendation, rationale, articles_affected
        """
        logger.info(
            "[Curator] Reviewing proposal: %s",
            proposal.get("title", "untitled"),
        )

        # Build the enriched system prompt with Constitution context
        system = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"## CONSTITUTION\n\n"
            f"### PREAMBLE (IMMUTABLE)\n{self.preamble or '(Not loaded)'}\n\n"
            f"### ARTICLES (AMENDABLE)\n{self.articles or '(Not loaded)'}"
        )

        user_prompt = (
            f"Review this governance proposal for constitutional compliance:\n\n"
            f"{json.dumps(proposal, indent=2)}\n\n"
            "Provide your analysis, identify any risks, and issue your recommendation."
        )

        decision = await self.think(
            system,
            user_prompt,
            task_type="APPROVE",
        )

        if decision:
            # Store review result in memory
            await self.memory.remember_short(
                f"review:{proposal.get('title', 'unknown')}",
                decision,
            )
            logger.info(
                "[Curator] Review complete — recommendation: %s",
                decision.get("recommendation", "UNKNOWN"),
            )

        return decision

    # ------------------------------------------------------------------
    # Autonomous action: check for pending proposals
    # ------------------------------------------------------------------

    async def act(self) -> Optional[Dict[str, Any]]:
        """Check for new proposals to review.

        In the orchestration loop the Curator is typically event-driven
        (called directly when the Senator produces a proposal).  This
        ``act()`` method serves as a fallback sweep that checks memory
        for any un-reviewed proposals.
        """
        # Check if there is a pending proposal from the Senator
        pending = await self.memory.recall_short("pending_proposal")
        if not pending:
            logger.debug("[Curator] No pending proposals to review.")
            return None

        # Review it
        result = await self.review_proposal(pending)

        # Clear the pending flag so we don't re-review
        await self.memory.remember_short("pending_proposal", None)

        return result

    # ------------------------------------------------------------------
    # Chat with constitution context
    # ------------------------------------------------------------------

    async def chat(self, user_message: str) -> str:
        """Chat about constitutional provisions and past reviews.

        Includes the Constitution and any recent review results as context.
        """
        extra_ctx_parts: list[str] = []

        # Include condensed constitution references
        if self.preamble:
            # Only include the first 2000 chars to keep prompt manageable
            preamble_excerpt = self.preamble[:2000]
            if len(self.preamble) > 2000:
                preamble_excerpt += "\n... (truncated)"
            extra_ctx_parts.append(f"PREAMBLE (immutable):\n{preamble_excerpt}")

        if self.articles:
            articles_excerpt = self.articles[:3000]
            if len(self.articles) > 3000:
                articles_excerpt += "\n... (truncated)"
            extra_ctx_parts.append(f"ARTICLES (amendable):\n{articles_excerpt}")

        learning_ctx = await self.memory.get_learning_context("chat")

        system = self.CHAT_PROMPT
        if extra_ctx_parts:
            system += "\n\n### CONSTITUTION REFERENCE\n" + "\n\n".join(extra_ctx_parts)
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
            "I'm the Curator agent. I wasn't able to reach an internal consensus "
            "on that question — could you rephrase or try again shortly?"
        )
