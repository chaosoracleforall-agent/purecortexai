import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from google.cloud import secretmanager
import anthropic
import google.generativeai as genai

class ConsensusOrchestrator:
    """
    Enterprise-grade Dual-Brain Orchestrator for PureCortex.
    Simultaneously prompts Claude 3.5 Sonnet and Gemini AI Ultra for consensus.
    """

    def __init__(self, project_id: str = "purecortexai"):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
        
        # Initialize Brains
        self._initialize_brains()

    def _get_secret(self, secret_id: str, version_id: str = "latest") -> str:
        """Retrieves a secret from GCP Secret Manager."""
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    def _initialize_brains(self):
        """Initializes both Claude and Gemini clients with secrets."""
        # 1. Initialize Claude 3.5 Sonnet
        claude_api_key = self._get_secret("CLAUDE_API_KEY")
        self.claude_client = anthropic.AsyncAnthropic(api_key=claude_api_key)

        # 2. Initialize Gemini AI Ultra
        gemini_api_key = self._get_secret("GEMINI_API_KEY")
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel("gemini-1.5-pro") # Mapping to AI Ultra

    async def _prompt_claude(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Prompts Claude 3.5 Sonnet and returns a structured response."""
        try:
            message = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            # Assuming the model returns valid JSON in its content
            return json.loads(message.content[0].text)
        except Exception as e:
            return {"error": f"Claude Error: {str(e)}", "action": "NONE"}

    async def _prompt_gemini(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Prompts Gemini AI Ultra and returns a structured response."""
        try:
            full_prompt = f"{system_prompt}\n\nUser Request: {user_prompt}"
            response = await self.gemini_model.generate_content_async(full_prompt)
            # Sanitizing and parsing JSON from Gemini's response
            content = response.text.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            return {"error": f"Gemini Error: {str(e)}", "action": "NONE"}

    def evaluate_consensus(self, claude_resp: Dict[str, Any], gemini_resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluates the logical consensus between the two brains.
        Returns the action if both agree, otherwise returns None for review.
        """
        action_claude = claude_resp.get("action")
        action_gemini = gemini_resp.get("action")

        # Basic consensus check: Do the primary actions match?
        if action_claude == action_gemini and action_claude != "NONE" and action_claude is not None:
            print(f"✅ CONSENSUS REACHED: Action '{action_claude}' approved by both brains.")
            return claude_resp
        else:
            print(f"❌ CONSENSUS FAILED: Brains disagreed or returned NONE.")
            print(f"Claude: {action_claude} | Gemini: {action_gemini}")
            return None

    async def decide_action(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Executes parallel inference and evaluates consensus.
        """
        print(f"--- Initiating Dual-Brain Deliberation ---")
        
        # 1. Parallel Inference
        claude_task = self._prompt_claude(system_prompt, user_prompt)
        gemini_task = self._prompt_gemini(system_prompt, user_prompt)
        
        claude_resp, gemini_resp = await asyncio.gather(claude_task, gemini_task)

        # 2. Consensus Evaluation
        return self.evaluate_consensus(claude_resp, gemini_resp)

# --- Usage Example (Stub) ---
if __name__ == "__main__":
    orchestrator = ConsensusOrchestrator()
    
    # Example Prompt for a Treasury Action
    system = "You are the PureCortex Core Intelligence. You must decide whether to approve a treasury swap on Algorand. Respond ONLY in valid JSON with fields: 'action' (SWAP|HOLD|NONE), 'asset_in', 'asset_out', 'amount', 'rationale'."
    user = "Should we swap 10,000 ALGO for USDC given current market volatility?"
    
    async def run_test():
        decision = await orchestrator.decide_action(system, user)
        if decision:
            print(f"Final Decision for Execution: {json.dumps(decision, indent=2)}")
        else:
            print("Action deferred to manual security review.")

    asyncio.run(run_test())
