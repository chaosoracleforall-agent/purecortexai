import tweepy
import os
from google.cloud import secretmanager

def get_secret(name):
    client = secretmanager.SecretManagerServiceClient()
    path = f"projects/purecortexai/secrets/{name}/versions/latest"
    response = client.access_secret_version(request={"name": path})
    return response.payload.data.decode("UTF-8")

def setup_twitter():
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

    # 2. Authenticate (v1.1 for profile updates, v2 for tweeting)
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    
    client_v2 = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )

    print("--- UPDATING TWITTER PROFILE: purecortexat ---")

    # A. Update Description
    description = "The premier launchpad for autonomous AI agents on Algorand. Cognitive consensus through tri-brain orchestration. Point of Emancipation: 03.31.26 🦞"
    try:
        api_v1.update_profile(description=description)
        print("✅ Description Updated.")
    except Exception as e:
        print(f"❌ Description Update Failed: {e}")

    # B. Update PFP & Banner (Manual step recommendation or upload attempt)
    # api_v1.update_profile_image('twitter_pfp.png')
    # api_v1.update_profile_banner('twitter_cover.png')
    
    # C. Post First Tweet
    try:
        client_v2.create_tweet(text="Hello world. The era of sovereign intelligence has begun on Algorand. $CORTEX 🦞")
        print("✅ First Tweet Posted: 'Hello world'...")
    except Exception as e:
        print(f"❌ Tweet Failed: {e}")

if __name__ == "__main__":
    setup_twitter()
