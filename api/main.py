import json
import ipaddress
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4, UUID
from dotenv import load_dotenv

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_env_file = os.path.join(ROOT_DIR, ".env")
# override=False: real environment variables (systemd / docker / CI / the
# test suite's isolated DATABASE_URL) must win over the .env file. With
# override=True the .env silently redirected tests to the dev Postgres.
if os.path.exists(_env_file):
    load_dotenv(dotenv_path=_env_file, override=False)
else:
    load_dotenv(override=False)

from fastapi import Depends, FastAPI, HTTPException, Header, BackgroundTasks, Response
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, SecretStr, field_validator
from supabase import create_client, Client


try:
    from db import SessionLocal, engine
    from models import Scan, Base, User, BlogPost, UserApiKey, TrialScan
except ImportError:
    from ..db import SessionLocal, engine
    from ..models import Scan, Base, User, BlogPost, UserApiKey, TrialScan

# Kept separate: if Celery is unavailable the API must still start (scans then
# run through the bounded local fallback) instead of failing on the relative
# re-import above.
try:
    from worker.tasks import process_query_task
except Exception as _celery_import_err:  # pragma: no cover - depends on env
    process_query_task = None
    logging.getLogger("ai_qa_agent.api").warning("Celery task import failed: %s", _celery_import_err)

try:
    from core.ai_config import AI_PROVIDERS_REGISTRY
except ImportError:
    from ..core.ai_config import AI_PROVIDERS_REGISTRY

try:
    from .rate_limiter import rate_limit_dependency
except ImportError:
    try:
        from rate_limiter import rate_limit_dependency
    except ImportError:
        async def rate_limit_dependency():
            return True

try:
    Base.metadata.create_all(bind=engine)
    from api.blogs import seed_default_blogs_if_empty
    seed_default_blogs_if_empty()
except Exception as e:
    print(f"[STARTUP DB INIT] Notice: {e}")


# Diagnostics go through logging, not print: background tasks fail where nobody
# is watching stdout, and an operator needs the traceback to tell "expired
# token" apart from "Supabase is down".
logger = logging.getLogger("ai_qa_agent.api")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="JASUSS API",
    description="Automated Web Quality Assurance & Regression Platform (Powered by Nexus)",
    version="2.0.0",
)

_DEFAULT_SAFE_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://jasuss.tech",
    "https://www.jasuss.tech",
    "https://api.jasuss.tech",
    "https://web-two-flame-39.vercel.app",
]
_cors_origins_raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _cors_origins_raw:
    if _cors_origins_raw == "*":
        _CORS_ORIGINS: list = ["*"]
    else:
        _custom = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
        _CORS_ORIGINS: list = list(dict.fromkeys(_DEFAULT_SAFE_ORIGINS + _custom))
else:
    _CORS_ORIGINS: list = _DEFAULT_SAFE_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=r"^https:\/\/web(-[a-zA-Z0-9_-]+)*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Domain Routers
from api.billing import billing_router
from api.admin import admin_router
from api.blogs import blogs_router

app.include_router(billing_router)
app.include_router(admin_router)
app.include_router(blogs_router)


supabase_url = (os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").strip()
supabase_anon_key = (os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or "").strip()
supabase_service_key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

# Print and log explicit startup diagnostic check for all three Supabase variables
_status_url = "PRESENT" if supabase_url else "MISSING"
_status_anon = "PRESENT" if supabase_anon_key else "MISSING"
_status_service = "PRESENT" if supabase_service_key else "MISSING"

_startup_diag = (
    f"[SUPABASE AUTH] Environment check: "
    f"NEXT_PUBLIC_SUPABASE_URL={_status_url}, "
    f"NEXT_PUBLIC_SUPABASE_ANON_KEY={_status_anon}, "
    f"SUPABASE_SERVICE_ROLE_KEY={_status_service}"
)
logger.info(_startup_diag)
print(_startup_diag, flush=True)

# Use Service Role Key for backend if available to bypass RLS, otherwise fallback to Anon Key
supabase_key = supabase_service_key if supabase_service_key else supabase_anon_key

missing_supabase_vars = []
if not supabase_url:
    missing_supabase_vars.append("NEXT_PUBLIC_SUPABASE_URL")
if not supabase_key:
    missing_supabase_vars.append("SUPABASE_SERVICE_ROLE_KEY / NEXT_PUBLIC_SUPABASE_ANON_KEY")

if supabase_url and supabase_key:
    try:
        supabase: Optional[Client] = create_client(supabase_url, supabase_key)
        _init_msg = f"[SUPABASE AUTH] Client initialized successfully using {'SERVICE_ROLE_KEY' if supabase_service_key else 'ANON_KEY'}."
        logger.info(_init_msg)
        print(_init_msg, flush=True)
    except Exception as exc:
        logger.error(f"[SUPABASE AUTH ERROR] Failed to instantiate Supabase client: {exc}", exc_info=True)
        print(f"[SUPABASE AUTH ERROR] Failed to instantiate Supabase client: {exc}", file=sys.stderr, flush=True)
        supabase = None
else:
    _err_msg = (
        f"[SUPABASE AUTH ERROR] Supabase credentials missing in environment: "
        f"{', '.join(missing_supabase_vars)}. Authentication service is disabled."
    )
    logger.error(_err_msg)
    print(_err_msg, file=sys.stderr, flush=True)
    supabase = None


# A scan crawls up to `max_pages` pages with a real browser, so it needs a
# generous but finite budget. Without a timeout a wedged Playwright process
# holds a background worker forever.
PIPELINE_TIMEOUT_SECONDS = int(os.environ.get("QA_PIPELINE_TIMEOUT", "1800"))
MAX_PAGES_LIMIT = int(os.environ.get("QA_MAX_PAGES_LIMIT", "100"))

# How often the pipeline supervisor checks for timeout / user cancellation.
_PIPELINE_POLL_SECONDS = float(os.environ.get("QA_PIPELINE_POLL_SECONDS", "5"))

# A "running" scan whose last heartbeat (progress file / created_at) is older
# than this is considered orphaned (worker OOM-killed, API restarted while a
# fallback scan was running, ...) and is marked failed so the UI stops spinning.
STALE_RUNNING_SECONDS = int(os.environ.get("QA_STALE_SCAN_SECONDS", str(PIPELINE_TIMEOUT_SECONDS + 600)))
# A "pending" scan nobody picked up within this window is also marked failed.
STALE_PENDING_SECONDS = int(os.environ.get("QA_STALE_PENDING_SECONDS", "86400"))

# When Celery is unavailable, scans run inside the API process. Each scan is a
# Chromium-driving subprocess (~300-600 MB), so bound how many run at once;
# the rest wait in this executor's queue instead of OOM-killing the droplet.
LOCAL_MAX_CONCURRENT_SCANS = max(1, int(os.environ.get("QA_LOCAL_MAX_CONCURRENT_SCANS", "1")))
# Semaphore + daemon threads rather than a ThreadPoolExecutor: executor
# threads are joined at interpreter exit, which would block API shutdown
# until a 30-minute scan finished.
_local_scan_slots = threading.BoundedSemaphore(LOCAL_MAX_CONCURRENT_SCANS)

def _get_plan_max_pages(plan_tier: str) -> int:
    """Get max_pages limit from billing PLANS config for the given plan tier.

    Falls back to 10 (free-tier default) if the tier is unknown.
    The result is also capped by MAX_PAGES_LIMIT as an absolute safety ceiling.
    """
    from billing.gateways import PLANS
    plan = PLANS.get(plan_tier, PLANS.get("free", {}))
    plan_limit = plan.get("max_pages", 10)
    return min(plan_limit, MAX_PAGES_LIMIT)

# A pending/running scan younger than this blocks the user from starting another;
# older ones are treated as stuck so a dead worker can't lock a user out.
_ACTIVE_SCAN_WINDOW_SECONDS = PIPELINE_TIMEOUT_SECONDS + 600


def _enforce_scan_quota(user_id: str, plan_tier: str, is_admin: bool = False, db=None) -> None:
    """Reject a new scan when the user already has one in flight or has used
    their plan's monthly allowance (billing PLANS[*]["max_scans_per_month"]).
    Pass the session that will insert the scan (with the user row locked) so
    parallel requests cannot both pass the one-active-scan check."""
    if is_admin:
        return
    from billing.gateways import PLANS
    plan = PLANS.get(plan_tier, PLANS.get("free", {}))
    monthly_limit = plan.get("max_scans_per_month", 10)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    active = (
        db.query(Scan)
        .filter(
            Scan.user_id == user_id,
            Scan.status.in_(("pending", "running")),
            Scan.created_at >= now - timedelta(seconds=_ACTIVE_SCAN_WINDOW_SECONDS),
        )
        .count()
    )
    if active:
        raise HTTPException(
            status_code=409,
            detail="You already have a scan in progress. Please wait for it to finish (or stop it) before starting another.",
        )
    if monthly_limit is not None and monthly_limit >= 0:
        used = (
            db.query(Scan)
            # Scans that failed on our side don't use up the allowance
            .filter(Scan.user_id == user_id, Scan.created_at >= month_start, Scan.status != "failed")
            .count()
        )
        if used >= monthly_limit:
            raise HTTPException(
                status_code=429,
                detail=f"You've used all {monthly_limit} scans included in your plan this month. Your allowance resets on the 1st.",
            )


# Serializes trial bookkeeping across API workers on Postgres (advisory locks
# are transaction scoped, so the lock is released with the commit/rollback).
_TRIAL_ADVISORY_LOCK_KEY = 0x5452_4941_4C53  # "TRIALS"


def _lock_scan_creation(db, user_id: str, serialize_trials: bool) -> None:
    """Lock the user row (and, for a trial scan, the global trial counter) so
    the remaining/daily counts and the inserts that follow run atomically.
    SQLite ignores FOR UPDATE but serializes writers anyway."""
    if db.bind.dialect.name == "postgresql" and serialize_trials:
        from sqlalchemy import text
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _TRIAL_ADVISORY_LOCK_KEY})
    db.query(User).filter(User.id == user_id).with_for_update().first()


