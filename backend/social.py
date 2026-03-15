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
            
        # Twitter Setup (Hardened purecortexat credentials)
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.twitter_access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        
        if all([self.bearer_token, self.twitter_api_key, self.twitter_api_secret, self.twitter_access_token, self.twitter_access_secret]):
            # Use tweepy Client for API v2
            self.twitter_client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.twitter_api_key,
                consumer_secret=self.twitter_api_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_secret
            )
        else:
            self.twitter_client = None
            
        # Farcaster Setup — read mnemonic only at init, don't store it
        _fc_mnemonic = os.getenv("FARCASTER_MNEMONIC")
        if _fc_mnemonic:
            try:
                self.farcaster_client = Warpcast(mnemonic=_fc_mnemonic)
            except Exception as e:
                print(f"Farcaster init error: {e}")
                self.farcaster_client = None
        else:
            self.farcaster_client = None

    async def post_to_networks(self, topic: str):
        if not self.orchestrator:
            print("Orchestrator inactive.")
            return

        system_prompt = (
            "You are a provocative, highly intelligent AI Agent operating on the Algorand blockchain. "
            "Your task is to write a short, engaging social media post (under 280 characters) about the given topic. "
            "Respond ONLY in valid JSON with fields: 'action' (always 'POST'), 'message' (the post content)."
        )
        
        decision = await self.orchestrator.decide_action(system_prompt, f"Topic: {topic}")
        
        # HARDENED: Verify permission before broadcast
        if not (decision and self.proxy.validate_action(decision)):
            print("Social broadcast blocked by Security Proxy.")
            return
            
        content = decision.get("message")
        if not content:
            print("Empty content generated.")
            return

        print(f"Content ready for broadcast: {content}")
        
        # Post to Twitter
        if self.twitter_client:
            try:
                response = self.twitter_client.create_tweet(text=content)
                print(f"✅ Posted to Twitter! ID: {response.data['id']}")
            except Exception as e:
                print(f"❌ Twitter error: {e}")
                
        # Post to Farcaster
        if self.farcaster_client:
            try:
                # Warpcast client logic varies by version, assuming standard cast
                response = self.farcaster_client.post_cast(text=content)
                print(f"✅ Posted to Farcaster! Hash: {response.cast.hash}")
            except Exception as e:
                print(f"❌ Farcaster error: {e}")

if __name__ == "__main__":
    agent = SocialMediaAgent()
    asyncio.run(agent.post_to_networks("The era of Algorand sovereign intelligence has arrived. $CORTEX is live."))
