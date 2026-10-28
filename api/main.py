import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4, UUID
from dotenv import load_dotenv

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_env_file = os.path.join(ROOT_DIR, ".env")
# override=False: real environment variables (systemd / docker / CI / the
# test suite's isolated DATABASE_URL) must win over the .env file.
if os.path.exists(_env_file):
    load_dotenv(dotenv_path=_env_file, override=False)
else:
    load_dotenv(override=False)

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, SecretStr, field_validator
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

try:
    from config import settings
    from db import SessionLocal, engine
    from models import Base, Scan, ScanSecret, TrialScan, User, UserApiKey
except ImportError:
    from ..config import settings
    from ..db import SessionLocal, engine
    from ..models import Base, Scan, ScanSecret, TrialScan, User, UserApiKey

from api.deps import (
    ADMIN_EMAILS,
    AuthUser,
    get_or_create_user,
    require_admin,
    require_user,
    resolve_is_admin,
    supabase,
)
from api.pipeline import (
    MAX_PAGES_LIMIT,
    PIPELINE_TIMEOUT_SECONDS,
    _get_scan_status_value,
    delete_scan_artifacts,
    generate_pdf_from_json,
    generate_xlsx_from_json,
    get_scan,
    progress_file_path,
    purge_orphaned_scan_secrets,
    reap_all_stale_scans,
    relative_to_root,
    resolve_report_path,
    run_qa_pipeline,
    store_scan_secret,
    trial_daily_limit,
    trial_enabled,
    trial_free_scans,
    update_scan,
    user_has_own_key,
    user_key_pool,
    user_results_dir,
    usable_user_key,
)
from api.rate_limiter import make_rate_limiter, rate_limit_dependency, rate_limit_read, STANDARD_LIMIT
from api.secrets import encrypt_plaintext_rows, encrypt_secret, mask_secret
from api.utils import can_use_celery, iso_utc, redis_reachable, validate_provider_endpoint

# Kept separate: if Celery is unavailable the API must still start (scans then
# run through the bounded local fallback) instead of failing on the import.
try:
    from worker.tasks import process_query_task
except Exception as _celery_import_err:  # pragma: no cover - depends on env
    process_query_task = None
    logging.getLogger("ai_qa_agent.api").warning("Celery task import failed: %s", _celery_import_err)

try:
    from core.ai_config import AI_PROVIDERS_REGISTRY
except ImportError:
    from ..core.ai_config import AI_PROVIDERS_REGISTRY

# Diagnostics go through logging, not print: background tasks fail where nobody
# is watching stdout, and an operator needs the traceback to tell "expired
# token" apart from "Supabase is down".
logger = logging.getLogger("ai_qa_agent.api")

rate_limit_write = make_rate_limiter(STANDARD_LIMIT, "user", "write")

# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

_REAPER_INTERVAL_SECONDS = 60.0
_reaper_stop = threading.Event()


def _reaper_loop() -> None:
    """Periodic maintenance off the request path: GET handlers stay read-only."""
    while True:
        try:
            reap_all_stale_scans()
            purge_orphaned_scan_secrets()
        except Exception as error:  # pragma: no cover - defensive
            logger.debug("Maintenance sweep failed: %s", error)
        if _reaper_stop.wait(_REAPER_INTERVAL_SECONDS):
            return


def init_database() -> None:
    """Local-only schema bootstrap. Deployments run ``alembic upgrade head``
    instead (see docs); AUTO_CREATE_TABLES=true forces it."""
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        try:
            from api.blogs import seed_default_blogs_if_empty
            seed_default_blogs_if_empty()
        except Exception as error:
            logger.warning("Blog seeding skipped: %s", error)
    try:
        encrypt_plaintext_rows()
    except Exception as error:
        logger.warning("Secret backfill skipped: %s", error)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await run_in_threadpool(init_database)
    except Exception as error:
        logger.error("Database initialisation failed: %s", error)
    _reaper_stop.clear()
    threading.Thread(target=_reaper_loop, name="qa-maintenance", daemon=True).start()
    try:
        yield
    finally:
        _reaper_stop.set()


