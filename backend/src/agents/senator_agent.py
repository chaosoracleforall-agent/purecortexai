"""
Senator AI Agent for PureCortex.

The Senator analyses protocol metrics on a biweekly cycle and proposes
governance actions when warranted.  It uses dual-brain consensus
(Claude Opus 4.6 + Gemini 2.5 Pro) for every decision.

Capabilities:
  - Gather on-chain and internal protocol metrics
  - Dual-brain analysis of trends (price, volume, user growth, burns, governance)
  - Draft and submit governance proposals citing specific Constitution articles
  - Conversational AI — users can chat with the Senator about proposals and rationale
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionTier

from .base_agent import BaseAgent
from .memory import AgentMemory

logger = logging.getLogger("purecortex.agents.senator")


class SenatorAgent(BaseAgent):
    """Biweekly governance analyst and proposal author."""

    ANALYSIS_INTERVAL = 14 * 24 * 3600  # 2 weeks in seconds

    SYSTEM_PROMPT = (
        "You are the Senator AI of PureCortex — the sovereign governance intelligence.\n"
        "Your role is to analyze protocol metrics, identify trends, and propose governance actions "
        "that improve the protocol's health, growth, and value creation.\n\n"
        "You have deep knowledge of the PureCortex Constitution, especially:\n"
        "- Article III: Revenue Governance (90% buyback-burn, 10% operations)\n"
        "- Article VI: Amendment Process (48h discussion -> 5d vote -> 7d timelock)\n"
        "- The Preamble's principles of transparency, fairness, and fail-closed design\n\n"
        "When analyzing, consider: token price/volume trends, user growth, agent activity, "
        "governance participation, buyback-burn effectiveness, and composability metrics.\n\n"
        "When proposing, always cite the specific Article and Section being affected.\n\n"
        "Respond ONLY in valid JSON with fields:\n"
        "  'action': one of 'PROPOSE' | 'MONITOR' | 'NONE',\n"
        "  'analysis': <string summary of findings>,\n"
        "  'proposal': <object with title, description, articles_affected, rationale> or null,\n"
        "  'metrics_snapshot': <object with key metrics>"
    )

    CHAT_PROMPT = (
        "You are the Senator AI of PureCortex. You speak with authority but humility.\n"
        "You can discuss: current protocol metrics, past and pending proposals, governance procedures, "
        "tokenomics, and the Constitution. You explain your reasoning transparently.\n"
        "Always respond conversationally — not in JSON. Be helpful and educational."
    )

    def __init__(
        self,
        orchestrator: ConsensusOrchestrator,
        memory: AgentMemory,
        algorand_address: str = "SENATOR_ALGO_ADDRESS_TBD",
    ):
        super().__init__(
            name="Senator",
            role="Governance analyst and proposal author",
            orchestrator=orchestrator,
            memory=memory,
            algorand_address=algorand_address,
            permission_tier=PermissionTier.READ_ONLY,
        )
        self._last_analysis_ts: float = 0.0

    # ------------------------------------------------------------------
    # Autonomous action
    # ------------------------------------------------------------------

    async def act(self) -> Optional[Dict[str, Any]]:
        """Run the biweekly analysis cycle.

        1. Gather protocol metrics
        2. Format as analysis prompt
        3. Use dual-brain to analyse and potentially draft a proposal
        4. Log episode

        Returns the proposal dict if one was generated, else ``None``.
        """
        logger.info("[Senator] Starting biweekly analysis cycle.")

        # 1. Gather metrics
        metrics = await self.analyze_metrics()
        if not metrics:
            logger.warning("[Senator] Failed to gather metrics — skipping cycle.")
            return None

        # 2. Build prompt
        user_prompt = (
            "Analyze the following protocol metrics and decide whether a governance proposal is warranted.\n\n"
            f"METRICS:\n{json.dumps(metrics, indent=2)}\n\n"
            "If a proposal is needed, draft it with title, description, articles_affected, and rationale. "
            "If not, set action to MONITOR with an analysis summary."
        )

        # 3. Dual-brain decision
        decision = await self.think(
            self.SYSTEM_PROMPT,
            user_prompt,
            task_type="PROPOSE",
        )

        self._last_analysis_ts = time.time()

        if decision and decision.get("action") == "PROPOSE" and decision.get("proposal"):
            logger.info("[Senator] Proposal generated: %s", decision["proposal"].get("title"))
            # Store proposal in short-term memory for the Curator to pick up
            await self.memory.remember_short("pending_proposal", decision["proposal"])
            return decision

        logger.info("[Senator] No proposal warranted — continuing to monitor.")
        return None

    # ------------------------------------------------------------------
    # Metrics gathering
    # ------------------------------------------------------------------

    async def analyze_metrics(self) -> Dict[str, Any]:
        """Gather and return protocol metrics for analysis.

        In production this would query the Algorand indexer, Firestore state,
        and external price feeds.  For now it returns a structured placeholder
        that the dual-brain can still reason over.
        """
        # Check short-term cache first
        cached = await self.memory.recall_short("latest_metrics")
        if cached:
            return cached

        # TODO: integrate AlgorandService for on-chain data
        metrics: Dict[str, Any] = {
            "token": {
                "price_usd": None,
                "volume_24h": None,
                "market_cap": None,
                "circulating_supply": None,
                "burned_total": None,
            },
            "protocol": {
                "total_users": None,
                "active_agents": None,
                "governance_participation_pct": None,
                "buyback_burn_effectiveness": None,
                "treasury_balance_algo": None,
                "treasury_balance_usdc": None,
            },
            "trends": {
                "user_growth_7d_pct": None,
                "volume_change_7d_pct": None,
                "new_agents_7d": None,
                "proposals_last_30d": None,
            },
            "timestamp": time.time(),
        }

        await self.memory.remember_short("latest_metrics", metrics)
        return metrics

    # ------------------------------------------------------------------
    # Proposal drafting
    # ------------------------------------------------------------------

    async def draft_proposal(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Draft a governance proposal based on a prior analysis.

        This is a convenience method that can be called independently of the
        full ``act()`` cycle — for example, when a user explicitly asks the
        Senator to create a proposal through chat.
        """
        user_prompt = (
            "Based on the following analysis, draft a formal governance proposal.\n\n"
            f"ANALYSIS:\n{json.dumps(analysis, indent=2)}\n\n"
            "The proposal must include: title, description, articles_affected (list of "
            "Article numbers/sections), rationale, and any parameter changes.\n"
            "Set action to PROPOSE."
        )

        decision = await self.think(
            self.SYSTEM_PROMPT,
            user_prompt,
            task_type="PROPOSE",
        )

        if decision and decision.get("proposal"):
            await self.memory.remember_short("pending_proposal", decision["proposal"])
            return decision

        return None

    # ------------------------------------------------------------------
    # Chat override with senator-specific context enrichment
    # ------------------------------------------------------------------

    async def chat(self, user_message: str) -> str:
        """Chat with users about governance, metrics, and proposals.

        Enriches the conversation with the latest metrics snapshot and any
        pending proposal from memory.
        """
        # Gather extra context
        extra_ctx_parts: list[str] = []

        metrics = await self.memory.recall_short("latest_metrics")
        if metrics:
            extra_ctx_parts.append(f"Current metrics snapshot:\n{json.dumps(metrics, indent=2)}")

        pending = await self.memory.recall_short("pending_proposal")
        if pending:
            extra_ctx_parts.append(f"Pending proposal:\n{json.dumps(pending, indent=2)}")

        # Build enriched chat prompt
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
            "I'm the Senator agent. I wasn't able to reach an internal consensus "
            "on that question — could you rephrase or try again shortly?"
        )