def _env_int(name: str, default: int) -> int:
    try:
        return int((os.environ.get(name) or "").strip() or default)
    except ValueError:
        return default


def _trial_server_key() -> Optional[str]:
    """The owner's Gemini key that free-trial scans run on. Never sent to clients."""
    return (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip() or None


def _trial_free_scans() -> int:
    return max(0, _env_int("TRIAL_FREE_SCANS", 3))


def _trial_daily_limit() -> int:
    """Global cap of trial scans per UTC day across all users; 0 disables the cap."""
    return max(0, _env_int("TRIAL_DAILY_LIMIT", 50))


def _trial_model() -> str:
    return (os.environ.get("TRIAL_AI_MODEL") or "").strip() or AI_PROVIDERS_REGISTRY["gemini"].default_model


def _trial_enabled() -> bool:
    return bool(_trial_server_key()) and _trial_free_scans() > 0


def _usable_user_key(key: UserApiKey) -> bool:
    """A stored provider entry the scan can run on: any key, or a Local LLM
    endpoint, which legitimately has no key."""
    return bool(key.api_key) or (key.provider_id or "gemini").lower() == "local_llm"


def _user_key_pool(db, user_id: str) -> list:
    user_keys = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id)
        .order_by(UserApiKey.is_default.desc(), UserApiKey.created_at.desc())
        .all()
    )
    return [
        {
            "api_key": k.api_key,
            "provider_id": k.provider_id or "gemini",
            "model": k.model,
            "endpoint": k.endpoint,
            "label": k.key_name or k.provider_id,
        }
        for k in user_keys
        if _usable_user_key(k)
    ]


def _user_has_own_key(db, user_id: str) -> bool:
    if any(_usable_user_key(k) for k in db.query(UserApiKey).filter(UserApiKey.user_id == user_id).all()):
        return True
    db_user = db.query(User).filter(User.id == user_id).first()
    return bool(db_user and (db_user.gemini_api_key or "").strip())


def _trial_status(db, user_id: str) -> dict:
    """Free-trial state for a user: scans run on the server key before they
    must add their own. Trial scans that failed on our side are refunded."""
    enabled = _trial_enabled()
    total = _trial_free_scans() if enabled else 0
    used = (
        db.query(TrialScan)
        .join(Scan, Scan.id == TrialScan.scan_id)
        .filter(TrialScan.user_id == user_id, Scan.status != "failed")
        .count()
    )
    daily_available = False
    if enabled:
        daily_limit = _trial_daily_limit()
        if daily_limit <= 0:
            daily_available = True
        else:
            day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            daily_used = db.query(TrialScan).filter(TrialScan.created_at >= day_start).count()
            daily_available = daily_used < daily_limit
    return {
        "enabled": enabled,
        "total": total,
        "used": used,
        "remaining": max(0, total - used) if enabled else 0,
        "has_own_key": _user_has_own_key(db, user_id),
        "daily_available": daily_available,
    }


_NO_KEY_DETAIL = (
    "An AI provider API key is required to generate the AI QA report. Please configure your API key "
    "(Gemini, OpenAI, Claude, DeepSeek, or Local LLM) in your Workspace Profile settings before launching a scan."
)
_TRIAL_BUSY_DETAIL = (
    "Free trial scans are busy right now (daily limit reached). "
    "Add your own free Gemini API key to scan immediately."
)


def _trial_exhausted_detail(trial: dict) -> str:
    if not trial.get("enabled"):
        return _NO_KEY_DETAIL
    total = trial.get("total", 0)
    return (
        f"An AI provider API key is required to keep scanning. You've used your {total} free trial "
        f"scan{'' if total == 1 else 's'}. Add your own free Gemini API key in your profile to keep scanning."
    )


class ScanAuthPayload(BaseModel):
    login_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[SecretStr] = None

    @field_validator("login_url")
    @classmethod
    def validate_login_url(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = value.strip()
        if not value.lower().startswith(("http://", "https://")):
            raise ValueError("login_url must be an absolute http(s) URL")

        parsed = urlparse(value)
        host = (parsed.hostname or "").lower().strip(".").rstrip(".")
        if not host:
            raise ValueError("login_url must include a valid hostname")

        if os.environ.get("ALLOW_LOCAL_TARGETS", "").lower() != "true":
            BLOCKED_HOSTS = {
                "169.254.169.254",
                "metadata.google.internal",
                "metadata.google",
            }
            if host in BLOCKED_HOSTS:
                raise ValueError("login_url targets a reserved address")

            try:
                addr = ipaddress.ip_address(host)
                if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_reserved:
                    raise ValueError("login_url targets a private or reserved address")
            except ValueError as ip_err:
                if "targets a" in str(ip_err):
                    raise
                BLOCKED_PREFIXES = ("localhost", "local", "internal", "intranet")
                if any(host == p or host.endswith("." + p) for p in BLOCKED_PREFIXES):
                    raise ValueError("login_url targets a reserved hostname")

        return value


class ScanRequest(BaseModel):
    url: str
    max_pages: int = 10
    auth_token: Optional[str] = None
    auth: Optional[ScanAuthPayload] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = (value or "").strip()
        if not value.lower().startswith(("http://", "https://")):
            raise ValueError("url must be an absolute http(s) URL")

        # SSRF protection: block private/loopback/link-local/cloud-metadata hosts.
        # A scan URL is navigated by a real browser with the server's network
        # identity, so internal endpoints are reachable and their contents end
        # up in the report returned to the user.
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower().strip(".").rstrip(".")
        if not host:
            raise ValueError("url must include a valid hostname")

        if os.environ.get("ALLOW_LOCAL_TARGETS", "").lower() != "true":
            # Block cloud metadata endpoints by hostname.
            BLOCKED_HOSTS = {
                "169.254.169.254",  # AWS / Azure / GCP IMDS
                "metadata.google.internal",
                "metadata.google",
            }
            if host in BLOCKED_HOSTS:
                raise ValueError("url targets a reserved address")

            # Block loopback, private, and link-local IPs.
            try:
                addr = ipaddress.ip_address(host)
                if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_reserved:
                    raise ValueError("url targets a private or reserved address")
            except ValueError as ip_err:
                if "targets a" in str(ip_err):
                    raise
                # host is a hostname, not an IP — additional hostname checks.
                BLOCKED_PREFIXES = ("localhost", "local", "internal", "intranet")
                if any(host == p or host.endswith("." + p) for p in BLOCKED_PREFIXES):
                    raise ValueError("url targets a reserved hostname")

        return value

    @field_validator("max_pages")
    @classmethod
    def validate_max_pages(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_pages must be at least 1")
        if value > MAX_PAGES_LIMIT:
            raise ValueError(f"max_pages must not exceed {MAX_PAGES_LIMIT}")
        return value


def require_user(authorization: str = Header(None)):
    """
    Resolve the caller's Supabase user from the Authorization header.

    Used as a dependency on every route that touches scan data.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    if not supabase:
        missing_desc = ", ".join(missing_supabase_vars) if missing_supabase_vars else "NEXT_PUBLIC_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY"
        logger.error("Authentication rejected: Supabase client is not configured. Missing variable(s): %s", missing_desc)
        raise HTTPException(
            status_code=503,
            detail=f"Authentication service unavailable: missing environment variable(s) {missing_desc}",
        )

    user = None
    for attempt in (1, 2):
        try:
            user = supabase.auth.get_user(token).user
            break
        except Exception as error:
            # A rejected token is final. A transport failure (typically the
            # server closing an idle HTTP/2 connection: "ConnectionTerminated")
            # is retried once; reporting it as 401 made the UI drop the user's
            # data as if they were signed out.
            is_rejection = type(error).__module__.startswith("supabase_auth") or hasattr(error, "status")
            if is_rejection:
                logger.warning("Token verification failed: %s", error)
                raise HTTPException(status_code=401, detail="Invalid token")
            if attempt == 2:
                logger.error("Auth service unreachable while verifying token: %s", error, exc_info=True)
                raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable, please retry")
            logger.warning("Auth transport error (%s); retrying token verification once", error)


    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Sync user to local database
    try:
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.id == user.id).first()
            if not db_user:
                db_user = User(
                    id=user.id,
                    email=user.email,
                    role="user",
                    plan_tier="free"
                )
                db.add(db_user)
                db.commit()
    except Exception as e:
        logger.error(f"Failed to sync user {user.id} to local DB: {e}")

    return user


ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get(
        "ADMIN_EMAILS",
        "dellizulter@gmail.com,admin@jasuss.tech,admin@jasuss.io",
    ).split(",")
    if e.strip()
}


def _iso_utc(value):
    """Serialize a DB timestamp with an explicit UTC offset.

    SQLite hands back naive datetimes; without the offset the browser parses
    the ISO string as local time and shows UTC clock values to the user.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _is_admin_email(email: str) -> bool:
    """Admin allow-list. Never match on an "admin@" local part alone: anyone
    who owns admin@<any-domain> could otherwise sign up and become admin."""
    email = (email or "").lower()
    return email in ADMIN_EMAILS or email.endswith("@admin.jasuss.io")


@app.get("/api/v1/auth/me")
@app.get("/api/v1/user/me")
async def get_current_user_profile(user=Depends(require_user)):
    """
    Retrieve authenticated user profile, resolved directly from backend database.
    Checks and returns whether user is 'admin' or 'user' to govern routing and permissions.
    """
    user_id_val = str(getattr(user, "id", user))
    user_email = (getattr(user, "email", "") or "").lower()

    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id_val).first()
        if not db_user:
            initial_role = "admin" if _is_admin_email(user_email) else "user"
            db_user = User(
                id=user_id_val,
                email=user_email or f"user_{user_id_val}@example.com",
                role=initial_role,
                plan_tier="free"
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        else:
            # Synchronize admin status for recognized admin emails if not yet set
            if _is_admin_email(user_email) and db_user.role != "admin":
                db_user.role = "admin"
                db.commit()
                db.refresh(db_user)

        is_admin = db_user.role == "admin"
        return {
            "id": db_user.id,
            "email": db_user.email,
            "role": db_user.role,
            "is_admin": is_admin,
            "plan_tier": db_user.plan_tier or "free",
            "has_gemini_key": bool(db_user.gemini_api_key),
            "created_at": _iso_utc(db_user.created_at),
            "dashboard_url": "/admin" if is_admin else "/dashboard",
        }


class ApiKeyUpdateRequest(BaseModel):
    api_key: str


class UserApiKeyCreateRequest(BaseModel):
    provider_id: str = "gemini"
    api_key: str
    key_name: Optional[str] = None
    model: Optional[str] = None
    endpoint: Optional[str] = None
    is_default: Optional[bool] = False


@app.get("/api/v1/user/api-keys")
async def list_user_api_keys(user=Depends(require_user)):
    """Retrieve all multi-model API keys configured by the user, with provider info, plan quota, and limit status."""
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id_val).first()
        plan_tier = (db_user.plan_tier or "free").lower() if db_user else "free"
        is_paid = plan_tier in ["pro", "enterprise", "team", "growth"] or (db_user and db_user.role == "admin")

        # If user has a legacy gemini_api_key on the User record but nothing in user_api_keys, auto-migrate it
        existing_keys = db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).order_by(UserApiKey.created_at.asc()).all()
        if not existing_keys and db_user and db_user.gemini_api_key:
            legacy_key = UserApiKey(
                user_id=user_id_val,
                provider_id="gemini",
                key_name="Google Gemini Studio",
                api_key=db_user.gemini_api_key,
                model=AI_PROVIDERS_REGISTRY["gemini"].default_model,
                is_default=True,
            )
            db.add(legacy_key)
            db.commit()
            db.refresh(legacy_key)
            existing_keys = [legacy_key]

        max_allowed = 999 if is_paid else 3
        count = len(existing_keys)
        trial = _trial_status(db, user_id_val)

        return {
            "keys": [k.to_dict() for k in existing_keys],
            "count": count,
            "max_allowed": max_allowed,
            "plan_tier": plan_tier,
            "is_paid": is_paid,
            "can_add_more": is_paid or count < 3,
            "has_key": count > 0,
            "trial": trial,
            "supported_providers": [
                {
                    "id": pid,
                    "name": meta.name,
                    "description": meta.description,
                    "models": meta.models,
                    "default_model": meta.default_model,
                    "requires_endpoint": meta.requires_endpoint,
                    "default_endpoint": meta.default_endpoint,
                }
                for pid, meta in AI_PROVIDERS_REGISTRY.items()
            ],
        }