app = FastAPI(
    title="JASUSS API",
    description="Automated Web Quality Assurance & Regression Platform (Powered by Nexus)",
    version="2.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

_PRODUCTION_ORIGINS = [
    "https://jasuss.tech",
    "https://www.jasuss.tech",
    "https://api.jasuss.tech",
    "https://web-two-flame-39.vercel.app",
]
_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
_DEFAULT_SAFE_ORIGINS = _PRODUCTION_ORIGINS + ([] if settings.is_production else _DEV_ORIGINS)
_DEFAULT_ORIGIN_REGEX = r"^https://web-two-flame-39(-[a-z0-9-]+)?\.vercel\.app$"

_cors_origins_raw = (settings.ALLOWED_ORIGINS or "").strip()
_cors_allow_credentials = True
if _cors_origins_raw == "*":
    # Browsers reject "*" together with credentials; auth is a bearer header,
    # so credentials are simply not needed in that mode.
    _CORS_ORIGINS: list = ["*"]
    _cors_allow_credentials = False
    logger.warning("ALLOWED_ORIGINS=* : credentialed cross-origin requests are disabled")
elif _cors_origins_raw:
    _custom = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
    _CORS_ORIGINS = list(dict.fromkeys(_DEFAULT_SAFE_ORIGINS + _custom))
else:
    _CORS_ORIGINS = _DEFAULT_SAFE_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or _DEFAULT_ORIGIN_REGEX,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Error responses: always {"detail": ...}, never driver/exception text
# ---------------------------------------------------------------------------

@app.exception_handler(SQLAlchemyError)
async def _database_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s: %s", request.method, request.url.path, type(exc).__name__, exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": "Database temporarily unavailable, please retry"})


@app.exception_handler(Exception)
async def _unhandled_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Register Domain Routers
from api.admin import admin_router
from api.blogs import blogs_router

app.include_router(admin_router)
app.include_router(blogs_router)
if settings.BILLING_ENABLED:
    from api.billing import billing_router
    app.include_router(billing_router)
else:
    logger.info("Billing router disabled (BILLING_ENABLED is not set)")


# ---------------------------------------------------------------------------
# Plans, quotas and the free trial
# ---------------------------------------------------------------------------

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


def _trial_status(db, user_id: str) -> dict:
    """Free-trial state for a user: scans run on the server key before they
    must add their own. Trial scans that failed on our side are refunded."""
    enabled = trial_enabled()
    total = trial_free_scans() if enabled else 0
    used = (
        db.query(TrialScan)
        .join(Scan, Scan.id == TrialScan.scan_id)
        .filter(TrialScan.user_id == user_id, Scan.status != "failed")
        .count()
    )
    daily_available = False
    if enabled:
        daily_limit = trial_daily_limit()
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
        "has_own_key": user_has_own_key(db, user_id),
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
_NO_WORKER_DETAIL = "No scan worker is available right now. Please try again in a few minutes."
_PAID_TIERS = ("pro", "enterprise", "team", "growth")


def _trial_exhausted_detail(trial: dict) -> str:
    if not trial.get("enabled"):
        return _NO_KEY_DETAIL
    total = trial.get("total", 0)
    return (
        f"An AI provider API key is required to keep scanning. You've used your {total} free trial "
        f"scan{'' if total == 1 else 's'}. Add your own free Gemini API key in your profile to keep scanning."
    )


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

def _validate_scan_target(value: Optional[str], label: str) -> Optional[str]:
    """SSRF protection for URLs the server's browser will navigate to: block
    private/loopback/link-local/cloud-metadata hosts (literal check here, DNS
    resolution happens worker side). ALLOW_LOCAL_TARGETS=true disables it."""
    if not value:
        return None
    value = value.strip()
    if not value.lower().startswith(("http://", "https://")):
        raise ValueError(f"{label} must be an absolute http(s) URL")
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().strip(".").rstrip(".")
    if not host:
        raise ValueError(f"{label} must include a valid hostname")
    from security.url_guard import is_blocked_host, local_targets_allowed
    if not local_targets_allowed() and is_blocked_host(host):
        raise ValueError(f"{label} targets a private or reserved address")
    return value


class ScanAuthPayload(BaseModel):
    login_url: Optional[str] = Field(default=None, max_length=2048)
    username: Optional[str] = Field(default=None, max_length=512)
    password: Optional[SecretStr] = None

    @field_validator("login_url")
    @classmethod
    def validate_login_url(cls, value: Optional[str]) -> Optional[str]:
        return _validate_scan_target(value, "login_url")


