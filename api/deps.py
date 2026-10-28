"""Authentication dependencies shared by every router.

- ``require_user``: resolves the caller from the bearer token. The Supabase
  access token is verified locally (HS256 with SUPABASE_JWT_SECRET, or the
  project's JWKS for asymmetric keys); ``supabase.auth.get_user`` is only the
  fallback when no local check can run. Results are cached briefly so the
  2-second status poll does not cost a network round trip per request.
- ``resolve_is_admin``: the one definition of "is this caller an admin".
- ``require_admin``: ``require_user`` + ``resolve_is_admin``.
- ``get_or_create_user``: the one place a ``users`` row is created.
"""

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException
from sqlalchemy.exc import IntegrityError

try:
    from config import settings
    from db import SessionLocal
    from models import User
except ImportError:  # pragma: no cover - package-relative import
    from ..config import settings
    from ..db import SessionLocal
    from ..models import User

logger = logging.getLogger("ai_qa_agent.api.auth")

supabase_url = (os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL") or "").strip()
supabase_anon_key = (os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or "").strip()
supabase_service_key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
supabase_key = supabase_service_key or supabase_anon_key

missing_supabase_vars = []
if not supabase_url:
    missing_supabase_vars.append("NEXT_PUBLIC_SUPABASE_URL")
if not supabase_key:
    missing_supabase_vars.append("SUPABASE_SERVICE_ROLE_KEY / NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase = None
if supabase_url and supabase_key:
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        logger.info(
            "Supabase client initialised with %s",
            "SERVICE_ROLE_KEY" if supabase_service_key else "ANON_KEY",
        )
    except Exception as exc:  # pragma: no cover - depends on env
        logger.error("Failed to instantiate Supabase client: %s", exc, exc_info=True)
        supabase = None
else:
    logger.warning(
        "Supabase credentials missing (%s): authentication is disabled",
        ", ".join(missing_supabase_vars),
    )

ADMIN_EMAILS = settings.admin_emails
if not ADMIN_EMAILS:
    logger.warning("ADMIN_EMAILS is empty: no account is granted admin by email (set it or use app_metadata.role)")

_JWT_ALGORITHMS = ("HS256", "RS256", "ES256")


@dataclass
class AuthUser:
    """The caller as seen by the API. Mirrors the attributes routes read from
    Supabase's user object (id, email, app_metadata, user_metadata)."""
    id: str
    email: str = ""
    app_metadata: Dict[str, Any] = field(default_factory=dict)
    user_metadata: Dict[str, Any] = field(default_factory=dict)
    email_confirmed_at: Optional[str] = None
    role: Optional[str] = None
    token: str = field(default="", repr=False)
    from_jwt: bool = field(default=False, repr=False)


def _as_auth_user(raw: Any, token: str) -> AuthUser:
    app_meta = getattr(raw, "app_metadata", None)
    user_meta = getattr(raw, "user_metadata", None)
    return AuthUser(
        id=str(getattr(raw, "id", "") or ""),
        email=str(getattr(raw, "email", "") or "").lower(),
        app_metadata=dict(app_meta) if isinstance(app_meta, dict) else {},
        user_metadata=dict(user_meta) if isinstance(user_meta, dict) else {},
        email_confirmed_at=str(getattr(raw, "email_confirmed_at", None) or getattr(raw, "confirmed_at", None) or "") or None,
        role=getattr(raw, "role", None),
        token=token,
        from_jwt=False,
    )


# ---------------------------------------------------------------------------
# Local token verification
# ---------------------------------------------------------------------------

_jwks_client = None
_jwks_lock = threading.Lock()


def _jwks_url() -> Optional[str]:
    if settings.SUPABASE_JWKS_URL:
        return settings.SUPABASE_JWKS_URL
    if supabase_url:
        return supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
    return None


def _get_jwks_client():
    global _jwks_client
    url = _jwks_url()
    if not url:
        return None
    with _jwks_lock:
        if _jwks_client is None:
            from jwt import PyJWKClient
            _jwks_client = PyJWKClient(url, cache_keys=True, lifespan=3600)
        return _jwks_client


class _LocalVerifyUnavailable(Exception):
    """No local check could run (no secret / JWKS unreachable): fall back."""


def _verify_token_locally(token: str) -> AuthUser:
    """Return the caller from a locally verified token, raise HTTPException(401)
    for a rejected token, or _LocalVerifyUnavailable when nothing can be checked."""
    import jwt

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    alg = str(header.get("alg") or "")
    if alg not in _JWT_ALGORITHMS:
        raise HTTPException(status_code=401, detail="Invalid token")

    options = {"require": ["exp", "sub"]}
    audience = settings.SUPABASE_JWT_AUDIENCE or None
    try:
        if alg == "HS256":
            secret = (settings.SUPABASE_JWT_SECRET or "").strip()
            if not secret:
                raise _LocalVerifyUnavailable("SUPABASE_JWT_SECRET not configured")
            claims = jwt.decode(token, secret, algorithms=["HS256"], audience=audience, options=options)
        else:
            client = _get_jwks_client()
            if client is None:
                raise _LocalVerifyUnavailable("no JWKS url")
            try:
                signing_key = client.get_signing_key_from_jwt(token)
            except jwt.exceptions.PyJWKClientError as error:
                raise _LocalVerifyUnavailable(str(error))
            claims = jwt.decode(token, signing_key.key, algorithms=[alg], audience=audience, options=options)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as error:
        logger.warning("Token rejected by local verification: %s", type(error).__name__)
        raise HTTPException(status_code=401, detail="Invalid token")

    app_meta = claims.get("app_metadata")
    user_meta = claims.get("user_metadata")
    return AuthUser(
        id=str(claims.get("sub") or ""),
        email=str(claims.get("email") or "").lower(),
        app_metadata=app_meta if isinstance(app_meta, dict) else {},
        user_metadata=user_meta if isinstance(user_meta, dict) else {},
        email_confirmed_at=None,
        role=claims.get("role"),
        token=token,
        from_jwt=True,
    )


def _verify_token_remotely(token: str) -> AuthUser:
    if not supabase:
        missing_desc = ", ".join(missing_supabase_vars) if missing_supabase_vars else "NEXT_PUBLIC_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY"
        logger.error("Authentication rejected: Supabase client is not configured. Missing variable(s): %s", missing_desc)
        raise HTTPException(
            status_code=503,
            detail=f"Authentication service unavailable: missing environment variable(s) {missing_desc}",
        )
    for attempt in (1, 2):
        try:
            raw = supabase.auth.get_user(token).user
            break
        except Exception as error:
            # A rejected token is final. A transport failure (typically the
            # server closing an idle HTTP/2 connection) is retried once;
            # reporting it as 401 made the UI drop the user's data as if they
            # were signed out.
            is_rejection = type(error).__module__.startswith("supabase_auth") or hasattr(error, "status")
            if is_rejection:
                logger.warning("Token verification failed: %s", type(error).__name__)
                raise HTTPException(status_code=401, detail="Invalid token")
            if attempt == 2:
                logger.error("Auth service unreachable while verifying token: %s", error, exc_info=True)
                raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable, please retry")
            logger.warning("Auth transport error (%s); retrying token verification once", type(error).__name__)
    if not raw or not getattr(raw, "id", None):
        raise HTTPException(status_code=401, detail="Invalid token")
    return _as_auth_user(raw, token)


# ---------------------------------------------------------------------------
# Caches
# ---------------------------------------------------------------------------

_auth_cache: Dict[str, tuple] = {}
_auth_cache_lock = threading.Lock()
_AUTH_CACHE_MAX = 10000

_synced_users: set = set()
_confirmed_cache: Dict[str, tuple] = {}
_CONFIRMED_TTL = 3600.0


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _cached_user(token: str) -> Optional[AuthUser]:
    key = _token_key(token)
    with _auth_cache_lock:
        entry = _auth_cache.get(key)
        if entry and entry[1] > time.monotonic():
            return entry[0]
        _auth_cache.pop(key, None)
    return None


def _remember_user(token: str, user: AuthUser) -> None:
    ttl = max(0, int(settings.AUTH_CACHE_TTL_SECONDS))
    if ttl <= 0:
        return
    with _auth_cache_lock:
        if len(_auth_cache) >= _AUTH_CACHE_MAX:
            _auth_cache.clear()
        _auth_cache[_token_key(token)] = (user, time.monotonic() + ttl)


def clear_auth_caches() -> None:
    with _auth_cache_lock:
        _auth_cache.clear()
    _synced_users.clear()
    _confirmed_cache.clear()


def email_confirmed(user: Any) -> bool:
    """Whether the caller's email address is verified. A locally verified
    token carries no confirmation claim, so the answer is fetched from
    Supabase once per user and cached; without Supabase it is False (an
    email-based elevation must fail closed)."""
    if getattr(user, "email_confirmed_at", None) or getattr(user, "confirmed_at", None):
        return True
    user_id = str(getattr(user, "id", "") or "")
    token = getattr(user, "token", "") or ""
    if not user_id or not token or not supabase:
        return False
    entry = _confirmed_cache.get(user_id)
    if entry and entry[1] > time.monotonic():
        return entry[0]
    confirmed = False
    try:
        raw = supabase.auth.get_user(token).user
        confirmed = bool(getattr(raw, "email_confirmed_at", None) or getattr(raw, "confirmed_at", None))
    except Exception as error:
        logger.warning("Could not confirm email status for user %s: %s", user_id, type(error).__name__)
    if len(_confirmed_cache) > 5000:
        _confirmed_cache.clear()
    _confirmed_cache[user_id] = (confirmed, time.monotonic() + _CONFIRMED_TTL)
    return confirmed


# ---------------------------------------------------------------------------
# Admin resolution and user sync
# ---------------------------------------------------------------------------

def _admin_by_identity(user: Any) -> bool:
    """Admin from the identity provider: app_metadata.role (set server-side in
    Supabase, not writable by the browser) or the confirmed ADMIN_EMAILS list.
    user_metadata is never trusted."""
    app_meta = getattr(user, "app_metadata", None)
    if isinstance(app_meta, dict) and app_meta.get("role") == "admin":
        return True
    email = str(getattr(user, "email", "") or "").lower()
    return bool(email) and email in ADMIN_EMAILS and email_confirmed(user)


def resolve_is_admin(user: Any, db=None) -> bool:
    """The single admin rule: identity provider role, confirmed allow-listed
    email, or role='admin' on the users row."""
    if user is None:
        return False
    if _admin_by_identity(user):
        return True
    user_id = str(getattr(user, "id", user) or "")
    if not user_id:
        return False
    try:
        if db is not None:
            row = db.query(User.role).filter(User.id == user_id).first()
        else:
            with SessionLocal() as session:
                row = session.query(User.role).filter(User.id == user_id).first()
    except Exception as error:
        logger.error("Could not read role for user %s: %s", user_id, error)
        return False
    return bool(row and row[0] == "admin")


def _placeholder_email(user_id: str) -> str:
    return f"{user_id}@no-email.invalid"


def get_or_create_user(db, user: Any) -> User:
    """Return the ``users`` row for the caller, creating it on first sight
    with the real email, role derived from the identity provider and the free
    plan. Safe under concurrent first requests."""
    user_id = str(getattr(user, "id", user) or "")
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        return db_user
    email = str(getattr(user, "email", "") or "").strip().lower() or _placeholder_email(user_id)
    db_user = User(
        id=user_id,
        email=email,
        role="admin" if _admin_by_identity(user) else "user",
        plan_tier="free",
    )
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user is None:
            raise
        return db_user
    db.refresh(db_user)
    return db_user


def _sync_user_once(user: AuthUser) -> None:
    if user.id in _synced_users:
        return
    try:
        with SessionLocal() as db:
            get_or_create_user(db, user)
        if len(_synced_users) > 50000:
            _synced_users.clear()
        _synced_users.add(user.id)
    except Exception as error:
        logger.error("Failed to sync user %s to local DB: %s", user.id, error)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def require_user(authorization: str = Header(None)) -> AuthUser:
    """Resolve the caller from the Authorization header.

    Used as a dependency on every route that touches user data. Sync on
    purpose: FastAPI runs it in the threadpool, so the (rare) network call
    never blocks the event loop.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    cached = _cached_user(token)
    if cached is not None:
        return cached

    try:
        user = _verify_token_locally(token)
    except _LocalVerifyUnavailable as why:
        logger.debug("Local token verification unavailable (%s); using Supabase", why)
        user = _verify_token_remotely(token)

    if not user.id:
        raise HTTPException(status_code=401, detail="Invalid token")

    _sync_user_once(user)
    _remember_user(token, user)
    return user


def require_admin(authorization: str = Header(None)) -> AuthUser:
    """Admin-only dependency: a valid user that ``resolve_is_admin`` accepts."""
    user = require_user(authorization)
    if not resolve_is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