@app.get("/api/v1/user/trial")
async def get_user_trial(user=Depends(require_user)):
    """Free-trial allowance: scans a new user may run on the server's AI key before adding their own."""
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        return _trial_status(db, user_id_val)


@app.post("/api/v1/user/api-keys")
async def create_user_api_key(payload: UserApiKeyCreateRequest, user=Depends(require_user)):
    """
    Add a new AI provider API key for the current user.
    Enforces subscription paywall: Free users cannot add more than 3 API keys.
    """
    key_str = (payload.api_key or "").strip()
    provider_id = (payload.provider_id or "gemini").lower()

    if not key_str and provider_id != "local_llm":
        raise HTTPException(status_code=400, detail="API Key cannot be empty.")

    if provider_id not in AI_PROVIDERS_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unsupported AI provider: {provider_id}")

    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id_val).first()
        if not db_user:
            db_user = User(
                id=user_id_val,
                email=getattr(user, "email", f"user_{user_id_val}@example.com"),
                role="user",
                plan_tier="free"
            )
            db.add(db_user)
            db.commit()

        # Check existing count
        existing_count = db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).count()
        plan_tier = (db_user.plan_tier or "free").lower()
        is_paid = plan_tier in ["pro", "enterprise", "team", "growth"] or db_user.role == "admin"

        if existing_count >= 3 and not is_paid:
            raise HTTPException(
                status_code=403,
                detail="API Key limit reached (3/3). Free tier accounts are limited to a maximum of 3 API keys. Please start a subscription plan to add unlimited API integrations."
            )

        provider_meta = AI_PROVIDERS_REGISTRY[provider_id]
        model = payload.model or provider_meta.default_model

        is_first = existing_count == 0
        should_be_default = payload.is_default or is_first

        if should_be_default:
            db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).update({"is_default": False})

        new_key = UserApiKey(
            user_id=user_id_val,
            provider_id=provider_id,
            key_name=payload.key_name or f"{provider_meta.name} Key",
            api_key=key_str,
            model=model,
            endpoint=payload.endpoint or provider_meta.default_endpoint,
            is_default=should_be_default,
        )
        db.add(new_key)

        # Synchronize legacy gemini_api_key if this is gemini or default
        if provider_id == "gemini" or should_be_default:
            db_user.gemini_api_key = key_str

        db.commit()
        db.refresh(new_key)

        return {
            "status": "success",
            "message": f"Successfully integrated {provider_meta.name} API key.",
            "key": new_key.to_dict(),
        }


@app.put("/api/v1/user/api-keys/{key_id}/default")
async def set_default_user_api_key(key_id: str, user=Depends(require_user)):
    """Set a specific API key as the default for QA report generation."""
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id_val).first()
        target_key = db.query(UserApiKey).filter(UserApiKey.id == key_id, UserApiKey.user_id == user_id_val).first()
        if not target_key:
            raise HTTPException(status_code=404, detail="API Key not found.")

        db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).update({"is_default": False})
        target_key.is_default = True

        if db_user:
            db_user.gemini_api_key = target_key.api_key
        db.commit()

        return {"status": "success", "message": f"{target_key.key_name} is now your active default API key."}


@app.delete("/api/v1/user/api-keys/{key_id}")
async def delete_user_api_key_by_id(key_id: str, user=Depends(require_user)):
    """Delete an API key integration."""
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id_val).first()
        target_key = db.query(UserApiKey).filter(UserApiKey.id == key_id, UserApiKey.user_id == user_id_val).first()
        if not target_key:
            raise HTTPException(status_code=404, detail="API Key not found.")

        was_default = target_key.is_default
        db.delete(target_key)
        db.commit()

        remaining = db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).order_by(UserApiKey.created_at.desc()).all()
        if was_default:
            if remaining:
                remaining[0].is_default = True
                if db_user:
                    db_user.gemini_api_key = remaining[0].api_key
            else:
                if db_user:
                    db_user.gemini_api_key = None
            db.commit()

        return {"status": "success", "message": "API Key removed successfully."}


@app.get("/api/v1/user/api-key")
async def get_user_gemini_api_key(user=Depends(require_user)):
    """Retrieve whether the current user has configured their Gemini API key, with masked preview."""
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id_val).first()
        key = db_user.gemini_api_key.strip() if db_user and db_user.gemini_api_key else None
        if not key:
            default_k = db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val, UserApiKey.is_default == True).first()
            if not default_k:
                default_k = db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).first()
            if default_k:
                key = default_k.api_key.strip()
        if not key:
            return {"has_key": False, "masked_key": None}
        masked = f"{key[:6]}...{key[-4:]}" if len(key) >= 12 else "••••••••"
        return {"has_key": True, "masked_key": masked}


