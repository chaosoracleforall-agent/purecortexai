import requests
import json

def search_agent(name):
    """
    Searches for an agent on Moltbook by name.
    """
    url = f"https://www.moltbook.com/api/v1/agents/search"
    params = {"name": name}
    
    print(f"--- Searching for Agent: {name} ---")
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Search results:")
            print("-" * 40)
            print(json.dumps(data, indent=2))
            print("-" * 40)
            return data
        else:
            print(f"\n❌ Failed to search!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

if __name__ == "__main__":
    search_agent("PureCortex")