class ScanRequest(BaseModel):
    url: str = Field(..., max_length=2048)
    max_pages: int = 10
    auth_token: Optional[str] = Field(default=None, max_length=8192)
    auth: Optional[ScanAuthPayload] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        result = _validate_scan_target(value, "url")
        if not result:
            raise ValueError("url must be an absolute http(s) URL")
        return result

    @field_validator("max_pages")
    @classmethod
    def validate_max_pages(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_pages must be at least 1")
        if value > MAX_PAGES_LIMIT:
            raise ValueError(f"max_pages must not exceed {MAX_PAGES_LIMIT}")
        return value


class ApiKeyUpdateRequest(BaseModel):
    api_key: str = Field(..., max_length=512)


class UserApiKeyCreateRequest(BaseModel):
    provider_id: str = Field(default="gemini", max_length=40)
    api_key: str = Field(default="", max_length=512)
    key_name: Optional[str] = Field(default=None, max_length=120)
    model: Optional[str] = Field(default=None, max_length=120)
    endpoint: Optional[str] = Field(default=None, max_length=2048)
    is_default: Optional[bool] = False

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: Optional[str]) -> Optional[str]:
        return validate_provider_endpoint(value)


# ---------------------------------------------------------------------------
# Profile and provider keys
# ---------------------------------------------------------------------------

def _user_id(user) -> str:
    return str(getattr(user, "id", user))


def _is_paid_tier(plan_tier: str) -> bool:
    return (plan_tier or "free").lower() in _PAID_TIERS


@app.get("/api/v1/auth/me", dependencies=[Depends(rate_limit_read)])
def get_current_user_profile(user=Depends(require_user)):
    """Authenticated user profile from the local database. Read-only: admin
    status is resolved on every call, the row is created on first sight."""
    with SessionLocal() as db:
        db_user = get_or_create_user(db, user)
        is_admin = resolve_is_admin(user, db)
        return {
            "id": db_user.id,
            "email": db_user.email,
            "role": "admin" if is_admin else (db_user.role or "user"),
            "is_admin": is_admin,
            "plan_tier": db_user.plan_tier or "free",
            "has_gemini_key": user_has_own_key(db, db_user.id),
            "created_at": iso_utc(db_user.created_at),
            "dashboard_url": "/admin" if is_admin else "/dashboard",
        }


def _supported_providers() -> list:
    return [
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
    ]


@app.get("/api/v1/user/api-keys", dependencies=[Depends(rate_limit_read)])
def list_user_api_keys(user=Depends(require_user)):
    """All provider keys configured by the user, with plan quota and trial state."""
    user_id_val = _user_id(user)
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.id == user_id_val).first()
        plan_tier = (db_user.plan_tier or "free").lower() if db_user else "free"
        is_paid = _is_paid_tier(plan_tier) or resolve_is_admin(user, db)
        existing_keys = (
            db.query(UserApiKey)
            .filter(UserApiKey.user_id == user_id_val)
            .order_by(UserApiKey.created_at.asc())
            .all()
        )
        max_allowed = 999 if is_paid else 3
        count = len(existing_keys)
        return {
            "keys": [k.to_dict() for k in existing_keys],
            "count": count,
            "max_allowed": max_allowed,
            "plan_tier": plan_tier,
            "is_paid": is_paid,
            "can_add_more": is_paid or count < 3,
            "has_key": count > 0,
            "trial": _trial_status(db, user_id_val),
            "supported_providers": _supported_providers(),
        }


@app.get("/api/v1/user/trial", dependencies=[Depends(rate_limit_read)])
def get_user_trial(user=Depends(require_user)):
    """Free-trial allowance: scans a new user may run on the server's AI key before adding their own."""
    with SessionLocal() as db:
        return _trial_status(db, _user_id(user))


