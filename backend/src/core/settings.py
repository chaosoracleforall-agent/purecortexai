"""Central settings for enterprise access-control foundation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    cloud_sql_connection_name: str | None
    internal_admin_token: str | None
    internal_admin_allowed_cidrs: tuple[str, ...]
    key_hmac_secret: str | None
    admin_allowed_emails: tuple[str, ...]
    trust_proxy_headers: bool
    trusted_proxy_cidrs: tuple[str, ...]
    google_oauth_client_id: str | None
    google_oauth_client_secret: str | None
    oauth2_proxy_cookie_secret: str | None
    turnstile_site_key: str | None
    turnstile_secret_key: str | None
    developer_access_cooldown_seconds: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("PURECORTEX_DATABASE_URL"),
        cloud_sql_connection_name=os.getenv("PURECORTEX_CLOUD_SQL_CONNECTION_NAME"),
        internal_admin_token=os.getenv("PURECORTEX_INTERNAL_ADMIN_TOKEN"),
        internal_admin_allowed_cidrs=_split_csv(
            os.getenv(
                "PURECORTEX_INTERNAL_ADMIN_ALLOWED_CIDRS",
                "127.0.0.1/32,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,fc00::/7",
            )
        ),
        key_hmac_secret=os.getenv("PURECORTEX_KEY_HMAC_SECRET"),
        admin_allowed_emails=_split_csv(
            os.getenv("PURECORTEX_ADMIN_ALLOWED_EMAILS", "chaosoracleforall@gmail.com")
        ),
        trust_proxy_headers=_as_bool(os.getenv("PURECORTEX_TRUST_PROXY_HEADERS"), default=False),
        trusted_proxy_cidrs=_split_csv(
            os.getenv(
                "PURECORTEX_TRUSTED_PROXY_CIDRS",
                "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
            )
        ),
        google_oauth_client_id=os.getenv("PURECORTEX_GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=os.getenv("PURECORTEX_GOOGLE_OAUTH_CLIENT_SECRET"),
        oauth2_proxy_cookie_secret=os.getenv("PURECORTEX_OAUTH2_PROXY_COOKIE_SECRET"),
        turnstile_site_key=os.getenv("PURECORTEX_TURNSTILE_SITE_KEY"),
        turnstile_secret_key=os.getenv("PURECORTEX_TURNSTILE_SECRET_KEY"),
        developer_access_cooldown_seconds=max(
            int(os.getenv("PURECORTEX_DEVELOPER_ACCESS_COOLDOWN_SECONDS", "300")),
            0,
        ),
    )
