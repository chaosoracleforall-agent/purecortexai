import logging
from enum import IntEnum
from typing import Dict, Any, Optional

logger = logging.getLogger("purecortex.sandboxing")


class PermissionTier(IntEnum):
    READ_ONLY = 0      # Info, basic chat
    SOCIAL_POST = 1    # Tweeting, Farcaster casting
    ASSET_MANAGEMENT = 2 # Creating agents, minor swaps
    TREASURY_SWAP = 3   # Major ALGO/USDC swaps


class PermissionProxy:
    """
    Tiered Permission Escalation & Sandboxing Layer for PURECORTEX Agents.
    Hardened according to the DAIO security mandate.
    """

    def __init__(self, current_tier: PermissionTier = PermissionTier.READ_ONLY):
        self.current_tier = current_tier

        # Maps actions to their required tiers
        self.action_requirements = {
            "REPLY": PermissionTier.READ_ONLY,
            "RESPOND": PermissionTier.READ_ONLY,
            "MONITOR": PermissionTier.READ_ONLY,
            "ANALYZE": PermissionTier.READ_ONLY,
            "NONE": PermissionTier.READ_ONLY,
            "POST": PermissionTier.SOCIAL_POST,
            "PROPOSE": PermissionTier.ASSET_MANAGEMENT,
            "APPROVE": PermissionTier.ASSET_MANAGEMENT,
            "REJECT": PermissionTier.ASSET_MANAGEMENT,
            "CREATE_AGENT": PermissionTier.ASSET_MANAGEMENT,
            "SWAP": PermissionTier.TREASURY_SWAP,
            "EXECUTE": PermissionTier.TREASURY_SWAP,
            "CANCEL": PermissionTier.TREASURY_SWAP,
        }

    def validate_action(self, decision: Dict[str, Any]) -> bool:
        """
        Validates if the decision's requested 'action' is permitted within the current sandbox tier.
        """
        action = decision.get("action", "NONE")
        required_tier = self.action_requirements.get(action, PermissionTier.TREASURY_SWAP)  # Default to max security

        if self.current_tier >= required_tier:
            return True

        logger.warning(
            "Action '%s' BLOCKED. Required tier: %s, Current: %s",
            action, required_tier.name, self.current_tier.name,
        )
        return False

    def escalate_tier(self, new_tier: PermissionTier, authorization_token: str):
        """
        Escalates the current sandbox tier.
        Requires a valid authorization token set via SANDBOX_ESCALATION_TOKEN env var.
        In production, this should be replaced with multi-sig or hardware-signed proof.
        """
        import os
        import hmac

        expected = os.environ.get("SANDBOX_ESCALATION_TOKEN", "")
        if not expected:
            logger.error("ESCALATION DENIED: SANDBOX_ESCALATION_TOKEN not configured.")
            return

        if hmac.compare_digest(authorization_token, expected):
            self.current_tier = new_tier
            logger.info("ESCALATION SUCCESS: Tier elevated to %s", new_tier.name)
        else:
            logger.warning("ESCALATION DENIED: Invalid authorization token.")