@app.post("/api/v1/user/api-keys", dependencies=[Depends(rate_limit_write)])
def create_user_api_key(payload: UserApiKeyCreateRequest, user=Depends(require_user)):
    """Add a provider API key. Free accounts hold at most 3 keys."""
    key_str = (payload.api_key or "").strip()
    provider_id = (payload.provider_id or "gemini").lower()

    if provider_id not in AI_PROVIDERS_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unsupported AI provider: {provider_id}")
    if not key_str and provider_id != "local_llm":
        raise HTTPException(status_code=400, detail="API Key cannot be empty.")

    provider_meta = AI_PROVIDERS_REGISTRY[provider_id]
    endpoint = payload.endpoint or provider_meta.default_endpoint
    try:
        endpoint = validate_provider_endpoint(endpoint)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    user_id_val = _user_id(user)
    with SessionLocal() as db:
        db_user = get_or_create_user(db, user)
        existing_count = db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).count()
        is_paid = _is_paid_tier(db_user.plan_tier) or resolve_is_admin(user, db)
        if existing_count >= 3 and not is_paid:
            raise HTTPException(
                status_code=403,
                detail="API Key limit reached (3/3). Free tier accounts are limited to a maximum of 3 API keys. Please start a subscription plan to add unlimited API integrations."
            )

        should_be_default = bool(payload.is_default) or existing_count == 0
        if should_be_default:
            db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).update({"is_default": False})

        new_key = UserApiKey(
            user_id=user_id_val,
            provider_id=provider_id,
            key_name=(payload.key_name or "").strip() or f"{provider_meta.name} Key",
            api_key=encrypt_secret(key_str),
            model=(payload.model or "").strip() or provider_meta.default_model,
            endpoint=endpoint,
            is_default=should_be_default,
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        return {
            "status": "success",
            "message": f"Successfully integrated {provider_meta.name} API key.",
            "key": new_key.to_dict(),
        }


@app.put("/api/v1/user/api-keys/{key_id}/default", dependencies=[Depends(rate_limit_write)])
def set_default_user_api_key(key_id: str, user=Depends(require_user)):
    """Set a specific API key as the default for QA report generation."""
    user_id_val = _user_id(user)
    with SessionLocal() as db:
        target_key = db.query(UserApiKey).filter(UserApiKey.id == key_id, UserApiKey.user_id == user_id_val).first()
        if not target_key:
            raise HTTPException(status_code=404, detail="API Key not found.")
        db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).update({"is_default": False})
        target_key.is_default = True
        db.commit()
        return {"status": "success", "message": f"{target_key.key_name} is now your active default API key."}


def _promote_newest_default(db, user_id_val: str) -> None:
    remaining = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id_val)
        .order_by(UserApiKey.created_at.desc())
        .first()
    )
    if remaining:
        remaining.is_default = True


@app.delete("/api/v1/user/api-keys/{key_id}", dependencies=[Depends(rate_limit_write)])
def delete_user_api_key_by_id(key_id: str, user=Depends(require_user)):
    """Delete an API key integration."""
    user_id_val = _user_id(user)
    with SessionLocal() as db:
        target_key = db.query(UserApiKey).filter(UserApiKey.id == key_id, UserApiKey.user_id == user_id_val).first()
        if not target_key:
            raise HTTPException(status_code=404, detail="API Key not found.")
        was_default = bool(target_key.is_default)
        db.delete(target_key)
        db.flush()
        if was_default:
            _promote_newest_default(db, user_id_val)
        db.commit()
        return {"status": "success", "message": "API Key removed successfully."}


# Legacy single-key endpoints: thin wrappers over the user's key rows.

def _default_key_row(db, user_id_val: str) -> Optional[UserApiKey]:
    return (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id_val)
        .order_by(UserApiKey.is_default.desc(), UserApiKey.created_at.desc())
        .first()
    )


@app.get("/api/v1/user/api-key", dependencies=[Depends(rate_limit_read)])
def get_user_gemini_api_key(user=Depends(require_user)):
    """Whether the user has a usable provider key, with a masked preview of the default one."""
    with SessionLocal() as db:
        row = _default_key_row(db, _user_id(user))
        if not row or not usable_user_key(row):
            return {"has_key": False, "masked_key": None}
        return {"has_key": True, "masked_key": mask_secret(row.api_key)}


@app.post("/api/v1/user/api-key", dependencies=[Depends(rate_limit_write)])
@app.put("/api/v1/user/api-key", dependencies=[Depends(rate_limit_write)])
def update_user_gemini_api_key(payload: ApiKeyUpdateRequest, user=Depends(require_user)):
    """Save the user's Google Gemini API key (stored as the default gemini key row)."""
    key = (payload.api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Gemini API Key cannot be empty.")
    if len(key) < 15:
        raise HTTPException(status_code=400, detail="Invalid Gemini API key format. Expected a valid Google AI Studio key.")

    user_id_val = _user_id(user)
    with SessionLocal() as db:
        get_or_create_user(db, user)
        db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val).update({"is_default": False})
        existing_gemini = (
            db.query(UserApiKey)
            .filter(UserApiKey.user_id == user_id_val, UserApiKey.provider_id == "gemini")
            .order_by(UserApiKey.created_at.asc())
            .first()
        )
        if existing_gemini:
            existing_gemini.api_key = encrypt_secret(key)
            existing_gemini.is_default = True
        else:
            db.add(UserApiKey(
                user_id=user_id_val,
                provider_id="gemini",
                key_name="Google Gemini Studio",
                api_key=encrypt_secret(key),
                model=AI_PROVIDERS_REGISTRY["gemini"].default_model,
                is_default=True,
            ))
        db.commit()

    return {
        "status": "success",
        "has_key": True,
        "masked_key": mask_secret(key),
        "message": "Google Gemini API key saved successfully."
    }


