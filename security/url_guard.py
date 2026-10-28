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
import re
import socket
import threading
from typing import Dict, Optional
from urllib.parse import urlparse

BLOCKED_HOSTS = {"169.254.169.254", "metadata.google.internal", "metadata.google"}
BLOCKED_SUFFIXES = ("localhost", "local", "internal", "intranet")

# Hostnames that are not a dotted name but still parse as an IPv4 address in
# Chromium: a bare decimal (2130706433), a hex literal (0x7f000001) or dotted
# segments with hex/octal parts (0x7f.0.0.1, 0177.0.0.1). ipaddress rejects
# these so they would otherwise slip past the private-range check.
_NUMERIC_SEGMENT = re.compile(r"^(?:0x[0-9a-f]+|\d+)$")

_RESOLVE_LOCK = threading.Lock()
_RESOLVE_CACHE: Dict[str, Optional[str]] = {}


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


def _is_numeric_encoding(host: str) -> bool:
    """True for IP literals written in a form ipaddress does not parse."""
    segments = host.split(".")
    if not all(_NUMERIC_SEGMENT.match(seg) for seg in segments if seg != ""):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        return True


def is_blocked_host(host: Optional[str]) -> bool:
    """Cheap check on a literal hostname / IP; no DNS lookup.

    Single-label hostnames (``api``, ``redis``, ``db``) are blocked: on the
    public internet they never resolve, inside a compose network they are the
    other containers.
    """
    host = (host or "").lower().strip("[]").rstrip(".")
    if not host:
        return True
    if host in BLOCKED_HOSTS:
        return True
    if any(host == s or host.endswith("." + s) for s in BLOCKED_SUFFIXES):
        return True
    if _ip_is_private(host):
        return True
    if _is_numeric_encoding(host):
        return True
    if ":" not in host and "." not in host:
        return True
    return False


def resolve_private_reason(host: Optional[str]) -> Optional[str]:
    """
    Return a reason string if ``host`` is a blocked literal or resolves (DNS)
    to a private / reserved address, else None. Results are memoised for the
    life of the process so a crawl pays one lookup per distinct host; DNS
    failures are not treated as blocked, the request simply fails to load.
    """
    host = (host or "").lower().strip("[]").rstrip(".")
    if is_blocked_host(host):
        return f"{host or 'empty host'} is a private or reserved address"
    with _RESOLVE_LOCK:
        if host in _RESOLVE_CACHE:
            return _RESOLVE_CACHE[host]
    reason = None
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError, OSError):
        infos = []
    for info in infos:
        ip = info[4][0]
        if _ip_is_private(ip):
            reason = f"{host} resolves to private address {ip}"
            break
    with _RESOLVE_LOCK:
        _RESOLVE_CACHE[host] = reason
    return reason


def clear_resolve_cache() -> None:
    with _RESOLVE_LOCK:
        _RESOLVE_CACHE.clear()


def url_targets_private_network(url: str) -> Optional[str]:
    """
    Return a reason string if ``url`` points at a private / reserved address
    (after DNS resolution), else None. DNS failures are not treated as
    blocked: the crawl will simply fail to load the page.
    """
    host = (urlparse(url).hostname or "").lower()
    return resolve_private_reason(host)
