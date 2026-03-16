from src.services.request_ip import resolve_client_ip


def test_resolve_client_ip_uses_forwarded_header_from_trusted_proxy():
    client_ip = resolve_client_ip(
        {"x-forwarded-for": "203.0.113.10, 172.18.0.5", "x-real-ip": "203.0.113.10"},
        "172.18.0.5",
        trust_proxy_headers=True,
        trusted_proxy_cidrs=("172.16.0.0/12",),
    )
    assert client_ip == "203.0.113.10"


def test_resolve_client_ip_ignores_proxy_headers_from_untrusted_peer():
    client_ip = resolve_client_ip(
        {"x-forwarded-for": "203.0.113.10", "x-real-ip": "203.0.113.10"},
        "198.51.100.20",
        trust_proxy_headers=True,
        trusted_proxy_cidrs=("172.16.0.0/12",),
    )
    assert client_ip == "198.51.100.20"


def test_resolve_client_ip_uses_real_ip_when_forwarded_for_invalid():
    client_ip = resolve_client_ip(
        {"x-forwarded-for": "not-an-ip", "x-real-ip": "203.0.113.22"},
        "172.18.0.5",
        trust_proxy_headers=True,
        trusted_proxy_cidrs=("172.16.0.0/12",),
    )
    assert client_ip == "203.0.113.22"


def test_resolve_client_ip_returns_socket_peer_when_proxy_headers_disabled():
    client_ip = resolve_client_ip(
        {"x-forwarded-for": "203.0.113.22", "x-real-ip": "203.0.113.22"},
        "172.18.0.5",
        trust_proxy_headers=False,
        trusted_proxy_cidrs=("172.16.0.0/12",),
    )
    assert client_ip == "172.18.0.5"