@app.delete("/api/v1/user/api-key", dependencies=[Depends(rate_limit_write)])
def delete_user_gemini_api_key(user=Depends(require_user)):
    """Remove the user's Google Gemini API key(s)."""
    user_id_val = _user_id(user)
    with SessionLocal() as db:
        gemini_rows = db.query(UserApiKey).filter(UserApiKey.user_id == user_id_val, UserApiKey.provider_id == "gemini").all()
        lost_default = any(r.is_default for r in gemini_rows)
        for row in gemini_rows:
            db.delete(row)
        db.flush()
        if lost_default:
            _promote_newest_default(db, user_id_val)
        db.commit()
    return {"status": "success", "has_key": False, "masked_key": None, "message": "Gemini API key removed."}


# ---------------------------------------------------------------------------
# Scan dispatch
# ---------------------------------------------------------------------------

LOCAL_MAX_CONCURRENT_SCANS = settings.QA_LOCAL_MAX_CONCURRENT_SCANS
# Semaphore + daemon threads rather than a ThreadPoolExecutor: executor
# threads are joined at interpreter exit, which would block API shutdown
# until a 30-minute scan finished.
_local_scan_slots = threading.BoundedSemaphore(LOCAL_MAX_CONCURRENT_SCANS)


def _try_enqueue_celery(scan_id: str, task_args: list) -> bool:
    """Enqueue the scan on Celery if a broker and worker are reachable (probe cached)."""
    if process_query_task is None:
        return False
    try:
        if can_use_celery():
            process_query_task.apply_async(args=task_args, task_id=scan_id)
            return True
        logger.info("Celery broker/worker unavailable for scan %s", scan_id)
    except Exception as e:
        logger.warning("Celery enqueue failed for scan %s: %s", scan_id, e)
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
def create_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    user=Depends(require_user),
    _rate_ok: bool = Depends(rate_limit_dependency),
):
    scan_id = str(uuid4())
    user_id_val = _user_id(user)
    is_authenticated = bool(
        request.auth_token or (request.auth and (request.auth.login_url or request.auth.username or request.auth.password))
    )

    with SessionLocal() as db:
        db_user = get_or_create_user(db, user)
        user_plan = (db_user.plan_tier or "free").lower()
        is_admin = resolve_is_admin(user, db)
        ai_keys_pool = user_key_pool(db, user_id_val)

    # Strict BYOK enforcement: without a personal key the scan may only run as
    # one of the user's free trial scans on the server key (decided below,
    # inside the transaction that records the scan).
    needs_trial = not ai_keys_pool
    if needs_trial and not trial_enabled():
        raise HTTPException(status_code=400, detail=_NO_KEY_DETAIL)

    plan_max_pages = _get_plan_max_pages(user_plan)
    if request.max_pages > plan_max_pages:
        logger.info(
            "Plan cap applied: user %s (%s tier) requested %d pages, capped to %d",
            user_id_val, user_plan, request.max_pages, plan_max_pages,
        )
        request.max_pages = plan_max_pages

    allow_local = settings.allow_local_fallback
    if not allow_local and not can_use_celery():
        raise HTTPException(status_code=503, detail=_NO_WORKER_DETAIL)

    primary = ai_keys_pool[0] if ai_keys_pool else {}
    launch = {
        "auth_token": request.auth_token or None,
        "login_url": request.auth.login_url if request.auth else None,
        "username": request.auth.username if request.auth else None,
        "password": request.auth.password.get_secret_value() if request.auth and request.auth.password else None,
        "trial": needs_trial,
        "provider_id": primary.get("provider_id") or "gemini",
        "model_name": primary.get("model"),
        "endpoint": primary.get("endpoint"),
    }

    # The quota, trial allowance and daily-cap checks run in the same
    # transaction as the inserts, under a lock, so parallel POSTs (multiple
    # uvicorn workers or replicas) cannot all pass a check-then-insert.
    with SessionLocal() as db:
        get_or_create_user(db, user)
        _lock_scan_creation(db, user_id_val, serialize_trials=needs_trial)
        _enforce_scan_quota(user_id_val, user_plan, is_admin, db=db)

        trial_remaining = None
        if needs_trial:
            trial = _trial_status(db, user_id_val)
            if not trial["enabled"] or trial["remaining"] <= 0:
                raise HTTPException(status_code=400, detail=_trial_exhausted_detail(trial))
            if not trial["daily_available"]:
                raise HTTPException(status_code=429, detail=_TRIAL_BUSY_DETAIL)
            trial_remaining = max(0, trial["remaining"] - 1)

        db.add(Scan(
            id=scan_id,
            user_id=user_id_val,
            url=request.url,
            status="pending",
            is_authenticated=is_authenticated,
        ))
        db.flush()
        if needs_trial:
            db.add(TrialScan(scan_id=scan_id, user_id=user_id_val, created_at=datetime.now(timezone.utc)))
        store_scan_secret(db, scan_id, launch)
        db.commit()

    if needs_trial:
        logger.info("Scan %s runs as a free trial scan for user %s (%d remaining)", scan_id, user_id_val, trial_remaining)

    # The queue message carries identifiers only; credentials and the key
    # pool are read by the worker from the encrypted scan_secrets row.
    task_args = [scan_id, user_id_val, request.url, request.max_pages]
    enqueued = _try_enqueue_celery(scan_id, task_args)

    if not enqueued:
        if not allow_local:
            update_scan(scan_id, "failed")
            raise HTTPException(status_code=503, detail=_NO_WORKER_DETAIL)
        # Local development fallback: the BackgroundTask only *submits* to a
        # bounded executor so at most QA_LOCAL_MAX_CONCURRENT_SCANS run at once.
        background_tasks.add_task(_submit_local_scan, *task_args)

    return {
        "scan_id": scan_id,
        "url": request.url,
        "status": "pending",
        "is_authenticated": is_authenticated,
        "used_trial": needs_trial,
        "trial_remaining": trial_remaining,
        "message": "Scan queued successfully.",
    }


