"""Sliding-window rate limiting (Redis, in-memory fallback).

``make_rate_limiter(limit, scope)`` builds a FastAPI dependency:
- scope="user": keyed by the authenticated user id (requires a bearer token,
  resolved through ``require_user`` so the per-role limit applies);
- scope="ip": keyed by the client address (public routes, webhooks).
"""

import logging
import time
from collections import defaultdict
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request
import redis

try:
    from config import settings
    from api.deps import require_user
except ImportError:  # pragma: no cover - package-relative import
    from ..config import settings
    from .deps import require_user

logger = logging.getLogger("ai_qa_agent.rate_limiter")

# Shared Redis window when a broker is configured; otherwise the per-process
# in-memory window (single uvicorn worker, local development).
redis_url = (settings.REDIS_URL or "").strip()
redis_client = None
if redis_url:
    try:
        # socket_timeout too: without it a half-dead Redis blocks a request indefinitely.
        redis_client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
    except Exception:
        redis_client = None

# Requests per minute
STANDARD_LIMIT = settings.RATE_LIMIT_STANDARD
ELEVATED_LIMIT = settings.elevated_rate_limit
READ_LIMIT = settings.RATE_LIMIT_READ
PUBLIC_LIMIT = settings.RATE_LIMIT_PUBLIC
BURST_SECONDS = 60  # window

# In-memory sliding window fallback cache if Redis is unavailable
_memory_store: dict = defaultdict(list)
# Keys were never evicted, so every distinct IP/token ever seen stayed in
# memory for the life of the process. Sweep stale keys past this size.
_MEMORY_STORE_SWEEP_AT = settings.RATE_LIMIT_MEMORY_MAX_KEYS


def _sweep_memory_store(cutoff: float) -> None:
    for k in [k for k, v in _memory_store.items() if not v or v[-1] <= cutoff]:
        _memory_store.pop(k, None)


def reset_memory_store() -> None:
    _memory_store.clear()


def _is_elevated(user) -> bool:
    """Admins (identity-provider role) get the elevated allowance."""
    if user is None:
        return False
    app_meta = getattr(user, "app_metadata", None)
    if isinstance(app_meta, dict) and app_meta.get("role") == "admin":
        return True
    return str(getattr(user, "role", "") or "").lower() == "admin"


def get_user_limit(user, base_limit: Optional[int] = None) -> int:
    """Per-user allowance: elevated for admins, otherwise the route's base limit."""
    base = STANDARD_LIMIT if base_limit is None else base_limit
    if _is_elevated(user):
        return max(base, ELEVATED_LIMIT, base * 3)
    return base


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"


def _consume(key: str, limit: int) -> None:
    """Record one hit for ``key`` and raise 429 past ``limit`` per window."""
    now = time.time()
    used_redis = False

    if redis_client:
        try:
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, int(now - BURST_SECONDS))
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, BURST_SECONDS)
            _, count, _, _ = pipe.execute()
            used_redis = True
            if count >= limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
        except HTTPException:
            raise
        except (redis.RedisError, Exception) as err:
            logger.debug("Redis rate limiting unavailable (%s), falling back to in-memory store", err)
            used_redis = False

    if not used_redis:
        cutoff = now - BURST_SECONDS
        if len(_memory_store) >= _MEMORY_STORE_SWEEP_AT:
            _sweep_memory_store(cutoff)
        _memory_store[key] = [ts for ts in _memory_store[key] if ts > cutoff]
        _memory_store[key].append(now)
        if len(_memory_store[key]) > limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")


def make_rate_limiter(limit: int, scope: str = "user", name: str = "") -> Callable:
    """Build a dependency enforcing ``limit`` requests/minute.

    Sync on purpose: FastAPI runs it in the threadpool, so the blocking Redis
    round trip (up to the 1s timeout when Redis is down) never stalls the
    event loop. ``name`` separates buckets so a busy status poll does not
    use up the scan-creation allowance.
    """
    bucket = name or f"{scope}-{limit}"

    if scope == "user":
        def rate_limit_user(request: Request, user=Depends(require_user)) -> bool:
            key = f"rl:{bucket}:user:{getattr(user, 'id', user)}"
            _consume(key, get_user_limit(user, limit))
            return True
        return rate_limit_user

    def rate_limit_ip(request: Request) -> bool:
        _consume(f"rl:{bucket}:ip:{_client_ip(request)}", limit)
        return True
    return rate_limit_ip


# Route-level dependencies
rate_limit_dependency = make_rate_limiter(STANDARD_LIMIT, "user", "scan")
rate_limit_read = make_rate_limiter(READ_LIMIT, "user", "read")
rate_limit_public = make_rate_limiter(PUBLIC_LIMIT, "ip", "public")
