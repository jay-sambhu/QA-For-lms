"""
SSRF guard for scan targets.

The API validators only look at the literal hostname, so a public DNS name
that resolves to 127.0.0.1 / 10.x / 169.254.169.254 (e.g. ``127.0.0.1.nip.io``)
or a redirect to a literal internal IP would still be fetched by the server's
browser. These helpers close those gaps. Set ALLOW_LOCAL_TARGETS=true to
disable them for local development.
"""

import ipaddress
import os
import socket
from typing import Optional
from urllib.parse import urlparse

BLOCKED_HOSTS = {"169.254.169.254", "metadata.google.internal", "metadata.google"}
BLOCKED_SUFFIXES = ("localhost", "local", "internal", "intranet")


def local_targets_allowed() -> bool:
    return os.environ.get("ALLOW_LOCAL_TARGETS", "").lower() == "true"


def _ip_is_private(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str.split("%", 1)[0])
    except ValueError:
        return False
    if getattr(addr, "ipv4_mapped", None):
        addr = addr.ipv4_mapped
    return (
        addr.is_loopback
        or addr.is_private
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def is_blocked_host(host: Optional[str]) -> bool:
    """Cheap check on a literal hostname / IP; no DNS lookup."""
    host = (host or "").lower().strip("[]").rstrip(".")
    if not host:
        return True
    if host in BLOCKED_HOSTS:
        return True
    if any(host == s or host.endswith("." + s) for s in BLOCKED_SUFFIXES):
        return True
    return _ip_is_private(host)


def url_targets_private_network(url: str) -> Optional[str]:
    """
    Return a reason string if ``url`` points at a private / reserved address
    (after DNS resolution), else None. DNS failures are not treated as
    blocked: the crawl will simply fail to load the page.
    """
    host = (urlparse(url).hostname or "").lower()
    if is_blocked_host(host):
        return f"{host or url!r} is a private or reserved address"
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError, OSError):
        return None
    for info in infos:
        ip = info[4][0]
        if _ip_is_private(ip):
            return f"{host} resolves to private address {ip}"
    return None
