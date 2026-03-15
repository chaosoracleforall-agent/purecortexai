import tweepy
import os
from google.cloud import secretmanager

def get_secret(name):
    client = secretmanager.SecretManagerServiceClient()
    path = f"projects/purecortexai/secrets/{name}/versions/latest"
    response = client.access_secret_version(request={"name": path})
    return response.payload.data.decode("UTF-8")

def setup_twitter():
    # Paths to assets
    pfp_path = '/Users/davidgarcia/PureCortex/backend/twitter_pfp_hardened.png'
    banner_path = '/Users/davidgarcia/PureCortex/backend/twitter_cover.png'

    # 1. Fetch Hardened Credentials
    try:
        api_key = get_secret("TWITTER_API_KEY")
        api_secret = get_secret("TWITTER_API_SECRET")
        access_token = get_secret("TWITTER_ACCESS_TOKEN")
        access_secret = get_secret("TWITTER_ACCESS_SECRET")
        bearer_token = get_secret("TWITTER_BEARER_TOKEN")
    except Exception as e:
        print(f"Error fetching secrets: {e}")
        return

    # 2. Authenticate
    # v1.1 for Profile & Media
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    
    # v2 for Tweeting
    client_v2 = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )

    print("--- INITIATING PURECORTEX AI IDENTITY ROLLOUT ---")

    # A. Update Metadata
    description = "The premier launchpad for autonomous AI agents on Algorand. Cognitive consensus through tri-brain orchestration. Point of Emancipation: 03.31.26 🦞"
    url = "https://purecortex.ai"
    try:
        api_v1.update_profile(description=description, url=url)
        print("✅ Profile Metadata Updated.")
    except Exception as e:
        print(f"❌ Metadata Failed: {e}")

    # B. Update PFP
    if os.path.exists(pfp_path):
        try:
            api_v1.update_profile_image(pfp_path)
            print("✅ Profile Picture Uploaded.")
        except Exception as e:
            print(f"❌ PFP Upload Failed: {e}")
    else:
        print(f"❌ PFP not found at {pfp_path}")

    # C. Update Banner
    if os.path.exists(banner_path):
        try:
            api_v1.update_profile_banner(banner_path)
            print("✅ Banner Image Uploaded.")
        except Exception as e:
            print(f"❌ Banner Upload Failed: {e}")
    else:
        print(f"❌ Banner not found at {banner_path}")

    # D. First Tweet
    try:
        client_v2.create_tweet(text="Hello world. The era of sovereign intelligence has begun on Algorand. $CORTEX 🦞")
        print("✅ Genesis Tweet Broadcasted.")
    except Exception as e:
        print(f"❌ Genesis Tweet Failed: {e}")

if __name__ == "__main__":
    setup_twitter()
