"""Small helpers shared by the API routers (no FastAPI app, no models)."""

import logging
import re
import socket
import threading
import time
from datetime import timezone
from typing import Optional
from urllib.parse import urlparse

try:
    from config import settings
except ImportError:  # pragma: no cover - package-relative import
    from ..config import settings

logger = logging.getLogger("ai_qa_agent.api")


def iso_utc(value):
    """Serialize a DB timestamp with an explicit UTC offset.

    SQLite hands back naive datetimes; without the offset the browser parses
    the ISO string as local time and shows UTC clock values to the user.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def slugify(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "article"


def redis_reachable(timeout: float = 1.0) -> bool:
    """TCP probe of the configured Redis broker (no auth, no commands)."""
    redis_url = (settings.REDIS_URL or "").strip()
    if not redis_url:
        return False
    try:
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


_celery_probe_lock = threading.Lock()
_celery_probe = {"at": 0.0, "workers": None}


def celery_workers(force: bool = False) -> Optional[list]:
    """Names of Celery workers answering a ping, or None when the broker is
    down. Cached for QA_CELERY_PROBE_TTL_SECONDS: inspect().ping() broadcasts
    to every worker and waits the full timeout when none answer, which used
    to stall every scan submission."""
    ttl = max(0.0, float(settings.QA_CELERY_PROBE_TTL_SECONDS))
    with _celery_probe_lock:
        if not force and _celery_probe["at"] and time.monotonic() - _celery_probe["at"] < ttl:
            return _celery_probe["workers"]
        workers = None
        if redis_reachable(1.5):
            try:
                from worker.celery_app import celery_app
                replies = celery_app.control.inspect(timeout=1.0).ping() or {}
                workers = sorted(replies.keys())
            except Exception as error:
                logger.debug("Celery ping failed: %s", error)
                workers = None
        _celery_probe["at"] = time.monotonic()
        _celery_probe["workers"] = workers
        return workers


def reset_celery_probe() -> None:
    with _celery_probe_lock:
        _celery_probe["at"] = 0.0
        _celery_probe["workers"] = None


def can_use_celery() -> bool:
    return bool(celery_workers())


def validate_provider_endpoint(value: Optional[str], allow_local: Optional[bool] = None) -> Optional[str]:
    """Validate a user-supplied AI provider endpoint.

    The worker POSTs the prompt (and the user's key) to this URL, so it gets
    the same SSRF rules as scan targets: http(s) only, no credentials in the
    URL, no private / link-local / metadata hosts unless ALLOW_LOCAL_TARGETS.
    Raises ValueError with a user-facing message.
    """
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("endpoint must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise ValueError("endpoint must not embed credentials")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("endpoint must include a valid hostname")
    if allow_local is None:
        from security.url_guard import local_targets_allowed
        allow_local = local_targets_allowed()
    if not allow_local:
        from security.url_guard import is_blocked_host
        if is_blocked_host(host):
            raise ValueError("endpoint targets a private or reserved address")
    return value