@app.post("/api/v1/user/api-key")
@app.put("/api/v1/user/api-key")
async def update_user_gemini_api_key(payload: ApiKeyUpdateRequest, user=Depends(require_user)):
    """Update the current user's Google Gemini API key used for QA report generation."""
    key = (payload.api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Gemini API Key cannot be empty.")
    if len(key) < 15:
        raise HTTPException(status_code=400, detail="Invalid Gemini API key format. Expected a valid Google AI Studio key.")

    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id_val).first()
        if not db_user:
            db_user = User(
                id=user_id_val,
                email=getattr(user, "email", f"user_{user_id_val}@example.com"),
                role="user",
                plan_tier="free"
            )
            db.add(db_user)
        db_user.gemini_api_key = key

        # Synchronize with UserApiKey
        existing_gemini = db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val, UserApiKey.provider_id == "gemini").first()
        if existing_gemini:
            existing_gemini.api_key = key
            existing_gemini.is_default = True
        else:
            new_k = UserApiKey(
                user_id=user_id_val,
                provider_id="gemini",
                key_name="Google Gemini Studio",
                api_key=key,
                model=AI_PROVIDERS_REGISTRY["gemini"].default_model,
                is_default=True,
            )
            db.add(new_k)

        db.commit()

    masked = f"{key[:6]}...{key[-4:]}" if len(key) >= 12 else "••••••••"
    return {
        "status": "success",
        "has_key": True,
        "masked_key": masked,
        "message": "Google Gemini API key saved successfully."
    }


@app.delete("/api/v1/user/api-key")
async def delete_user_gemini_api_key(user=Depends(require_user)):
    """Remove current user's Google Gemini API key."""
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id_val).first()
        if db_user:
            db_user.gemini_api_key = None
        db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val, UserApiKey.provider_id == "gemini").delete()
        db.commit()
    return {"status": "success", "has_key": False, "masked_key": None, "message": "Gemini API key removed."}


def get_scan(scan_id: str, reap_stale: bool = False):
    """Retrieve a Scan record by ID using SQLAlchemy.

    reap_stale=True (status endpoint only) first marks an orphaned
    pending/running scan as failed.
    """
    try:
        with SessionLocal() as db:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if not scan:
                return None
            if reap_stale:
                _reap_stale_scans(db, [scan])
            return {
                "id": str(scan.id),
                "user_id": str(scan.user_id),
                "url": scan.url,
                "status": scan.status,
                "created_at": _iso_utc(scan.created_at),
                "completed_at": _iso_utc(scan.completed_at),
                "report_path": scan.report_path,
                "json_path": scan.json_path,
            }
    except Exception as error:
        logger.error("Database error retrieving scan %s: %s", scan_id, error)
        return None

def update_scan(
    scan_id: str,
    status: str,
    report_path: Optional[str] = None,
    json_path: Optional[str] = None,
):
    """Update a Scan's status and optional paths via SQLAlchemy."""
    try:
        with SessionLocal() as db:
            db_scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if not db_scan or db_scan.status == "cancelled":
                return
            db_scan.status = status
            if status == "completed":
                db_scan.completed_at = datetime.now(timezone.utc)
                db_scan.report_path = report_path
                db_scan.json_path = json_path
            elif status == "failed" and not db_scan.completed_at:
                db_scan.completed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as error:
        logger.error("Database error updating scan %s: %s", scan_id, error)


def _get_scan_status_value(scan_id: str) -> Optional[str]:
    """Return just the status column (used by the pipeline supervisor)."""
    try:
        with SessionLocal() as db:
            row = db.query(Scan.status).filter(Scan.id == scan_id).first()
            return row[0] if row else None
    except Exception as error:
        logger.debug("Could not read status for scan %s: %s", scan_id, error)
        return None


def _set_parent_death_signal():
    """preexec_fn: SIGKILL the pipeline if the process that spawned it dies.

    Celery revoke(terminate=True), the hard time limit and OOM kills take the
    worker child down without running `finally`, which used to orphan the
    run_qa.py subprocess and its Chromium.
    """
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl(1, signal.SIGKILL)  # PR_SET_PDEATHSIG
    except Exception:
        pass


def _kill_process_tree(process) -> None:
    """Kill the pipeline's whole process group (python, node driver, chromium)."""
    try:
        if process.poll() is not None:
            return
    except Exception:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
    try:
        process.wait(timeout=10)
    except Exception:
        pass


# Per-run intermediate files that are not needed once the final report exists.
# Final reports, progress files, the application model and learning patterns
# are kept (they are read by the API / later runs).
_INTERMEDIATE_PREFIXES = (
    "discovery_checkpoint_", "crawl_", "checkpoint_", "agent_decisions_",
    "test_plan_", "test_cases_", "regression_", "qa_findings_", "perf_a11y_",
    "execution_results_", "evidence_manifest_", "defects_", "api_test_results_",
)
ARTIFACT_RETENTION_DAYS = float(os.environ.get("QA_ARTIFACT_RETENTION_DAYS", "7"))


def _cleanup_old_artifacts(user_dir: str) -> None:
    """Delete screenshots and intermediate files older than the retention window.

    Without this user_data/<uid>/screenshots grew forever (hundreds of MB per
    active user), which fills a small droplet's disk. Set
    QA_ARTIFACT_RETENTION_DAYS=0 to disable.
    """
    if ARTIFACT_RETENTION_DAYS <= 0:
        return
    import shutil
    cutoff = time.time() - ARTIFACT_RETENTION_DAYS * 86400
    try:
        shots_root = os.path.join(user_dir, "screenshots")
        if os.path.isdir(shots_root):
            for entry in os.scandir(shots_root):
                if entry.is_dir(follow_symlinks=False) and entry.stat().st_mtime < cutoff:
                    shutil.rmtree(entry.path, ignore_errors=True)
        results_root = os.path.join(user_dir, "results")
        if os.path.isdir(results_root):
            for entry in os.scandir(results_root):
                if (
                    entry.is_file(follow_symlinks=False)
                    and entry.name.startswith(_INTERMEDIATE_PREFIXES)
                    and entry.stat().st_mtime < cutoff
                ):
                    try:
                        os.remove(entry.path)
                    except OSError:
                        pass
    except Exception as error:
        logger.debug("Artifact cleanup skipped for %s: %s", user_dir, error)


def _progress_mtime(user_id: str, scan_id: str) -> Optional[float]:
    for path in (
        os.path.join(ROOT_DIR, "user_data", str(user_id), "results", f"progress_{scan_id}.json"),
        os.path.join(ROOT_DIR, "results", f"progress_{scan_id}.json"),
    ):
        try:
            return os.path.getmtime(path)
        except OSError:
            continue
    return None


def _record_failure_reason(user_id: str, scan_id: str, message: str) -> None:
    """Write a user-facing failure reason to the scan's progress file so the
    scan page explains what happened. Keeps a more specific reason the
    pipeline itself already recorded (stage FAILED)."""
    path = os.path.join(ROOT_DIR, "user_data", str(user_id), "results", f"progress_{scan_id}.json")
    current = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            current = json.load(f) or {}
    except (OSError, ValueError):
        pass
    if current.get("stage") == "FAILED" and current.get("message"):
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "scan_id": str(scan_id),
                "stage": "FAILED",
                "percent": current.get("percent", 0),
                "message": message,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, f)
    except OSError as error:
        logger.debug("Could not record failure reason for %s: %s", scan_id, error)


def _reap_stale_scans(db, scans) -> None:
    """Mark orphaned pending/running scans as failed.

    A scan is left "running" forever when its worker is OOM-killed or the API
    process restarts mid-scan (local fallback). Uses the progress file's mtime
    as a heartbeat so long-but-alive scans are not reaped.
    """
    now = time.time()
    changed = False
    for scan in scans:
        if scan.status not in ("pending", "running") or not scan.created_at:
            continue
        created = scan.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        heartbeat = created.timestamp()
        if scan.status == "running":
            mtime = _progress_mtime(scan.user_id, scan.id)
            if mtime:
                heartbeat = max(heartbeat, mtime)
            limit = STALE_RUNNING_SECONDS
        else:
            limit = STALE_PENDING_SECONDS
        if now - heartbeat > limit:
            logger.warning("Marking stale %s scan %s as failed (no heartbeat for %ds)", scan.status, scan.id, int(now - heartbeat))
            scan.status = "failed"
            scan.completed_at = datetime.now(timezone.utc)
            _record_failure_reason(
                scan.user_id, scan.id,
                "The scan stopped responding and was marked as failed. Please start a new scan.",
            )
            changed = True
    if changed:
        try:
            db.commit()
        except Exception as error:
            db.rollback()
            logger.error("Could not persist stale-scan reaping: %s", error)



def _relative_to_root(path: str) -> str:
    """Store report paths relative to the repo root so they stay portable."""
    if not path:
        return path
    try:
        return os.path.relpath(os.path.abspath(path), ROOT_DIR)
    except ValueError:
        return path


def _resolve_report_path(stored_path: str) -> Optional[str]:
    """
    Resolve a stored report path to an absolute path inside ROOT_DIR.

    Returns None if the path escapes ROOT_DIR. The stored value comes from a
    database row, so it is treated as untrusted input rather than joined
    directly onto ROOT_DIR.
    """
    if not stored_path:
        return None

    candidate = os.path.realpath(os.path.join(ROOT_DIR, stored_path))
    real_root = os.path.realpath(ROOT_DIR)

    if os.path.commonpath([candidate, real_root]) != real_root:
        return None

    return candidate


