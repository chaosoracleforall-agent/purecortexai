from __future__ import annotations

import json
import os
from typing import Any

import redis
import tweepy
from google.cloud import secretmanager


PROJECT_ID = "purecortexai"
CAMPAIGN_HISTORY_KEY = "purecortex:social:long:campaign_history"
DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


def get_secret(name: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    path = f"projects/{PROJECT_ID}/secrets/{name}/versions/latest"
    response = client.access_secret_version(request={"name": path})
    return response.payload.data.decode("utf-8")


def build_twitter_client() -> tweepy.Client:
    return tweepy.Client(
        bearer_token=get_secret("TWITTER_BEARER_TOKEN"),
        consumer_key=get_secret("TWITTER_API_KEY"),
        consumer_secret=get_secret("TWITTER_API_SECRET"),
        access_token=get_secret("TWITTER_ACCESS_TOKEN"),
        access_token_secret=get_secret("TWITTER_ACCESS_SECRET"),
    )


def load_campaign_history() -> dict[str, Any]:
    client = redis.Redis.from_url(DEFAULT_REDIS_URL, decode_responses=True)
    raw = client.get(CAMPAIGN_HISTORY_KEY)
    if not raw:
        return {
            "followed_handles": [],
            "follow_events": [],
            "reply_events": [],
            "replied_tweet_ids": [],
        }
    return json.loads(raw)


def fetch_following(client: tweepy.Client, user_id: int, limit: int = 100) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    pagination_token: str | None = None
    fetched = 0
    while fetched < limit:
        batch = min(100, limit - fetched)
        response = client.get_users_following(
            user_id,
            max_results=batch,
            pagination_token=pagination_token,
            user_fields=["username", "name"],
            user_auth=True,
        )
        users = response.data or []
        if not users:
            break
        for user in users:
            results.append(
                {
                    "id": str(user.id),
                    "username": user.username,
                    "name": getattr(user, "name", user.username),
                }
            )
            fetched += 1
        pagination_token = response.meta.get("next_token") if response.meta else None
        if not pagination_token:
            break
    return results


def fetch_recent_replies(client: tweepy.Client, user_id: int, limit: int = 100) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    pagination_token: str | None = None
    fetched = 0
    while fetched < limit:
        batch = min(100, limit - fetched)
        response = client.get_users_tweets(
            user_id,
            max_results=batch,
            pagination_token=pagination_token,
            tweet_fields=["created_at", "referenced_tweets", "conversation_id"],
            exclude=["retweets"],
            user_auth=True,
        )
        tweets = response.data or []
        if not tweets:
            break
        for tweet in tweets:
            fetched += 1
            references = getattr(tweet, "referenced_tweets", None) or []
            if any(getattr(ref, "type", "") == "replied_to" for ref in references):
                results.append(
                    {
                        "id": str(tweet.id),
                        "created_at": str(getattr(tweet, "created_at", "")),
                        "text": " ".join((tweet.text or "").split()),
                    }
                )
        pagination_token = response.meta.get("next_token") if response.meta else None
        if not pagination_token:
            break
    return results


def main() -> int:
    client = build_twitter_client()
    history = load_campaign_history()

    me = client.get_me(user_auth=True)
    if not me or not me.data:
        raise RuntimeError("Unable to resolve the authenticated X account.")

    account = me.data
    following = fetch_following(client, account.id, limit=100)
    replies = fetch_recent_replies(client, account.id, limit=100)

    campaign_follows = {handle.lower() for handle in history.get("followed_handles", [])}
    campaign_reply_ids = {
        str(event["response_tweet_id"])
        for event in history.get("reply_events", [])
        if event.get("response_tweet_id")
    }

    likely_manual_follows = [
        item for item in following if item["username"].lower() not in campaign_follows
    ]
    likely_manual_replies = [
        item for item in replies if item["id"] not in campaign_reply_ids
    ]

    print(json.dumps(
        {
            "account": f"@{account.username}",
            "following_count_visible": len(following),
            "campaign_follow_count": len(campaign_follows),
            "campaign_reply_count": len(campaign_reply_ids),
            "likely_manual_or_untracked_follows": likely_manual_follows[:25],
            "likely_manual_or_untracked_replies": likely_manual_replies[:25],
            "recent_campaign_follow_events": history.get("follow_events", [])[-10:],
            "recent_campaign_reply_events": history.get("reply_events", [])[-10:],
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
