"""Trusted client IP resolution for reverse-proxied requests."""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable, Mapping
from functools import lru_cache


def _parse_ip(value: str | None):
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


@lru_cache(maxsize=32)
def _parse_network(cidr: str):
    return ipaddress.ip_network(cidr, strict=False)


def _trusted_networks(trusted_proxy_cidrs: Iterable[str]):
    networks = []
    for cidr in trusted_proxy_cidrs:
        try:
            networks.append(_parse_network(cidr))
        except ValueError:
            continue
    return tuple(networks)


def _is_trusted_proxy(remote_ip: str | None, trusted_proxy_cidrs: Iterable[str]) -> bool:
    remote = _parse_ip(remote_ip)
    if remote is None:
        return False
    return any(remote in network for network in _trusted_networks(tuple(trusted_proxy_cidrs)))


def _first_valid_forwarded_ip(value: str | None) -> str | None:
    if not value:
        return None
    for item in value.split(","):
        candidate = item.strip()
        if _parse_ip(candidate) is not None:
            return candidate
    return None


def resolve_client_ip(
    headers: Mapping[str, str] | None,
    client_host: str | None,
    *,
    trust_proxy_headers: bool,
    trusted_proxy_cidrs: Iterable[str],
) -> str:
    """Resolve the canonical client IP for a request.

    Proxy headers are honored only when the immediate peer is trusted.
    """
    headers = headers or {}

    if not trust_proxy_headers:
        return client_host or "unknown"

    if not _is_trusted_proxy(client_host, trusted_proxy_cidrs):
        return client_host or "unknown"

    forwarded_for = _first_valid_forwarded_ip(headers.get("x-forwarded-for"))
    if forwarded_for:
        return forwarded_for

    real_ip = headers.get("x-real-ip")
    if _parse_ip(real_ip) is not None:
        return real_ip.strip()

    return client_host or "unknown"
