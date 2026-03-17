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


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    stripped = value.strip()
    if not stripped:
        return default
    try:
        return int(stripped)
    except ValueError:
        return default


def _as_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    stripped = value.strip()
    if not stripped:
        return default
    try:
        return float(stripped)
    except ValueError:
        return default


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
    recaptcha_site_key: str | None
    recaptcha_project_id: str
    recaptcha_min_score: float
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
        recaptcha_site_key=os.getenv("PURECORTEX_RECAPTCHA_SITE_KEY"),
        recaptcha_project_id=(
            os.getenv("PURECORTEX_RECAPTCHA_PROJECT_ID")
            or os.getenv("PURECORTEX_GCP_PROJECT")
            or os.getenv("GCP_PROJECT_ID")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or "purecortexai"
        ),
        recaptcha_min_score=max(
            min(_as_float(os.getenv("PURECORTEX_RECAPTCHA_MIN_SCORE"), 0.5), 1.0),
            0.0,
        ),
        developer_access_cooldown_seconds=max(
            _as_int(os.getenv("PURECORTEX_DEVELOPER_ACCESS_COOLDOWN_SECONDS"), 300),
            0,
        ),
    )