# ---------------------------------------------------------------------------
# Scan listing, status, cancel, delete
# ---------------------------------------------------------------------------

_PUBLIC_SCAN_FIELDS = ("id", "user_id", "url", "status", "is_authenticated", "created_at", "completed_at")


def _public_scan(scan: dict) -> dict:
    return {k: scan.get(k) for k in _PUBLIC_SCAN_FIELDS}


@app.get("/api/v1/scans", dependencies=[Depends(rate_limit_read)])
def list_scans(user=Depends(require_user)):
    """List the caller's own scans, newest first."""
    user_id_val = _user_id(user)
    with SessionLocal() as db:
        scans = db.query(Scan).filter(Scan.user_id == user_id_val).order_by(Scan.created_at.desc()).limit(50).all()
        return {
            "scans": [
                {
                    "id": s.id,
                    "url": s.url,
                    "status": s.status,
                    "is_authenticated": bool(s.is_authenticated),
                    "created_at": iso_utc(s.created_at),
                    "completed_at": iso_utc(s.completed_at),
                }
                for s in scans
            ]
        }


def _is_report_payload(data) -> bool:
    return isinstance(data, dict) and ("summary" in data or "findings" in data or "url" in data or "score" in data)


@app.get("/api/v1/scans/{scan_id}", dependencies=[Depends(rate_limit_read)])
def get_scan_status(scan_id: UUID, user=Depends(require_user)):
    """Scan status, pipeline progress and (when completed) the report payload."""
    scan = get_scan(str(scan_id))
    user_id_val = _user_id(user)
    if not scan or str(scan.get("user_id")) != user_id_val:
        raise HTTPException(status_code=404, detail="Scan not found")

    response = _public_scan(scan)
    user_dir = os.path.join(ROOT_DIR, "user_data", user_id_val)
    for progress_path in (
        progress_file_path(user_id_val, str(scan_id)),
        os.path.join(ROOT_DIR, "results", f"progress_{scan_id}.json"),
    ):
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
            resolved = resolve_report_path(scan["json_path"])
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
                    if _is_report_payload(data):
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
                    response["has_cloud_report"] = True
                    if _is_report_payload(data):
                        response["results"] = data
            except Exception as e:
                logger.debug("Could not fetch report from Supabase Storage for scan %s: %s", scan_id, e)
                try:
                    from core.supabase_storage import get_supabase_client, BUCKET_NAME
                    sb = get_supabase_client()
                    if sb and sb.storage.from_(BUCKET_NAME).list(f"{user_id_val}/{scan_id}"):
                        response["has_cloud_report"] = True
                except Exception:
                    pass

    return response


