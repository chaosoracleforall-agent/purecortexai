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


def _forwarded_ips(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    candidates: list[str] = []
    for item in value.split(","):
        candidate = item.strip()
        if _parse_ip(candidate) is not None:
            candidates.append(candidate)
    return tuple(candidates)


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

    trusted_networks = _trusted_networks(tuple(trusted_proxy_cidrs))
    forwarded_for = _forwarded_ips(headers.get("x-forwarded-for"))
    if forwarded_for:
        # Walk from right to left and return the first hop that is not itself a
        # trusted proxy. This blocks spoofed leftmost values while still working
        # for sanitized multi-proxy chains.
        for candidate in reversed(forwarded_for):
            parsed = _parse_ip(candidate)
            if parsed is None:
                continue
            if not any(parsed in network for network in trusted_networks):
                return candidate
        return forwarded_for[-1]

    real_ip = headers.get("x-real-ip")
    if _parse_ip(real_ip) is not None:
        return real_ip.strip()

    return client_host or "unknown"
