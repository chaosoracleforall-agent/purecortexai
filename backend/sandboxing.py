from enum import IntEnum
from typing import Dict, Any, Optional

class PermissionTier(IntEnum):
    READ_ONLY = 0      # Info, basic chat
    SOCIAL_POST = 1    # Tweeting, Farcaster casting
    ASSET_MANAGEMENT = 2 # Creating agents, minor swaps
    TREASURY_SWAP = 3   # Major ALGO/USDC swaps

class PermissionProxy:
    """
    Tiered Permission Escalation & Sandboxing Layer for PureCortex Agents.
    Hardened according to the DAIO security mandate.
    """
    
    def __init__(self, current_tier: PermissionTier = PermissionTier.READ_ONLY):
        self.current_tier = current_tier
        
        # Maps actions to their required tiers
        self.action_requirements = {
            "REPLY": PermissionTier.READ_ONLY,
            "RESPOND": PermissionTier.READ_ONLY,
            "POST": PermissionTier.SOCIAL_POST,
            "CREATE_AGENT": PermissionTier.ASSET_MANAGEMENT,
            "SWAP": PermissionTier.TREASURY_SWAP,
        }

    def validate_action(self, decision: Dict[str, Any]) -> bool:
        """
        Validates if the decision's requested 'action' is permitted within the current sandbox tier.
        """
        action = decision.get("action", "NONE")
        required_tier = self.action_requirements.get(action, PermissionTier.TREASURY_SWAP) # Default to max security
        
        if self.current_tier >= required_tier:
            return True
        else:
            print(f"⚠️ SECURITY ALERT: Action '{action}' BLOCKED. Required Tier: {required_tier.name}, Current: {self.current_tier.name}")
            return False

    def escalate_tier(self, new_tier: PermissionTier, authorization_token: str):
        """
        Escalates the current sandbox tier.
        In production, this would require a multi-sig authorization or user-signed hardware proof.
        """
        # Placeholder for hardened authorization check
        if authorization_token == "DAIO-HARDENED-ROOT":
            self.current_tier = new_tier
            print(f"✅ ESCALATION SUCCESS: Tier elevated to {new_tier.name}")
        else:
            print("❌ ESCALATION DENIED: Invalid authorization token.")
