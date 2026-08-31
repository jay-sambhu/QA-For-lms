import os
import time
from fastapi import HTTPException, Request, Depends
import redis
from ..config import Settings

# Initialize Redis client (singleton)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(redis_url, decode_responses=True)

# Token bucket parameters (defaults, can be overridden via env)
STANDARD_LIMIT = int(os.getenv("RATE_LIMIT_STANDARD", "20"))  # requests per minute for students
INSTRUCTOR_LIMIT = int(os.getenv("RATE_LIMIT_INSTRUCTOR", "60"))  # requests per minute for instructors/paid
BURST_SECONDS = 60  # period for rate limiting (1 minute)

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
    allowed quota for the caller. Uses a Redis sorted set to store timestamps.
    """
    limit = get_user_limit(user)
    key = f"rl:{user.id}" if user else f"rl:ip:{request.client.host}"
    now = int(time.time())
    pipe = redis_client.pipeline()
    # Remove timestamps older than the window
    pipe.zremrangebyscore(key, 0, now - BURST_SECONDS)
    # Count remaining requests in the window
    pipe.zcard(key)
    # Add current request timestamp
    pipe.zadd(key, {str(now): now})
    # Ensure the key expires shortly after the window
    pipe.expire(key, BURST_SECONDS)
    _, count, _, _ = pipe.execute()
    if count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    return True
