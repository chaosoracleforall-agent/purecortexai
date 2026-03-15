"""
Base Agent Framework for PURECORTEX.

Every PURECORTEX AI agent inherits from BaseAgent, which wires up:
  - Tri-brain consensus (Claude Opus 4.6 + Gemini 2.5 Pro + GPT-5) via ConsensusOrchestrator
  - Permission sandboxing via PermissionProxy
  - Persistent memory with feedback loops via AgentMemory
  - GPG encryption for inter-agent secret communication
  - Isolated Signing Vault for Algorand transaction signing
  - A conversational chat interface scoped to the agent's domain

Security protocol:
  - All inter-agent secrets MUST be GPG-encrypted to the recipient
  - Transaction signing ALWAYS happens in the isolated SigningVault subprocess
  - Private keys NEVER exist in the main agent process memory
  - GPG passphrases are fetched per-operation from Secret Manager (never cached)
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
    """Abstract base for all PURECORTEX AI agents."""

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

        # GPG + Signing Vault (initialized async via init_crypto())
        self._gpg = None           # GPGCrypto instance
        self._signing_vault = None  # SigningVault instance

        logger.info(
            "Agent '%s' initialised  role=%s  tier=%s  algo=%s",
            self.name,
            self.role,
            self.permission_tier.name,
            self.algorand_address or "UNSET",
        )

    # ------------------------------------------------------------------
    # Core: tri-brain decision making
    # ------------------------------------------------------------------

    async def think(
        self,
        system_prompt: str,
        user_input: str,
        *,
        task_type: str = "general",
    ) -> Optional[Dict[str, Any]]:
        """Use tri-brain consensus to make a validated decision.

        Steps:
          1. Optionally enrich the prompt with learning context from memory.
          2. Run parallel Claude + Gemini + GPT-5 inference via ConsensusOrchestrator.
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
            logger.warning("[%s] Tri-brain consensus failed.", self.name)
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

        # For chat we still go through tri-brain but expect a conversational
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
    # GPG + Signing Vault
    # ------------------------------------------------------------------

    async def init_crypto(self) -> None:
        """Initialize GPG encryption and the isolated signing vault.

        Must be called after __init__ (async operations can't run in __init__).
        The orchestration loop calls this during startup.
        """
        identity = self.name.lower()  # "senator", "curator", "social"

        try:
            from ..services.gpg_crypto import create_agent_gpg
            self._gpg = await create_agent_gpg(identity=identity)
            logger.info("[%s] GPG encryption initialized.", self.name)
        except Exception as e:
            logger.warning("[%s] GPG init failed (non-fatal): %s", self.name, e)

        try:
            from ..services.signing_vault import create_signing_vault
            self._signing_vault = await create_signing_vault(identity=identity)
            logger.info("[%s] Signing vault initialized.", self.name)
        except Exception as e:
            logger.warning("[%s] Signing vault init failed (non-fatal): %s", self.name, e)

    async def encrypt_to(self, plaintext: str, recipients: list[str]) -> str:
        """Encrypt a message to one or more recipients using GPG.

        All inter-agent secrets MUST use this method.
        """
        if not self._gpg:
            raise RuntimeError(f"[{self.name}] GPG not initialized — call init_crypto() first")
        return await self._gpg.encrypt(plaintext, recipients)

    async def decrypt(self, ciphertext: str) -> str:
        """Decrypt a GPG-encrypted message sent to this agent."""
        if not self._gpg:
            raise RuntimeError(f"[{self.name}] GPG not initialized — call init_crypto() first")
        return await self._gpg.decrypt(ciphertext)

    async def sign_message(self, message: str) -> str:
        """GPG-sign a message for non-repudiation."""
        if not self._gpg:
            raise RuntimeError(f"[{self.name}] GPG not initialized — call init_crypto() first")
        return await self._gpg.sign(message)

    async def verify_message(self, signed_message: str) -> tuple[bool, str]:
        """Verify a GPG-signed message. Returns (valid, signer_email)."""
        if not self._gpg:
            raise RuntimeError(f"[{self.name}] GPG not initialized — call init_crypto() first")
        return await self._gpg.verify(signed_message)

    async def sign_transaction(self, unsigned_txn_bytes: bytes) -> bytes:
        """Sign an Algorand transaction in the isolated signing vault.

        The private key is NEVER loaded into this process — signing happens
        in an isolated subprocess that decrypts the GPG-encrypted mnemonic,
        signs the transaction, zeros all key material, and returns only the
        signed bytes.
        """
        if not self._signing_vault:
            raise RuntimeError(
                f"[{self.name}] Signing vault not initialized — call init_crypto() first"
            )
        return await self._signing_vault.sign_transaction(unsigned_txn_bytes)

    async def sign_transaction_group(self, unsigned_txns: list[bytes]) -> list[bytes]:
        """Sign a group of Algorand transactions atomically in the vault."""
        if not self._signing_vault:
            raise RuntimeError(
                f"[{self.name}] Signing vault not initialized — call init_crypto() first"
            )
        return await self._signing_vault.sign_transaction_group(unsigned_txns)

    async def cleanup_crypto(self) -> None:
        """Clean up GPG keyrings on shutdown."""
        if self._gpg:
            await self._gpg.cleanup()
        self._signing_vault = None

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
            "gpg_ready": self._gpg is not None and self._gpg._initialized,
            "vault_ready": self._signing_vault is not None,
            "metrics": metrics,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} tier={self.permission_tier.name}>"
