import requests
import json
import os

def check_agent_status(api_key):
    """
    Checks the status of an agent on Moltbook using its API Key.
    """
    url = "https://www.moltbook.com/api/v1/agents/status"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print(f"--- Checking Agent Status on Moltbook ---")
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Agent Found!")
            print("-" * 40)
            print(json.dumps(data, indent=2))
            print("-" * 40)
            return data
        else:
            print(f"\n❌ Failed to check status!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

if __name__ == "__main__":
    # This script requires the API Key as input
    import sys
    if len(sys.argv) > 1:
        check_agent_status(sys.argv[1])
    else:
        print("Usage: python check_purecortex_status.py YOUR_API_KEY")