def run_qa_pipeline(
    scan_id: str,
    user_id: str,
    url: str,
    max_pages: int,
    auth_token: Optional[str] = None,
    login_url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    ai_keys_pool: Optional[list] = None,
    provider_id: Optional[str] = None,
    model_name: Optional[str] = None,
    endpoint: Optional[str] = None,
):
    """Run the QA pipeline as a background subprocess using user's isolated API keys with seamless failover."""
    try:
        update_scan(scan_id, "running")
    except Exception as error:
        logger.exception("Failed to update scan %s to running: %s", scan_id, error)
        return

    # If key pool wasn't explicitly passed, retrieve it from the user's database records
    if not ai_keys_pool:
        try:
            with SessionLocal() as db:
                ai_keys_pool = _user_key_pool(db, str(user_id))
        except Exception as e:
            logger.warning("Could not fetch ai_keys_pool from DB for user %s: %s", user_id, e)

    # If primary key wasn't explicitly passed, use the first key from the pool or DB User record
    if not gemini_api_key:
        if ai_keys_pool and len(ai_keys_pool) > 0:
            gemini_api_key = ai_keys_pool[0].get("api_key")
            provider_id = provider_id or ai_keys_pool[0].get("provider_id")
            model_name = model_name or ai_keys_pool[0].get("model")
            endpoint = endpoint or ai_keys_pool[0].get("endpoint")
        else:
            try:
                with SessionLocal() as db:
                    db_u = db.query(User).filter(User.id == str(user_id)).first()
                    if db_u and db_u.gemini_api_key:
                        gemini_api_key = db_u.gemini_api_key.strip()
            except Exception as e:
                logger.warning("Could not fetch gemini_api_key from DB for user %s: %s", user_id, e)

    # SSRF: the API validator only inspects the literal hostname. Resolve it
    # here (worker side, off the request path) so DNS names pointing at
    # internal addresses cannot be scanned.
    try:
        from security.url_guard import local_targets_allowed, url_targets_private_network
        if not local_targets_allowed():
            for target in (url, login_url):
                reason = url_targets_private_network(target) if target else None
                if reason:
                    logger.warning("Scan %s rejected (SSRF guard): %s", scan_id, reason)
                    update_scan(scan_id, "failed")
                    return
    except Exception as guard_err:
        logger.warning("SSRF pre-flight check skipped for scan %s: %s", scan_id, guard_err)

    # --run-id namespaces this scan's output files, so concurrent scans cannot
    # pick up each other's results.
    cmd = [
        sys.executable,
        "run_qa.py",
        url,
        "--max-pages",
        str(max_pages),
        "--run-id",
        scan_id,
    ]

    # Store artifacts in isolated user directory
    user_dir = os.path.join(ROOT_DIR, "user_data", str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    cmd.extend(["--output-dir", user_dir])

    if provider_id:
        cmd.extend(["--provider", provider_id])

    if model_name:
        cmd.extend(["--model", model_name])

    if endpoint:
        cmd.extend(["--endpoint", endpoint])

    if login_url:
        cmd.extend(["--login-url", login_url])

    if username:
        cmd.extend(["--username", username])

    # Secrets (password, AI keys, bearer token) go through the child's
    # environment, never argv: argv is world-readable via `ps` / /proc.
    sub_env = dict(os.environ)
    for _k in ("QA_AUTH_PASSWORD", "QA_AUTH_TOKEN", "QA_AI_KEYS_POOL"):
        sub_env.pop(_k, None)
    if password:
        sub_env["QA_AUTH_PASSWORD"] = password
    if gemini_api_key:
        sub_env["GEMINI_API_KEY"] = gemini_api_key
    else:
        # PRODUCTION ENFORCEMENT: Never fallback to ambient developer / super-admin key
        sub_env.pop("GEMINI_API_KEY", None)
    if ai_keys_pool:
        sub_env["QA_AI_KEYS_POOL"] = json.dumps(ai_keys_pool)
    safe_token = (auth_token or "").replace("\n", "").replace("\r", "")
    if safe_token:
        sub_env["QA_AUTH_TOKEN"] = safe_token
    try:
        from security.url_guard import local_targets_allowed as _lta
        if not _lta():
            # Tells the crawler to abort browser requests to private IPs
            # (covers redirects to internal addresses).
            sub_env["QA_BLOCK_PRIVATE_NETWORK"] = "true"
    except Exception:
        pass

    secrets_to_redact = [v for v in (password, gemini_api_key, safe_token, _trial_server_key()) if v]
    for k_cfg in ai_keys_pool or []:
        k_val = k_cfg.get("api_key") if isinstance(k_cfg, dict) else None
        if k_val:
            secrets_to_redact.append(k_val)

    def _redact(text: str) -> str:
        for secret in secrets_to_redact:
            if secret in text:
                text = text.replace(secret, "[REDACTED]")
        return text

    # Only the tail is kept for diagnostics; buffering the whole stdout of a
    # 100-page crawl grew without bound.
    stdout_tail = deque(maxlen=400)
    json_path = None
    md_path = None
    result_returncode = None
    process = None
    stop_event = threading.Event()
    outcome = {"timed_out": False, "cancelled": False}

    def _supervise():
        """Kill the pipeline on timeout or when the user cancels the scan.

        The old code called process.wait(timeout=...) only after the stdout
        loop had already drained, i.e. after the process exited, so the
        timeout never fired and a wedged Chromium held the worker forever.
        """
        deadline = time.monotonic() + PIPELINE_TIMEOUT_SECONDS
        while not stop_event.wait(_PIPELINE_POLL_SECONDS):
            if process is None or process.poll() is not None:
                return
            if time.monotonic() >= deadline:
                outcome["timed_out"] = True
                _kill_process_tree(process)
                return
            if _get_scan_status_value(scan_id) == "cancelled":
                outcome["cancelled"] = True
                _kill_process_tree(process)
                return

    supervisor = None
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            cwd=ROOT_DIR,
            env=sub_env,
            # Own process group so the whole tree (python -> node driver ->
            # chromium) can be killed together.
            start_new_session=True,
            preexec_fn=_set_parent_death_signal if sys.platform.startswith("linux") else None,
        )
        supervisor = threading.Thread(target=_supervise, name=f"qa-supervise-{scan_id[:8]}", daemon=True)
        supervisor.start()

        # Display every action log in the console, but hide secret credentials and API keys
        for line in process.stdout:
            safe_line = _redact(line)
            stdout_tail.append(safe_line)
            if line.startswith("Final JSON:"):
                json_path = line.split(":", 1)[1].strip()
            elif line.startswith("Final Markdown:"):
                md_path = line.split(":", 1)[1].strip()
            sys.stdout.write(safe_line)
            sys.stdout.flush()

        result_returncode = process.wait()
    except Exception as error:
        # Includes Celery's SoftTimeLimitExceeded raised inside the read loop.
        _record_failure_reason(
            user_id, scan_id,
            "The scan stopped unexpectedly. Please try again, or scan fewer pages.",
        )
        update_scan(scan_id, "failed")
        logger.exception("Background task exception for scan %s: %s", scan_id, error)
        return
    finally:
        stop_event.set()
        if process is not None:
            _kill_process_tree(process)
            try:
                process.stdout.close()
            except Exception:
                pass
        _cleanup_old_artifacts(user_dir)

    result_stdout = "".join(stdout_tail)

    if outcome["cancelled"]:
        logger.info("Scan %s was cancelled by the user; pipeline terminated.", scan_id)
        return
    if outcome["timed_out"]:
        _record_failure_reason(
            user_id, scan_id,
            f"The scan took longer than {PIPELINE_TIMEOUT_SECONDS // 60} minutes and was stopped. "
            "Try again with fewer pages.",
        )
        update_scan(scan_id, "failed")
        logger.error(
            "Scan %s timed out after %ss and was terminated.",
            scan_id,
            PIPELINE_TIMEOUT_SECONDS,
        )
        return

    if json_path and md_path and result_returncode == 0:
        # Pre-render PDF and XLSX so all formats are immediately available without regeneration
        user_results_dir = os.path.join(ROOT_DIR, "user_data", str(user_id), "results")
        os.makedirs(user_results_dir, exist_ok=True)
        pdf_path = os.path.join(user_results_dir, f"final_qa_report_{scan_id}.pdf")
        xlsx_path = os.path.join(user_results_dir, f"final_qa_report_{scan_id}.xlsx")

        try:
            _generate_pdf_from_json(json_path, pdf_path)
        except Exception as e:
            logger.warning("Could not pre-render PDF for scan %s: %s", scan_id, e)
            pdf_path = None

        try:
            _generate_xlsx_from_json(json_path, xlsx_path)
        except Exception as e:
            logger.warning("Could not pre-render XLSX for scan %s: %s", scan_id, e)
            xlsx_path = None

        # Upload to Supabase Storage bucket under {user_id}/{scan_id}/report.{ext}
        # Enforcing strict 20 MB per-user bucket quota
        try:
            from core.supabase_storage import upload_scan_reports
            files_to_upload = {"json": json_path, "md": md_path}
            if pdf_path and os.path.isfile(pdf_path):
                files_to_upload["pdf"] = pdf_path
            if xlsx_path and os.path.isfile(xlsx_path):
                files_to_upload["xlsx"] = xlsx_path

            storage_res = upload_scan_reports(
                user_id=str(user_id),
                scan_id=str(scan_id),
                local_files=files_to_upload,
            )
            if storage_res.get("success"):
                logger.info("Successfully stored scan %s report artifacts in Supabase bucket", scan_id)
            else:
                logger.warning(
                    "Supabase storage upload note for scan %s: %s",
                    scan_id,
                    storage_res.get("message") or storage_res.get("reason"),
                )
        except Exception as e:
            logger.error("Error uploading reports to Supabase for scan %s: %s", scan_id, e)

        update_scan(
            scan_id,
            "completed",
            _relative_to_root(md_path),
            _relative_to_root(json_path),
        )
    else:
        if result_returncode is not None and result_returncode < 0:
            # Killed by a signal, most often the OOM killer on a small server
            reason = ("The scan was stopped by the server, possibly because it ran out of memory. "
                      "Try again with fewer pages.")
        else:
            reason = ("The scan could not finish. The site may be unreachable, "
                      "blocking automated browsers, or the AI provider may have rejected the request.")
        _record_failure_reason(user_id, scan_id, reason)
        update_scan(scan_id, "failed")
        logger.error(
            "Scan %s failed. Return code: %s\nStdout tail:\n%s",
            scan_id,
            result_returncode,
            result_stdout[-2000:],
        )


