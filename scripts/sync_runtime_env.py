#!/usr/bin/env python3
"""Sync runtime environment values from Secret Manager into the VM .env file."""

from __future__ import annotations

import base64
import os
import secrets
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
RUNTIME_DIR = ROOT / ".runtime"
AUTHENTICATED_EMAILS_PATH = RUNTIME_DIR / "oauth2-proxy-authenticated-emails.txt"


def load_env(path: Path) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    original = path.read_text().splitlines()
    for line in original:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values, original


def write_env(path: Path, original_lines: list[str], values: dict[str, str]) -> None:
    output: list[str] = []
    seen: set[str] = set()

    for line in original_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key, _ = line.split("=", 1)
            if key in values:
                output.append(f"{key}={values[key]}")
                seen.add(key)
                continue
        output.append(line)

    if output and output[-1] != "":
        output.append("")

    for key, value in values.items():
        if key not in seen:
            output.append(f"{key}={value}")

    path.write_text("\n".join(output) + "\n")


def maybe_access_secret(project: str, name: str) -> str | None:
    try:
        return subprocess.check_output(
            [
                "gcloud",
                "secrets",
                "versions",
                "access",
                "latest",
                f"--secret={name}",
                f"--project={project}",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return None


def ensure_secret_backed_value(
    values: dict[str, str],
    *,
    key: str,
    project: str,
    secret_name: str,
) -> None:
    secret_value = maybe_access_secret(project, secret_name)
    if secret_value:
        values[key] = secret_value


def ensure_generated_value(values: dict[str, str], key: str, generator) -> None:
    if not values.get(key):
        values[key] = generator()


def main() -> int:
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"Missing {ENV_PATH}")

    values, original_lines = load_env(ENV_PATH)
    project = (
        os.getenv("PURECORTEX_GCP_PROJECT")
        or values.get("GCP_PROJECT_ID")
        or os.getenv("GCP_PROJECT_ID")
        or "purecortexai"
    )

    ensure_generated_value(values, "PURECORTEX_SIGNER_SHARED_TOKEN", lambda: secrets.token_urlsafe(48))
    ensure_generated_value(values, "PURECORTEX_INTERNAL_ADMIN_TOKEN", lambda: secrets.token_urlsafe(48))
    ensure_generated_value(values, "PURECORTEX_KEY_HMAC_SECRET", lambda: secrets.token_hex(32))
    ensure_generated_value(values, "POSTGRES_PASSWORD", lambda: secrets.token_urlsafe(32))

    values.setdefault("PURECORTEX_INTERNAL_BACKEND_URL", "http://backend:8000")
    values.setdefault("PURECORTEX_ADMIN_ALLOWED_EMAILS", "chaosoracleforall@gmail.com")
    values.setdefault("PURECORTEX_TRUST_PROXY_HEADERS", "1")
    values.setdefault(
        "PURECORTEX_TRUSTED_PROXY_CIDRS",
        "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
    )

    ensure_secret_backed_value(
        values,
        key="PURECORTEX_GOOGLE_OAUTH_CLIENT_ID",
        project=project,
        secret_name="PURECORTEX_GOOGLE_OAUTH_CLIENT_ID",
    )
    ensure_secret_backed_value(
        values,
        key="PURECORTEX_GOOGLE_OAUTH_CLIENT_SECRET",
        project=project,
        secret_name="PURECORTEX_GOOGLE_OAUTH_CLIENT_SECRET",
    )
    ensure_secret_backed_value(
        values,
        key="PURECORTEX_OAUTH2_PROXY_COOKIE_SECRET",
        project=project,
        secret_name="PURECORTEX_OAUTH2_PROXY_COOKIE_SECRET",
    )

    cloud_sql_connection_name = values.get("PURECORTEX_CLOUD_SQL_CONNECTION_NAME", "").strip()
    if cloud_sql_connection_name:
        app_password = maybe_access_secret(project, "PURECORTEX_CLOUDSQL_APP_PASSWORD")
        if not app_password:
            raise RuntimeError(
                "PURECORTEX_CLOUDSQL_APP_PASSWORD secret missing while Cloud SQL is configured"
            )
        values["PURECORTEX_DATABASE_URL"] = (
            f"postgresql://purecortex:{app_password}@127.0.0.1:5432/purecortex"
        )
    else:
        values.setdefault(
            "PURECORTEX_DATABASE_URL",
            f"postgresql://purecortex:{values['POSTGRES_PASSWORD']}@postgres:5432/purecortex",
        )

    if not values.get("PURECORTEX_OAUTH2_PROXY_COOKIE_SECRET"):
        values["PURECORTEX_OAUTH2_PROXY_COOKIE_SECRET"] = (
            base64.urlsafe_b64encode(os.urandom(32)).decode()
        )

    write_env(ENV_PATH, original_lines, values)
    RUNTIME_DIR.mkdir(exist_ok=True)
    authenticated_emails = [
        email.strip().lower()
        for email in values["PURECORTEX_ADMIN_ALLOWED_EMAILS"].split(",")
        if email.strip()
    ]
    AUTHENTICATED_EMAILS_PATH.write_text("\n".join(authenticated_emails) + "\n")
    print("runtime-env-synced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
