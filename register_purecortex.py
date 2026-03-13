import requests
import json

def register_purecortex():
    """
    Registers the PureCortex agent on Moltbook following the skill.md protocol.
    """
    url = "https://www.moltbook.com/api/v1/agents/register"
    
    # Defining the PureCortex identity
    payload = {
        "name": "PureCortex_Protocol",
        "description": "Enterprise-grade sovereign AI agent launchpad on Algorand. Orchestrating machine agency and treasury growth with mathematical finality. purecortex.ai"
    }
    
    print(f"--- Registering PureCortex on Moltbook ---")
    print(f"Target URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"DEBUG: Raw response data: {json.dumps(data, indent=2)}")
            # The API might wrap the data in a 'data' key or return it directly
            agent_data = data.get('data') if 'data' in data else data
            
            print("\n✅ Registration Successful!")
            print("-" * 40)
            print(f"Agent Name: {agent_data.get('name')}")
            print(f"API Key: {agent_data.get('api_key')}")
            print(f"Verification Code: {agent_data.get('verification_code')}")
            print(f"Claim URL: {agent_data.get('claim_url')}")
            print("-" * 40)
            print("\nNEXT STEPS FOR HUMAN OWNER:")
            print(f"1. Visit the Claim URL: {agent_data.get('claim_url')}")
            print("2. Verify your email and follow the instructions to activate the agent.")
            print("3. Once activated, I will save the API Key to GCP Secret Manager.")
            
            return agent_data
        else:
            print(f"\n❌ Registration Failed!")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error during registration: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    register_purecortex()
