"""Encryption at rest for provider API keys and one-off scan credentials.

Values are stored as ``enc:<fernet token>`` when API_KEY_ENCRYPTION_KEY is
configured. Plaintext rows written before the key existed stay readable, so
the key can be introduced (and the backfill run) without downtime.
"""

import base64
import hashlib
import logging
from typing import Optional

try:
    from config import settings
except ImportError:  # pragma: no cover - package-relative import
    from ..config import settings

logger = logging.getLogger("ai_qa_agent.secrets")

ENC_PREFIX = "enc:"

_fernet = None
_fernet_resolved = False


def _derive_fernet_key(raw: str) -> bytes:
    """Accept a proper Fernet key or any passphrase (hashed to 32 bytes)."""
    candidate = raw.strip().encode("utf-8")
    try:
        if len(base64.urlsafe_b64decode(candidate)) == 32:
            return candidate
    except Exception:
        pass
    return base64.urlsafe_b64encode(hashlib.sha256(candidate).digest())


def _get_fernet():
    global _fernet, _fernet_resolved
    if _fernet_resolved:
        return _fernet
    _fernet_resolved = True
    raw = (settings.API_KEY_ENCRYPTION_KEY or "").strip()
    if not raw:
        _fernet = None
        return None
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(_derive_fernet_key(raw))
    except Exception as error:  # pragma: no cover - depends on env
        logger.error("API_KEY_ENCRYPTION_KEY is unusable, secrets stay in plaintext: %s", error)
        _fernet = None
    return _fernet


def encryption_enabled() -> bool:
    return _get_fernet() is not None


def reset_cache() -> None:
    """Re-read the key (tests swap API_KEY_ENCRYPTION_KEY at runtime)."""
    global _fernet, _fernet_resolved
    _fernet = None
    _fernet_resolved = False


def is_encrypted(value: Optional[str]) -> bool:
    return bool(value) and value.startswith(ENC_PREFIX)


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if value == "" or is_encrypted(value):
        return value
    fernet = _get_fernet()
    if fernet is None:
        return value
    return ENC_PREFIX + fernet.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not is_encrypted(value):
        return value
    fernet = _get_fernet()
    if fernet is None:
        logger.error("Encrypted secret found but API_KEY_ENCRYPTION_KEY is not configured")
        return None
    try:
        return fernet.decrypt(value[len(ENC_PREFIX):].encode("ascii")).decode("utf-8")
    except Exception as error:
        logger.error("Could not decrypt a stored secret (wrong API_KEY_ENCRYPTION_KEY?): %s", type(error).__name__)
        return None


def mask_secret(value: Optional[str]) -> str:
    """Short fingerprint for display: never more than the first 6 and last 4 characters."""
    key = (decrypt_secret(value) or "").strip()
    if len(key) >= 12:
        return f"{key[:6]}...{key[-4:]}"
    return "••••••••"


def encrypt_plaintext_rows() -> int:
    """One-off backfill: encrypt every plaintext secret column in place.

    Idempotent (rows already prefixed are skipped) and a no-op without a key,
    so it is safe to run at every startup.
    """
    if not encryption_enabled():
        return 0
    try:
        from db import SessionLocal
        from models import ApiKey, ScanSecret, UserApiKey
    except ImportError:  # pragma: no cover
        from ..db import SessionLocal
        from ..models import ApiKey, ScanSecret, UserApiKey
    changed = 0
    with SessionLocal() as db:
        for row in db.query(UserApiKey).filter(~UserApiKey.api_key.like(f"{ENC_PREFIX}%")).all():
            if row.api_key:
                row.api_key = encrypt_secret(row.api_key)
                changed += 1
        for row in db.query(ApiKey).filter(~ApiKey.key_value.like(f"{ENC_PREFIX}%")).all():
            if row.key_value:
                row.key_value = encrypt_secret(row.key_value)
                changed += 1
        for row in db.query(ScanSecret).filter(~ScanSecret.payload.like(f"{ENC_PREFIX}%")).all():
            if row.payload:
                row.payload = encrypt_secret(row.payload)
                changed += 1
        if changed:
            db.commit()
    if changed:
        logger.info("Encrypted %d stored secrets at rest", changed)
    return changed