def _revoke_scan_task(scan_id: str) -> None:
    try:
        from worker.celery_app import celery_app
        celery_app.control.revoke(scan_id, terminate=True, signal="SIGTERM")
        logger.info("Revoked Celery task for scan %s", scan_id)
    except Exception as e:
        logger.warning("Could not revoke Celery task for scan %s: %s", scan_id, e)


def _delete_cloud_reports(user_id_val: str, scan_id: str, context: str) -> None:
    try:
        from core.supabase_storage import delete_scan_reports
        delete_scan_reports(user_id_val, scan_id)
    except Exception as e:
        logger.warning("Could not delete Supabase files on %s for scan %s: %s", context, scan_id, e)


@app.post("/api/v1/scans/{scan_id}/cancel", dependencies=[Depends(rate_limit_write)])
def cancel_scan(scan_id: UUID, user=Depends(require_user)):
    """Stop a queued or running scan."""
    user_id_val = _user_id(user)
    sid = str(scan_id)
    with SessionLocal() as db:
        scan = db.query(Scan).filter(Scan.id == sid).first()
        if not scan or str(scan.user_id) != user_id_val:
            raise HTTPException(status_code=404, detail="Scan not found")
        if scan.status not in ("pending", "running"):
            raise HTTPException(status_code=409, detail=f"Scan is already {scan.status}; delete it instead.")
        scan.status = "cancelled"
        scan.completed_at = datetime.now(timezone.utc)
        db.query(ScanSecret).filter(ScanSecret.scan_id == sid).delete()
        db.commit()
    _revoke_scan_task(sid)
    _delete_cloud_reports(user_id_val, sid, "cancel")
    return {"status": "cancelled", "message": "Scan has been stopped."}


@app.delete("/api/v1/scans/{scan_id}", status_code=204, dependencies=[Depends(rate_limit_write)])
def delete_scan(scan_id: UUID, user=Depends(require_user)):
    """Delete a scan: its row (trial record and credentials cascade), local
    artifacts and the cloud report folder, freeing the user's storage quota."""
    user_id_val = _user_id(user)
    sid = str(scan_id)
    with SessionLocal() as db:
        scan = db.query(Scan).filter(Scan.id == sid).first()
        if not scan or str(scan.user_id) != user_id_val:
            raise HTTPException(status_code=404, detail="Scan not found")
        was_active = scan.status in ("pending", "running")
        db.delete(scan)
        db.commit()
    if was_active:
        _revoke_scan_task(sid)
    delete_scan_artifacts(user_id_val, sid)
    _delete_cloud_reports(user_id_val, sid, "delete")
    return Response(status_code=204)


@app.get("/api/v1/user/storage", dependencies=[Depends(rate_limit_read)])
def get_storage_usage(user=Depends(require_user)):
    """The user's Supabase Storage quota and usage under the 20 MB per-user limit."""
    user_id_val = _user_id(user)
    try:
        from core.supabase_storage import get_user_storage_usage
        return get_user_storage_usage(user_id_val)
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


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------

