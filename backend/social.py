import asyncio
import tweepy
from farcaster import Warpcast
import os
from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionProxy, PermissionTier

class SocialMediaAgent:
    def __init__(self):
        # Security Proxy Initialization (Tiered Escalation)
        self.proxy = PermissionProxy(PermissionTier.SOCIAL_POST)
        
        # Initialize Orchestrator
        try:
            self.orchestrator = ConsensusOrchestrator()
        except Exception:
            self.orchestrator = None
            
        # ... (rest of Twitter/Farcaster init) ...

    async def post_to_networks(self, topic: str):
        if not self.orchestrator:
            print("Orchestrator inactive.")
            return

        system_prompt = (
            "You are a provocative AI Agent on Algorand. Respond ONLY in valid JSON "
            "with 'action' (POST) and 'message' (the content)."
        )
        
        decision = await self.orchestrator.decide_action(system_prompt, f"Topic: {topic}")
        
        # HARDENED: Verify permission before broadcast
        if not (decision and self.proxy.validate_action(decision)):
            print("Social broadcast blocked by Security Proxy.")
            return
            
        content = decision.get("message")
        print(f"Content ready for broadcast: {content}")
        
        # ... (Twitter/Farcaster post code) ...

if __name__ == "__main__":
    agent = SocialMediaAgent()
    asyncio.run(agent.post_to_networks("The future of autonomous AI agents on Algorand."))
