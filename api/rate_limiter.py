import os
import time
import logging
from collections import defaultdict
from fastapi import HTTPException, Request, Depends
import redis

logger = logging.getLogger("ai_qa_agent.rate_limiter")

# Initialize Redis client (singleton)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
except Exception:
    redis_client = None

# Token bucket parameters (defaults, can be overridden via env)
STANDARD_LIMIT = int(os.getenv("RATE_LIMIT_STANDARD", "20"))  # requests per minute for students
INSTRUCTOR_LIMIT = int(os.getenv("RATE_LIMIT_INSTRUCTOR", "60"))  # requests per minute for instructors/paid
BURST_SECONDS = 60  # period for rate limiting (1 minute)

# In-memory sliding window fallback cache if Redis is unavailable
_memory_store: dict = defaultdict(list)

def get_user_limit(user) -> int:
    """Determine per‑user rate limit based on role.
    Assumes Supabase user object may contain a `role` attribute or
    `app_metadata['role']`. Falls back to "student".
    """
    role = getattr(user, "role", None) or getattr(user, "app_metadata", {}).get("role") or "student"
    if str(role).lower() in {"instructor", "paid", "admin"}:
        return INSTRUCTOR_LIMIT
    return STANDARD_LIMIT

async def rate_limit_dependency(request: Request, user=Depends(lambda: None)):
    """FastAPI dependency that raises HTTP 429 when the request exceeds the
    allowed quota for the caller. Uses Redis if available, with graceful in-memory
    sliding window fallback if Redis is unavailable.
    """
    limit = get_user_limit(user)
    user_id = getattr(user, "id", None)
    if user_id:
        key = f"rl:user:{user_id}"
    else:
        auth_hdr = request.headers.get("Authorization", "")
        client_host = request.client.host if request.client else "127.0.0.1"
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ", 1)[1].strip()
            key = f"rl:token:{token[-16:]}"
        else:
            key = f"rl:ip:{client_host}"

    now = time.time()
    used_redis = False

    if redis_client:
        try:
            pipe = redis_client.pipeline()
            # Remove timestamps older than the window
            pipe.zremrangebyscore(key, 0, int(now - BURST_SECONDS))
            # Count remaining requests in the window
            pipe.zcard(key)
            # Add current request timestamp
            pipe.zadd(key, {str(now): now})
            # Ensure the key expires shortly after the window
            pipe.expire(key, BURST_SECONDS)
            _, count, _, _ = pipe.execute()
            used_redis = True
            if count > limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
        except HTTPException:
            raise
        except (redis.RedisError, Exception) as err:
            logger.debug("Redis rate limiting unavailable (%s), falling back to in-memory store", err)
            used_redis = False

    if not used_redis:
        cutoff = now - BURST_SECONDS
        _memory_store[key] = [ts for ts in _memory_store[key] if ts > cutoff]
        _memory_store[key].append(now)
        if len(_memory_store[key]) > limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

    return True

