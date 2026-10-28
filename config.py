#!/usr/bin/env python3
"""Centralized environment configuration using pydantic-settings.

Every tunable the API reads lives here so there is one list of environment
variables instead of ad-hoc ``os.environ`` reads scattered across modules.
All fields are optional to allow test environments that do not provide them.
"""

from pathlib import Path
from typing import Optional

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    # Backward compatibility: support GOOGLE_API_KEY as fallback
    GOOGLE_API_KEY: Optional[str] = None
    AI_MODEL: str = "gemini-3.8-flash"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # Pipeline budget: a scan crawls up to max_pages pages with a real browser.
    QA_PIPELINE_TIMEOUT: int = 1800
    QA_MAX_PAGES_LIMIT: int = 100
    QA_PIPELINE_POLL_SECONDS: float = 5.0
    # A running scan whose heartbeat is older than this is marked failed
    # (defaults to QA_PIPELINE_TIMEOUT + 600 when unset).
    QA_STALE_SCAN_SECONDS: Optional[int] = None
    QA_STALE_PENDING_SECONDS: int = 86400
    QA_ARTIFACT_RETENTION_DAYS: float = 7.0
    # In-process scan fallback when no Celery worker answers.
    QA_LOCAL_MAX_CONCURRENT_SCANS: int = 1
    QA_ALLOW_LOCAL_FALLBACK: Optional[bool] = None
    QA_CELERY_PROBE_TTL_SECONDS: float = 30.0

    # Free trial: scans a new user may run on the server key.
    TRIAL_FREE_SCANS: int = 3
    TRIAL_DAILY_LIMIT: int = 50
    TRIAL_AI_MODEL: Optional[str] = None

    # Auth
    ADMIN_EMAILS: str = ""
    SUPABASE_JWT_SECRET: Optional[str] = None
    SUPABASE_JWT_AUDIENCE: str = "authenticated"
    SUPABASE_JWKS_URL: Optional[str] = None
    AUTH_CACHE_TTL_SECONDS: int = 60

    # Secrets at rest (Fernet key or any passphrase; see api/secrets.py)
    API_KEY_ENCRYPTION_KEY: Optional[str] = None

    # Rate limits (requests per minute)
    RATE_LIMIT_STANDARD: int = 20
    RATE_LIMIT_ELEVATED: Optional[int] = None
    RATE_LIMIT_INSTRUCTOR: int = 60
    RATE_LIMIT_READ: int = 120
    RATE_LIMIT_PUBLIC: int = 60
    RATE_LIMIT_MEMORY_MAX_KEYS: int = 5000

    # HTTP
    ALLOWED_ORIGINS: str = ""
    CORS_ORIGIN_REGEX: Optional[str] = None
    BILLING_ENABLED: bool = False
    AUTO_CREATE_TABLES: Optional[bool] = None
    ALLOW_LOCAL_TARGETS: bool = False

    @field_validator(
        "QA_PIPELINE_TIMEOUT", "QA_MAX_PAGES_LIMIT", "QA_STALE_PENDING_SECONDS",
        "QA_LOCAL_MAX_CONCURRENT_SCANS", "TRIAL_FREE_SCANS", "TRIAL_DAILY_LIMIT",
        "AUTH_CACHE_TTL_SECONDS", "RATE_LIMIT_STANDARD", "RATE_LIMIT_INSTRUCTOR",
        "RATE_LIMIT_READ", "RATE_LIMIT_PUBLIC", "RATE_LIMIT_MEMORY_MAX_KEYS",
        mode="before",
    )
    @classmethod
    def _blank_int_is_default(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("QA_STALE_SCAN_SECONDS", "RATE_LIMIT_ELEVATED", "TRIAL_AI_MODEL",
                     "SUPABASE_JWT_SECRET", "SUPABASE_JWKS_URL", "API_KEY_ENCRYPTION_KEY",
                     "CORS_ORIGIN_REGEX", "QA_ALLOW_LOCAL_FALLBACK", "AUTO_CREATE_TABLES",
                     mode="before")
    @classmethod
    def _blank_is_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("BILLING_ENABLED", "ALLOW_LOCAL_TARGETS", mode="before")
    @classmethod
    def _blank_bool_is_false(cls, value):
        if isinstance(value, str) and not value.strip():
            return False
        return value

    @field_validator("QA_PIPELINE_TIMEOUT", "QA_MAX_PAGES_LIMIT", "QA_LOCAL_MAX_CONCURRENT_SCANS")
    @classmethod
    def _at_least_one(cls, value: int) -> int:
        return max(1, int(value))

    @field_validator("TRIAL_FREE_SCANS", "TRIAL_DAILY_LIMIT", "QA_STALE_PENDING_SECONDS")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        return max(0, int(value))

    @property
    def gemini_key(self) -> Optional[str]:
        """Effective Gemini API key, preferring GEMINI_API_KEY over GOOGLE_API_KEY."""
        return (self.GEMINI_API_KEY or self.GOOGLE_API_KEY or "").strip() or None

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("production", "prod")

    @property
    def stale_running_seconds(self) -> int:
        if self.QA_STALE_SCAN_SECONDS is not None:
            return max(0, self.QA_STALE_SCAN_SECONDS)
        return self.QA_PIPELINE_TIMEOUT + 600

    @property
    def allow_local_fallback(self) -> bool:
        """In-process pipeline runs when no worker answers: opt-in in
        production, on by default for local development."""
        if self.QA_ALLOW_LOCAL_FALLBACK is not None:
            return self.QA_ALLOW_LOCAL_FALLBACK
        return not self.is_production

    @property
    def auto_create_tables(self) -> bool:
        """create_all() at startup is for local sqlite only; deployments run
        ``alembic upgrade head``."""
        if self.AUTO_CREATE_TABLES is not None:
            return self.AUTO_CREATE_TABLES
        return (self.DATABASE_URL or "sqlite").startswith("sqlite")

    @property
    def admin_emails(self) -> set:
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}

    @property
    def elevated_rate_limit(self) -> int:
        return self.RATE_LIMIT_ELEVATED if self.RATE_LIMIT_ELEVATED is not None else self.RATE_LIMIT_INSTRUCTOR


# Instantiate a singleton for import convenience
try:
    settings = Settings()
except ValidationError as exc:
    # Fail fast with clear message if required vars missing
    raise RuntimeError(f"Configuration error: {exc}") from exc
