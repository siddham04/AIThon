"""SSRF guards for server-side URL fetch (ingestion)."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",
    "metadata.google",
    "169.254.169.254",
})

_PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "100.64.0.0/10",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)


def _ip_blocked(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    for net in _PRIVATE_NETWORKS:
        if addr in net:
            return True
    return bool(
        getattr(addr, "is_private", False)
        or getattr(addr, "is_loopback", False)
        or getattr(addr, "is_link_local", False)
        or getattr(addr, "is_reserved", False)
    )


def _resolve_host_ips(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(
            hostname,
            None,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve host: {hostname}") from exc
    ips: list[str] = []
    for info in infos:
        ip = info[4][0]
        if ip not in ips:
            ips.append(ip)
    if not ips:
        raise ValueError(f"Cannot resolve host: {hostname}")
    return ips


def validate_public_http_url(url: str) -> str:
    """Return normalized URL or raise ValueError for disallowed targets."""
    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL is required")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are allowed")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise ValueError("URL must include a hostname")
    if host in _BLOCKED_HOSTNAMES:
        raise ValueError("That host is not allowed")
    if host.endswith(".local") or host.endswith(".internal"):
        raise ValueError("That host is not allowed")

    literal: ipaddress.IPv4Address | ipaddress.IPv6Address | None = None
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if _ip_blocked(literal):
            raise ValueError("That address is not allowed")
    else:
        for ip_str in _resolve_host_ips(host):
            addr = ipaddress.ip_address(ip_str)
            if _ip_blocked(addr):
                raise ValueError("URL resolves to a private or restricted address")

    port = parsed.port
    if port is not None and port not in (80, 443, 8080, 8443):
        raise ValueError("URL port is not allowed")

    return raw