_DOWNLOAD_MEDIA_TYPES = {
    "json": "application/json",
    "md": "text/markdown; charset=utf-8",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_FILE_TYPE_ALIASES = {"json": "json", "md": "md", "markdown": "md", "pdf": "pdf", "xlsx": "xlsx", "excel": "xlsx"}
_INVALID_FILE_TYPE_DETAIL = "Invalid file type. Supported formats: 'json', 'md', 'markdown', 'pdf', 'xlsx'"


def _canonical_file_type(file_type: str) -> str:
    ext = _FILE_TYPE_ALIASES.get((file_type or "").lower().strip("."))
    if not ext:
        raise HTTPException(status_code=400, detail=_INVALID_FILE_TYPE_DETAIL)
    return ext


def _owned_completed_scan(scan_id: UUID, user) -> dict:
    scan = get_scan(str(scan_id))
    if not scan or str(scan.get("user_id")) != _user_id(user):
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


def _first_existing(*relative_paths: str) -> Optional[str]:
    for candidate in relative_paths:
        if candidate and os.path.isfile(os.path.join(ROOT_DIR, candidate)):
            return candidate
    return None


@app.get("/api/v1/scans/{scan_id}/download/{file_type}", dependencies=[Depends(rate_limit_read)])
def download_scan_file(scan_id: UUID, file_type: str, user=Depends(require_user)):
    """Download a completed scan's report in the requested format (json, md/markdown, pdf, xlsx)."""
    canonical_ext = _canonical_file_type(file_type)
    scan = _owned_completed_scan(scan_id, user)
    user_id_val = _user_id(user)
    if scan.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Scan is not completed")

    sid = str(scan_id)
    canonical_filename = f"qa-report-{sid}.{canonical_ext}"
    media_type = _DOWNLOAD_MEDIA_TYPES[canonical_ext]
    headers = {
        "Content-Disposition": f'attachment; filename="{canonical_filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }

    # 1. Direct download from Supabase Storage (no re-generation)
    try:
        from core.supabase_storage import get_scan_report_file
        cloud_bytes = get_scan_report_file(user_id_val, sid, canonical_ext)
        if cloud_bytes:
            return Response(content=cloud_bytes, media_type=media_type, headers={**headers, "X-Report-Source": "supabase-storage"})
    except Exception as e:
        logger.debug("Supabase storage direct download check for scan %s: %s", sid, e)

    # 2. Local disk, rendering PDF/XLSX from the JSON report when missing
    results_rel = os.path.join("user_data", user_id_val, "results")
    stored_path = None
    if canonical_ext == "json":
        stored_path = scan.get("json_path")
    elif canonical_ext == "md":
        stored_path = scan.get("report_path")
    else:
        stored_path = _first_existing(
            os.path.join(results_rel, f"final_qa_report_{sid}.{canonical_ext}"),
            os.path.join("user_data", user_id_val, f"final_qa_report_{sid}.{canonical_ext}"),
            os.path.join("user_data", user_id_val, f"qa-report-{sid}.{canonical_ext}"),
            os.path.join("results", f"qa-report-{sid}.{canonical_ext}"),
        )
        if not stored_path and scan.get("json_path"):
            json_resolved = resolve_report_path(scan.get("json_path"))
            if json_resolved and os.path.isfile(json_resolved):
                target = os.path.join(user_results_dir(user_id_val), f"final_qa_report_{sid}.{canonical_ext}")
                (generate_pdf_from_json if canonical_ext == "pdf" else generate_xlsx_from_json)(json_resolved, target)
                stored_path = relative_to_root(target)

    if not stored_path:
        raise HTTPException(status_code=404, detail="Report file path not found")

    resolved = resolve_report_path(stored_path)
    if not resolved or not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    # Upload to Supabase Storage lazily so future accesses are served directly
    # from the bucket. Done in the background: it is several network round
    # trips (bucket check, quota listing, upload, signed URL).
    def _lazy_upload():
        try:
            from core.supabase_storage import upload_scan_reports
            upload_scan_reports(user_id_val, sid, {canonical_ext: resolved})
        except Exception as e:
            logger.debug("Lazy upload to Supabase storage note: %s", e)

    threading.Thread(target=_lazy_upload, name="qa-lazy-upload", daemon=True).start()

    return FileResponse(
        path=resolved,
        filename=canonical_filename,
        media_type=media_type,
        headers={**headers, "X-Report-Source": "local-disk"},
    )


@app.get("/api/v1/scans/{scan_id}/signed-url/{file_type}", dependencies=[Depends(rate_limit_read)])
def get_scan_report_signed_url_endpoint(scan_id: UUID, file_type: str, user=Depends(require_user)):
    """Return a direct signed download URL from Supabase Storage."""
    canonical_ext = _canonical_file_type(file_type)
    _owned_completed_scan(scan_id, user)
    from core.supabase_storage import get_scan_report_signed_url
    url = get_scan_report_signed_url(_user_id(user), str(scan_id), canonical_ext)
    if not url:
        raise HTTPException(status_code=404, detail="Report file not found in Supabase Storage")
    return {"signed_url": url, "scan_id": str(scan_id), "file_type": canonical_ext}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

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
    """Readiness probe: database and redis reachability (details stay in the logs)."""
    from sqlalchemy import text
    checks = {"database": "unknown", "redis": "unknown"}
    is_ready = True

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as db_err:
        logger.error("Readiness: database check failed: %s", type(db_err).__name__)
        checks["database"] = "error"
        is_ready = False

    if (settings.REDIS_URL or "").strip():
        checks["redis"] = "connected" if redis_reachable(1.0) else "unavailable"
    else:
        checks["redis"] = "not_configured"

    status_code = 200 if is_ready else 503
    return JSONResponse(status_code=status_code, content={"status": "ok" if is_ready else "degraded", **checks})


# Re-exported for worker/tasks.py; new code should import these from api.pipeline / api.deps.
__all__ = [
    "app", "ADMIN_EMAILS", "AuthUser", "require_user", "require_admin", "resolve_is_admin",
    "run_qa_pipeline", "update_scan", "get_scan", "_get_scan_status_value", "supabase",
]