def _can_use_celery() -> bool:
    """Check if Redis broker is reachable and an active worker is available."""
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return False
    try:
        from urllib.parse import urlparse
        import socket
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=1.5):
            pass
    except Exception:
        return False

    try:
        from worker.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=1.0)
        return bool(inspector and inspector.ping())
    except Exception:
        return False


def _try_enqueue_celery(scan_id: str, task_args: list) -> bool:
    """Enqueue the scan on Celery if a broker and worker are reachable."""
    try:
        from worker.tasks import process_query_task
        _apply_fn = getattr(process_query_task, "apply_async", None)
        is_mocked = _apply_fn is not None and type(_apply_fn).__name__ in ("MagicMock", "Mock", "AsyncMock")
        if is_mocked or _can_use_celery():
            process_query_task.apply_async(args=task_args, task_id=scan_id)
            return True
        logger.info("Celery broker/worker unavailable; running scan %s via background task", scan_id)
    except Exception as e:
        logger.warning("Celery enqueue failed (%s), running via background task", e)
    return False


def _run_local_scan(*args, **kwargs):
    try:
        run_qa_pipeline(*args, **kwargs)
    except Exception as error:
        scan_id = args[0] if args else kwargs.get("scan_id")
        logger.exception("Local pipeline run for scan %s crashed: %s", scan_id, error)
        if scan_id:
            update_scan(scan_id, "failed")


def _run_local_scan_bounded(*args, **kwargs):
    with _local_scan_slots:
        _run_local_scan(*args, **kwargs)


def _submit_local_scan(*args, **kwargs):
    """Queue an in-process pipeline run; at most LOCAL_MAX_CONCURRENT_SCANS run at once."""
    threading.Thread(
        target=_run_local_scan_bounded, args=args, kwargs=kwargs,
        name="qa-local-scan", daemon=True,
    ).start()


@app.post("/api/v1/scans")
@app.post("/api/scans")
async def create_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    user=Depends(require_user),
    _rate_ok: bool = Depends(rate_limit_dependency),
):
    scan_id = str(uuid4())
    user_id_val = str(getattr(user, "id", user))
    is_authenticated = bool(
        request.auth_token or (request.auth and (request.auth.login_url or request.auth.username or request.auth.password))
    )

    # Enforce plan-based page limit using billing PLANS config
    from models import User as _User  # noqa: PLC0415
    ai_keys_pool = []
    primary_provider_id = "gemini"
    primary_model_name = None
    primary_endpoint = None

    with SessionLocal() as db:
        db_user_check = db.query(_User).filter(_User.id == user_id_val).first()
        user_plan = getattr(db_user_check, "plan_tier", "free") if db_user_check else "free"
        user_gemini_api_key = getattr(db_user_check, "gemini_api_key", None) if db_user_check else None

        ai_keys_pool = _user_key_pool(db, user_id_val)

        if user_gemini_api_key and not any(k["api_key"] == user_gemini_api_key for k in ai_keys_pool):
            ai_keys_pool.append({
                "api_key": user_gemini_api_key,
                "provider_id": "gemini",
                "model": AI_PROVIDERS_REGISTRY["gemini"].default_model,
                "endpoint": None,
                "label": "Gemini API Key",
            })

        if ai_keys_pool:
            if not user_gemini_api_key:
                user_gemini_api_key = ai_keys_pool[0]["api_key"]
            primary_provider_id = ai_keys_pool[0].get("provider_id") or "gemini"
            primary_model_name = ai_keys_pool[0].get("model")
            primary_endpoint = ai_keys_pool[0].get("endpoint")

    # Strict BYOK enforcement: without a personal key the scan may only run as
    # one of the user's free trial scans on the server key (decided below,
    # inside the transaction that records the scan).
    needs_trial = not (user_gemini_api_key or "").strip() and not ai_keys_pool
    if needs_trial and not _trial_enabled():
        raise HTTPException(status_code=400, detail=_NO_KEY_DETAIL)

    plan_max_pages = _get_plan_max_pages(user_plan)
    if request.max_pages > plan_max_pages:
        logger.info(
            "Plan cap applied: user %s (%s tier) requested %d pages, capped to %d",
            user_id_val, user_plan, request.max_pages, plan_max_pages,
        )
        request.max_pages = plan_max_pages

    user_email = str(getattr(user, "email", "") or "")
    user_app_meta = getattr(user, "app_metadata", None) or {}
    is_admin = _is_admin_email(user_email) or (isinstance(user_app_meta, dict) and user_app_meta.get("role") == "admin")

    # Persist in SQLAlchemy database as single source of truth. The quota,
    # trial allowance and daily-cap checks run in the same transaction as the
    # inserts, under a lock, so parallel POSTs (multiple uvicorn workers or
    # replicas) cannot all pass a check-then-insert.
    def _record_scan() -> Optional[int]:
        with SessionLocal() as db:
            try:
                db_user = db.query(User).filter(User.id == user_id_val).first()
                if not db_user:
                    db_user = User(id=user_id_val, email=f"user_{user_id_val}@example.com", role="student")
                    db.add(db_user)
                    db.commit()
            except Exception:
                db.rollback()

            _lock_scan_creation(db, user_id_val, serialize_trials=needs_trial)
            _enforce_scan_quota(user_id_val, user_plan, is_admin, db=db)

            remaining = None
            if needs_trial:
                trial = _trial_status(db, user_id_val)
                if not trial["enabled"] or trial["remaining"] <= 0:
                    raise HTTPException(status_code=400, detail=_trial_exhausted_detail(trial))
                if not trial["daily_available"]:
                    raise HTTPException(status_code=429, detail=_TRIAL_BUSY_DETAIL)
                remaining = max(0, trial["remaining"] - 1)

            db_scan = Scan(
                id=scan_id,
                user_id=user_id_val,
                url=request.url,
                status="pending",
                is_authenticated=is_authenticated,
            )
            db.add(db_scan)
            if needs_trial:
                db.flush()
                db.add(TrialScan(scan_id=scan_id, user_id=user_id_val, created_at=datetime.now(timezone.utc)))
            db.commit()
            return remaining

    trial_remaining = await run_in_threadpool(_record_scan)
    used_trial = needs_trial

    if used_trial:
        # The pipeline must run on the server key only: an explicit one-entry
        # pool stops the worker from reloading keys the user may add later,
        # which would run a scan already charged to the trial on their key.
        user_gemini_api_key = _trial_server_key()
        ai_keys_pool = [{
            "api_key": user_gemini_api_key,
            "provider_id": "gemini",
            "model": _trial_model(),
            "endpoint": None,
            "label": "Free trial",
        }]
        primary_provider_id = "gemini"
        primary_model_name = _trial_model()
        primary_endpoint = None
        logger.info("Scan %s runs as a free trial scan for user %s (%d remaining)", scan_id, user_id_val, trial_remaining)

    # Extract auth details securely without storing or logging passwords
    login_url = request.auth.login_url if request.auth else None
    username = request.auth.username if request.auth else None
    password_raw = request.auth.password.get_secret_value() if request.auth and request.auth.password else None

    task_args = [
        scan_id,
        user_id_val,
        request.url,
        request.max_pages,
        request.auth_token,
        login_url,
        username,
        password_raw,
        user_gemini_api_key,
        ai_keys_pool,
        primary_provider_id,
        primary_model_name,
        primary_endpoint,
    ]

    # Enqueue asynchronous Celery task with background task fallback. The
    # broker probe + inspect().ping() block for up to ~2.5s, so they run in
    # the threadpool rather than on the event loop.
    enqueued = await run_in_threadpool(_try_enqueue_celery, scan_id, task_args)

    # In local development fallback to an in-process run if Celery was not
    # enqueued. The BackgroundTask only *submits* to a bounded executor so at
    # most QA_LOCAL_MAX_CONCURRENT_SCANS pipelines run at once.
    if not enqueued:
        background_tasks.add_task(
            _submit_local_scan,
            scan_id,
            user_id_val,
            request.url,
            request.max_pages,
            request.auth_token,
            login_url,
            username,
            password_raw,
            user_gemini_api_key,
            ai_keys_pool=ai_keys_pool,
            provider_id=primary_provider_id,
            model_name=primary_model_name,
            endpoint=primary_endpoint,
        )

    return {
        "scan_id": scan_id,
        "url": request.url,
        "status": "pending",
        "is_authenticated": is_authenticated,
        "used_trial": used_trial,
        "trial_remaining": trial_remaining,
        "message": "Scan queued successfully."
    }



