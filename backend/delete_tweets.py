from __future__ import annotations

import argparse
import re
import sys
from typing import Iterable

import tweepy
from google.cloud import secretmanager


PROJECT_ID = "purecortexai"
DEFAULT_PATTERN = r"\$?PRCX\b"


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


def iter_recent_tweets(
    client: tweepy.Client,
    *,
    user_id: int,
    limit: int,
    exclude_replies: bool,
    exclude_retweets: bool,
) -> Iterable[tweepy.Tweet]:
    fetched = 0
    pagination_token: str | None = None
    exclude: list[str] = []
    if exclude_replies:
        exclude.append("replies")
    if exclude_retweets:
        exclude.append("retweets")

    while fetched < limit:
        batch_size = min(100, limit - fetched)
        response = client.get_users_tweets(
            id=user_id,
            max_results=batch_size,
            pagination_token=pagination_token,
            tweet_fields=["created_at"],
            exclude=exclude or None,
            user_auth=True,
        )
        tweets = response.data or []
        if not tweets:
            break
        for tweet in tweets:
            yield tweet
            fetched += 1
        pagination_token = response.meta.get("next_token") if response.meta else None
        if not pagination_token:
            break


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete recent tweets from the authenticated account matching a pattern.",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="Case-insensitive regex used to match tweet text.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="How many recent tweets to scan (default: 100).",
    )
    parser.add_argument(
        "--include-replies",
        action="store_true",
        help="Include replies when scanning tweets.",
    )
    parser.add_argument(
        "--include-retweets",
        action="store_true",
        help="Include retweets when scanning tweets.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete matching tweets. Omit for dry-run.",
    )
    args = parser.parse_args()

    pattern = re.compile(args.pattern, re.IGNORECASE)
    client = build_twitter_client()
    me = client.get_me(user_auth=True)
    if not me or not me.data:
        raise RuntimeError("Unable to resolve the authenticated X account.")

    matches: list[tweepy.Tweet] = []
    for tweet in iter_recent_tweets(
        client,
        user_id=me.data.id,
        limit=args.limit,
        exclude_replies=not args.include_replies,
        exclude_retweets=not args.include_retweets,
    ):
        if pattern.search(tweet.text or ""):
            matches.append(tweet)

    if not matches:
        print("No matching tweets found.")
        return 0

    print(f"Authenticated account: @{me.data.username}")
    print(f"Matched {len(matches)} tweet(s) using pattern: {args.pattern}")
    for tweet in matches:
        preview = " ".join((tweet.text or "").split())
        print(f"- {tweet.id}: {preview[:220]}")

    if not args.execute:
        print("\nDry run only. Re-run with --execute to delete the matched tweets.")
        return 0

    for tweet in matches:
        response = client.delete_tweet(tweet.id, user_auth=True)
        if not response or not response.data or not response.data.get("deleted"):
            print(f"Failed to delete tweet {tweet.id}", file=sys.stderr)
            return 1
        print(f"Deleted tweet {tweet.id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