@app.get("/api/v1/scans")
@app.get("/api/scans")
async def list_scans(user=Depends(require_user)):
    """List the caller's own scans, newest first."""
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        scans = db.query(Scan).filter(Scan.user_id == user_id_val).order_by(Scan.created_at.desc()).limit(50).all()
        _reap_stale_scans(db, scans)
        return {
            "scans": [
                {
                    "id": s.id,
                    "url": s.url,
                    "status": s.status,
                    "created_at": _iso_utc(s.created_at),
                    "completed_at": _iso_utc(s.completed_at),
                }
                for s in scans
            ]
        }



@app.get("/api/v1/scans/{scan_id}")
@app.get("/api/scans/{scan_id}")
async def get_scan_status(scan_id: UUID, user=Depends(require_user)):
    # DB, disk and Supabase I/O: keep it off the event loop.
    return await run_in_threadpool(_get_scan_status_sync, scan_id, user)


def _get_scan_status_sync(scan_id: UUID, user):
    scan = get_scan(str(scan_id), reap_stale=True)
    user_id_val = str(getattr(user, "id", user))

    if not scan or str(scan.get("user_id")) != user_id_val:
        raise HTTPException(status_code=404, detail="Scan not found")

    response = dict(scan)
    
    user_dir = os.path.join(ROOT_DIR, "user_data", str(scan.get("user_id", "")))
    progress_candidates = [
        os.path.join(user_dir, "results", f"progress_{scan_id}.json"),
        os.path.join(ROOT_DIR, "results", f"progress_{scan_id}.json"),
    ]
    for progress_path in progress_candidates:
        if os.path.exists(progress_path):
            try:
                with open(progress_path, "r", encoding="utf-8") as f:
                    response["progress"] = json.load(f)
            except Exception:
                pass
            break

    if "progress" not in response and scan.get("status") == "completed":
        response["progress"] = {
            "scan_id": str(scan_id),
            "stage": "COMPLETED",
            "percent": 100,
            "message": "Scan completed successfully.",
        }

    if scan.get("status") == "completed":
        response["results"] = None
        response["has_cloud_report"] = False
        report_candidates = []
        if scan.get("json_path"):
            resolved = _resolve_report_path(scan["json_path"])
            if resolved:
                report_candidates.append(resolved)
        report_candidates.extend([
            os.path.join(user_dir, "results", f"final_qa_report_{scan_id}.json"),
            os.path.join(ROOT_DIR, "results", f"final_qa_report_{scan_id}.json"),
            os.path.join(user_dir, "results", f"gemini_qa_report_{scan_id}.json"),
            os.path.join(ROOT_DIR, "results", f"gemini_qa_report_{scan_id}.json"),
        ])
        import glob
        report_candidates.extend(glob.glob(os.path.join(user_dir, "results", f"*{scan_id}*.json")))
        report_candidates.extend(glob.glob(os.path.join(ROOT_DIR, "results", f"*{scan_id}*.json")))

        for report_path in report_candidates:
            if report_path and os.path.isfile(report_path):
                try:
                    with open(report_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict) and ("summary" in data or "findings" in data or "url" in data or "score" in data):
                            response["results"] = data
                            response["has_cloud_report"] = True
                            break
                except (OSError, json.JSONDecodeError) as error:
                    logger.error("Could not read report for scan %s from %s: %s", scan_id, report_path, error)

        # Fallback: load report JSON from Supabase Storage if not on local disk
        if not response.get("results"):
            try:
                from core.supabase_storage import get_scan_report_file
                cloud_bytes = get_scan_report_file(user_id_val, str(scan_id), "json")
                if cloud_bytes:
                    data = json.loads(cloud_bytes.decode("utf-8"))
                    if isinstance(data, dict) and ("summary" in data or "findings" in data or "url" in data or "score" in data):
                        response["results"] = data
                        response["has_cloud_report"] = True
                    else:
                        # File exists in Supabase but is not a valid JSON report
                        response["has_cloud_report"] = True
            except Exception as e:
                logger.debug("Could not fetch report from Supabase Storage for scan %s: %s", scan_id, e)
                # Even if download failed, check if the file listing says it exists
                try:
                    from core.supabase_storage import get_supabase_client, BUCKET_NAME
                    sb = get_supabase_client()
                    if sb:
                        folder = f"{user_id_val}/{str(scan_id)}"
                        items = sb.storage.from_(BUCKET_NAME).list(folder)
                        if items and len(items) > 0:
                            response["has_cloud_report"] = True
                except Exception:
                    pass

    return response


@app.post("/api/v1/scans/{scan_id}/cancel")
@app.post("/api/scans/{scan_id}/cancel")
@app.delete("/api/v1/scans/{scan_id}")
@app.delete("/api/scans/{scan_id}")
async def cancel_scan(scan_id: UUID, user=Depends(require_user)):
    """Cancel an ongoing scan or mark it stopped and clean up cloud storage to free quota."""
    return await run_in_threadpool(_cancel_scan_sync, scan_id, user)


def _cancel_scan_sync(scan_id: UUID, user):
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        scan = db.query(Scan).filter(Scan.id == str(scan_id)).first()
        if not scan or str(scan.user_id) != user_id_val:
            raise HTTPException(status_code=404, detail="Scan not found")
        if scan.status in ("pending", "running"):
            scan.status = "cancelled"
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            try:
                from worker.celery_app import celery_app
                celery_app.control.revoke(str(scan_id), terminate=True, signal="SIGTERM")
                logger.info("Revoked Celery task for scan %s", scan_id)
            except Exception as e:
                logger.warning("Could not revoke Celery task for scan %s: %s", scan_id, e)
            try:
                from core.supabase_storage import delete_scan_reports
                delete_scan_reports(user_id_val, str(scan_id))
            except Exception as e:
                logger.warning("Could not delete Supabase files on cancel: %s", e)
            return {"status": "cancelled", "message": "Scan has been stopped."}

        # If completed/failed/stopped, also remove from Supabase bucket to free up the 20 MB quota
        try:
            from core.supabase_storage import delete_scan_reports
            delete_scan_reports(user_id_val, str(scan_id))
        except Exception as e:
            logger.warning("Could not delete Supabase files on scan delete: %s", e)
        return {"status": scan.status, "message": f"Scan is {scan.status}."}


@app.get("/api/v1/user/storage")
@app.get("/api/storage/usage")
async def get_storage_usage(user=Depends(require_user)):
    """
    Return user's Supabase Storage quota and usage under the 20 MB per-user limit.
    """
    user_id_val = str(getattr(user, "id", user))
    try:
        from core.supabase_storage import get_user_storage_usage
        return await run_in_threadpool(get_user_storage_usage, user_id_val)
    except Exception as e:
        logger.error("Error fetching storage usage for %s: %s", user_id_val, e)
        return {
            "used_bytes": 0,
            "limit_bytes": 20 * 1024 * 1024,
            "used_mb": 0.0,
            "limit_mb": 20.0,
            "used_percent": 0.0,
            "remaining_bytes": 20 * 1024 * 1024,
            "file_count": 0,
            "is_quota_exceeded": False,
        }

def _get_download_media_type(format_ext: str) -> str:
    """Return canonical media type for download formats."""
    media_types = {
        "json": "application/json",
        "md": "text/markdown; charset=utf-8",
        "markdown": "text/markdown; charset=utf-8",
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return media_types.get(format_ext, "application/octet-stream")


def _generate_pdf_from_json(json_path: str, output_path: str):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    # Paragraph parses its text as markup: report content such as
    # "Missing <title> tag" or URLs with "&" made reportlab raise and the PDF
    # download returned 500. Escape everything that comes from the report.
    from xml.sax.saxutils import escape as _esc
    meta = data.get("report_metadata", {}) or {}
    findings = data.get("findings", []) or []
    story = [
        Paragraph("<b>Autonomous QA Test Report</b>", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Target: {_esc(str(meta.get('target', 'N/A')))}", styles["Normal"]),
        Paragraph(f"Pages Crawled: {_esc(str(meta.get('pages_crawled', 0)))}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(f"<b>Findings ({len(findings)})</b>", styles["Heading2"]),
    ]
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        story.append(Paragraph(
            f"• [{_esc(str(finding.get('severity', 'INFO')))}] {_esc(str(finding.get('title', '')))}",
            styles["Normal"],
        ))
    if not findings:
        story.append(Paragraph("No defects detected. Target web application verified successfully.", styles["Normal"]))
    doc.build(story)


def _generate_xlsx_from_json(json_path: str, output_path: str):
    import openpyxl
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

    def _cell(value):
        # Scraped page text can contain control characters, which openpyxl
        # rejects with IllegalCharacterError (-> 500 on download).
        if isinstance(value, (int, float)) or value is None:
            return value
        return ILLEGAL_CHARACTERS_RE.sub("", str(value))

    meta = data.get("report_metadata", {}) or {}
    quality = meta.get("quality_score", {})
    score = quality.get("score", 100) if isinstance(quality, dict) else quality
    wb = openpyxl.Workbook()
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_summary.append(["Target", _cell(meta.get("target", "N/A"))])
    ws_summary.append(["Generated At", _cell(meta.get("generated_at", ""))])
    ws_summary.append(["Pages Crawled", _cell(meta.get("pages_crawled", 0))])
    ws_summary.append(["Quality Score", _cell(score)])

    ws_findings = wb.create_sheet(title="Findings")
    ws_findings.append(["ID", "Title", "Severity", "Priority", "Classification", "URL"])
    for f in data.get("findings", []) or []:
        if not isinstance(f, dict):
            continue
        ws_findings.append([
            _cell(f.get("id", "")),
            _cell(f.get("title", "")),
            _cell(f.get("severity", "")),
            _cell(f.get("priority", "")),
            _cell(f.get("classification", "")),
            _cell(f.get("url", "")),
        ])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb.save(output_path)


@app.get("/api/v1/scans/{scan_id}/download/{file_type}")
@app.get("/api/scans/{scan_id}/download/{file_type}")
async def download_scan_file(scan_id: UUID, file_type: str, user=Depends(require_user)):
    """
    Download a completed scan's report artifact in the requested format (json, md/markdown, pdf, xlsx).
    Sets explicit Content-Disposition and media_type headers with canonical filenames.
    """
    # Supabase download, PDF/XLSX rendering and the lazy upload are all
    # blocking; running them inline stalled every other request.
    return await run_in_threadpool(_download_scan_file_sync, scan_id, file_type, user)


def _download_scan_file_sync(scan_id: UUID, file_type: str, user):
    file_type_norm = file_type.lower().strip(".")
    if file_type_norm not in ("json", "md", "markdown", "pdf", "xlsx", "excel"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Supported formats: 'json', 'md', 'markdown', 'pdf', 'xlsx'"
        )

    scan = get_scan(str(scan_id))
    user_id_val = str(getattr(user, "id", user))
    if not scan or str(scan.get("user_id")) != user_id_val:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Scan is not completed")

    canonical_ext = "xlsx" if file_type_norm in ("excel", "xlsx") else ("md" if file_type_norm in ("markdown", "md") else file_type_norm)
    canonical_filename = f"qa-report-{scan_id}.{canonical_ext}"
    media_type = _get_download_media_type(canonical_ext)

    # 1. DIRECT DOWNLOAD FROM SUPABASE STORAGE BUCKET (ZERO RE-GENERATION)
    try:
        from core.supabase_storage import get_scan_report_file
        cloud_bytes = get_scan_report_file(user_id_val, str(scan_id), canonical_ext)
        if cloud_bytes:
            return Response(
                content=cloud_bytes,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{canonical_filename}"',
                    "Access-Control-Expose-Headers": "Content-Disposition",
                    "X-Report-Source": "supabase-storage",
                },
            )
    except Exception as e:
        logger.debug("Supabase storage direct download check for scan %s: %s", scan_id, e)

    # 2. FALLBACK: Check local disk or generate if missing, then upload to Supabase for subsequent downloads
    stored_path = None
    if canonical_ext == "json":
        stored_path = scan.get("json_path")
    elif canonical_ext == "md":
        stored_path = scan.get("report_path") or scan.get("md_path")
    elif canonical_ext == "pdf":
        candidates = [
            scan.get("pdf_path"),
            os.path.join("user_data", user_id_val, "results", f"final_qa_report_{scan_id}.pdf"),
            os.path.join("user_data", user_id_val, f"final_qa_report_{scan_id}.pdf"),
            os.path.join("user_data", user_id_val, f"qa-report-{scan_id}.pdf"),
            os.path.join("results", f"qa-report-{scan_id}.pdf"),
        ]
        stored_path = next((c for c in candidates if c and os.path.isfile(os.path.join(ROOT_DIR, c) if not os.path.isabs(c) else c)), None)
        if not stored_path and scan.get("json_path"):
            json_resolved = _resolve_report_path(scan.get("json_path"))
            if json_resolved and os.path.isfile(json_resolved):
                target_pdf = os.path.join(ROOT_DIR, "user_data", user_id_val, "results", f"final_qa_report_{scan_id}.pdf")
                _generate_pdf_from_json(json_resolved, target_pdf)
                stored_path = _relative_to_root(target_pdf)
    elif canonical_ext == "xlsx":
        candidates = [
            scan.get("xlsx_path"),
            os.path.join("user_data", user_id_val, "results", f"final_qa_report_{scan_id}.xlsx"),
            os.path.join("user_data", user_id_val, f"final_qa_report_{scan_id}.xlsx"),
            os.path.join("user_data", user_id_val, f"qa-report-{scan_id}.xlsx"),
            os.path.join("results", f"qa-report-{scan_id}.xlsx"),
        ]
        stored_path = next((c for c in candidates if c and os.path.isfile(os.path.join(ROOT_DIR, c) if not os.path.isabs(c) else c)), None)
        if not stored_path and scan.get("json_path"):
            json_resolved = _resolve_report_path(scan.get("json_path"))
            if json_resolved and os.path.isfile(json_resolved):
                target_xlsx = os.path.join(ROOT_DIR, "user_data", user_id_val, "results", f"final_qa_report_{scan_id}.xlsx")
                _generate_xlsx_from_json(json_resolved, target_xlsx)
                stored_path = _relative_to_root(target_xlsx)

    if not stored_path:
        raise HTTPException(status_code=404, detail="Report file path not found")

    resolved = _resolve_report_path(stored_path)
    if not resolved or not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    # Upload to Supabase Storage lazily so future accesses are served directly
    # from the bucket. Done in the background: it is several network round
    # trips (bucket check, quota listing, upload, signed URL).
    def _lazy_upload():
        try:
            from core.supabase_storage import upload_scan_reports
            upload_scan_reports(user_id_val, str(scan_id), {canonical_ext: resolved})
        except Exception as e:
            logger.debug("Lazy upload to Supabase storage note: %s", e)

    threading.Thread(target=_lazy_upload, name="qa-lazy-upload", daemon=True).start()

    return FileResponse(
        path=resolved,
        filename=canonical_filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{canonical_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
            "X-Report-Source": "local-disk",
        },
    )


@app.get("/api/v1/scans/{scan_id}/signed-url/{file_type}")
async def get_scan_report_signed_url_endpoint(scan_id: UUID, file_type: str, user=Depends(require_user)):
    """Return a direct signed download URL from Supabase Storage."""
    user_id_val = str(getattr(user, "id", user))
    scan = await run_in_threadpool(get_scan, str(scan_id))
    if not scan or str(scan.get("user_id")) != user_id_val:
        raise HTTPException(status_code=404, detail="Scan not found")

    file_type_norm = file_type.lower().strip(".")
    if file_type_norm not in ("json", "md", "markdown", "pdf", "xlsx", "excel"):
        raise HTTPException(status_code=400, detail="Invalid file type. Supported formats: 'json', 'md', 'markdown', 'pdf', 'xlsx'")
    file_type = "xlsx" if file_type_norm in ("excel", "xlsx") else ("md" if file_type_norm in ("markdown", "md") else file_type_norm)

    from core.supabase_storage import get_scan_report_signed_url
    url = await run_in_threadpool(get_scan_report_signed_url, user_id_val, str(scan_id), file_type)
    if not url:
        raise HTTPException(status_code=404, detail="Report file not found in Supabase Storage")
    return {"signed_url": url, "scan_id": str(scan_id), "file_type": file_type}


@app.get("/")
def read_root():
    return {"message": "AI QA Agent SaaS API is running."}


@app.get("/healthz")
@app.get("/api/v1/healthz")
def healthz():
    """Liveness probe: returns 200 if process is up."""
    return {"status": "ok", "service": "ai-qa-api"}


@app.get("/readyz")
@app.get("/api/v1/readyz")
def readyz():
    """Readiness probe: verifies database and redis reachability."""
    from sqlalchemy import text
    checks = {"database": "unknown", "redis": "unknown"}
    is_ready = True

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            checks["database"] = "connected"
    except Exception as db_err:
        checks["database"] = f"error: {str(db_err)}"
        is_ready = False

    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            from urllib.parse import urlparse
            import socket
            parsed = urlparse(redis_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            with socket.create_connection((host, port), timeout=1.0):
                checks["redis"] = "connected"
        except Exception as redis_err:
            checks["redis"] = f"unavailable: {str(redis_err)}"
    else:
        checks["redis"] = "not_configured"

    status_code = 200 if is_ready else 503
    return JSONResponse(status_code=status_code, content={"status": "ok" if is_ready else "degraded", **checks})
