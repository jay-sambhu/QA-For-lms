"""Scan pipeline runner and scan persistence helpers.

Imported by the Celery worker as well as the API, so it must never import the
FastAPI app (api.main): the worker should not build CORS/routers or run
startup hooks just to reach ``run_qa_pipeline``.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

try:
    from config import settings
    from db import SessionLocal
    from models import Scan, ScanSecret, UserApiKey
    from api.secrets import decrypt_secret, encrypt_secret
    from api.utils import iso_utc
    from core.ai_config import AI_PROVIDERS_REGISTRY
except ImportError:  # pragma: no cover - package-relative import
    from ..config import settings
    from ..db import SessionLocal
    from ..models import Scan, ScanSecret, UserApiKey
    from .secrets import decrypt_secret, encrypt_secret
    from .utils import iso_utc
    from ..core.ai_config import AI_PROVIDERS_REGISTRY

logger = logging.getLogger("ai_qa_agent.api")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# A scan crawls up to `max_pages` pages with a real browser, so it needs a
# generous but finite budget. Without a timeout a wedged Playwright process
# holds a background worker forever.
PIPELINE_TIMEOUT_SECONDS = settings.QA_PIPELINE_TIMEOUT
MAX_PAGES_LIMIT = settings.QA_MAX_PAGES_LIMIT
# How often the pipeline supervisor checks for timeout / user cancellation.
_PIPELINE_POLL_SECONDS = settings.QA_PIPELINE_POLL_SECONDS
# A "running" scan whose last heartbeat (progress file / created_at) is older
# than this is considered orphaned (worker OOM-killed, API restarted while a
# fallback scan was running, ...) and is marked failed so the UI stops spinning.
STALE_RUNNING_SECONDS = settings.stale_running_seconds
# A "pending" scan nobody picked up within this window is also marked failed.
STALE_PENDING_SECONDS = settings.QA_STALE_PENDING_SECONDS
ARTIFACT_RETENTION_DAYS = settings.QA_ARTIFACT_RETENTION_DAYS


# ---------------------------------------------------------------------------
# Keys and trial configuration
# ---------------------------------------------------------------------------

def trial_server_key() -> Optional[str]:
    """The owner's Gemini key that free-trial scans run on. Never sent to clients."""
    return (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip() or settings.gemini_key


def trial_free_scans() -> int:
    return settings.TRIAL_FREE_SCANS


def trial_daily_limit() -> int:
    """Global cap of trial scans per UTC day across all users; 0 disables the cap."""
    return settings.TRIAL_DAILY_LIMIT


def trial_model() -> str:
    return (settings.TRIAL_AI_MODEL or "").strip() or AI_PROVIDERS_REGISTRY["gemini"].default_model


def trial_enabled() -> bool:
    return bool(trial_server_key()) and trial_free_scans() > 0


def usable_user_key(key: UserApiKey) -> bool:
    """A stored provider entry the scan can run on: any key, or a Local LLM
    endpoint, which legitimately has no key."""
    return bool(key.api_key) or (key.provider_id or "gemini").lower() == "local_llm"


def user_key_pool(db, user_id: str) -> list:
    """The user's provider keys, decrypted, default first."""
    user_keys = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id)
        .order_by(UserApiKey.is_default.desc(), UserApiKey.created_at.desc())
        .all()
    )
    pool = []
    for k in user_keys:
        if not usable_user_key(k):
            continue
        secret = decrypt_secret(k.api_key) if k.api_key else ""
        if k.api_key and secret is None:
            logger.error("Skipping key %s for user %s: cannot decrypt", k.id, user_id)
            continue
        pool.append({
            "api_key": secret or "",
            "provider_id": k.provider_id or "gemini",
            "model": k.model,
            "endpoint": k.endpoint,
            "label": k.key_name or k.provider_id,
        })
    return pool


def user_has_own_key(db, user_id: str) -> bool:
    return any(usable_user_key(k) for k in db.query(UserApiKey).filter(UserApiKey.user_id == user_id).all())


# ---------------------------------------------------------------------------
# Scan persistence
# ---------------------------------------------------------------------------

def scan_to_dict(scan: Scan) -> dict:
    return {
        "id": str(scan.id),
        "user_id": str(scan.user_id),
        "url": scan.url,
        "status": scan.status,
        "is_authenticated": bool(scan.is_authenticated),
        "created_at": iso_utc(scan.created_at),
        "completed_at": iso_utc(scan.completed_at),
        "report_path": scan.report_path,
        "json_path": scan.json_path,
    }


def get_scan(scan_id: str, reap_stale: bool = False) -> Optional[dict]:
    """Retrieve a Scan record by ID.

    Returns None only for a genuine miss; database errors propagate
    (SQLAlchemyError -> 503 through the app's exception handler) so an outage
    is not reported to the user as "Scan not found".

    reap_stale=True (status endpoint only) first marks an orphaned
    pending/running scan as failed.
    """
    with SessionLocal() as db:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return None
        if reap_stale:
            reap_stale_scans(db, [scan])
        return scan_to_dict(scan)


def update_scan(
    scan_id: str,
    status: str,
    report_path: Optional[str] = None,
    json_path: Optional[str] = None,
    attempts: int = 4,
) -> bool:
    """Update a Scan's status and optional paths, retrying transient database
    errors with backoff so a hiccup at the end of a 30-minute pipeline does
    not leave the scan 'running' until the stale reaper fires."""
    delay = 0.5
    for attempt in range(1, attempts + 1):
        try:
            with SessionLocal() as db:
                db_scan = db.query(Scan).filter(Scan.id == scan_id).first()
                if not db_scan or db_scan.status == "cancelled":
                    return False
                db_scan.status = status
                if status == "completed":
                    db_scan.completed_at = datetime.now(timezone.utc)
                    db_scan.report_path = report_path
                    db_scan.json_path = json_path
                elif status == "failed" and not db_scan.completed_at:
                    db_scan.completed_at = datetime.now(timezone.utc)
                if status in ("completed", "failed", "cancelled"):
                    db.query(ScanSecret).filter(ScanSecret.scan_id == scan_id).delete()
                db.commit()
                return True
        except SQLAlchemyError as error:
            if attempt == attempts:
                logger.error(
                    "Database error updating scan %s to %s after %d attempts: %s",
                    scan_id, status, attempts, error,
                )
                return False
            logger.warning("Database error updating scan %s (attempt %d): %s; retrying", scan_id, attempt, type(error).__name__)
            time.sleep(delay)
            delay = min(delay * 2, 5.0)
    return False


def _get_scan_status_value(scan_id: str) -> Optional[str]:
    """Return just the status column (used by the pipeline supervisor)."""
    try:
        with SessionLocal() as db:
            row = db.query(Scan.status).filter(Scan.id == scan_id).first()
            return row[0] if row else None
    except Exception as error:
        logger.debug("Could not read status for scan %s: %s", scan_id, error)
        return None


def store_scan_secret(db, scan_id: str, payload: dict) -> None:
    """Persist one-off launch credentials (encrypted) for the worker to read."""
    db.add(ScanSecret(scan_id=scan_id, payload=encrypt_secret(json.dumps(payload))))


def pop_scan_secret(scan_id: str) -> Optional[dict]:
    """Read and delete the launch credentials for a scan."""
    try:
        with SessionLocal() as db:
            row = db.query(ScanSecret).filter(ScanSecret.scan_id == scan_id).first()
            if not row:
                return None
            raw = decrypt_secret(row.payload)
            db.delete(row)
            db.commit()
        if raw is None:
            logger.error("Launch credentials for scan %s could not be decrypted", scan_id)
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception as error:
        logger.error("Could not read launch credentials for scan %s: %s", scan_id, type(error).__name__)
        return None


def purge_orphaned_scan_secrets(max_age_seconds: Optional[int] = None) -> int:
    """Drop launch credentials of scans that are no longer queued or running."""
    max_age = STALE_PENDING_SECONDS if max_age_seconds is None else max_age_seconds
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=max_age)
    try:
        with SessionLocal() as db:
            rows = db.query(ScanSecret).all()
            removed = 0
            for row in rows:
                scan = db.query(Scan.status).filter(Scan.id == row.scan_id).first()
                created = row.created_at.replace(tzinfo=None) if row.created_at else None
                if not scan or scan[0] not in ("pending", "running") or (created and created < cutoff):
                    db.delete(row)
                    removed += 1
            if removed:
                db.commit()
            return removed
    except Exception as error:
        logger.debug("Scan secret purge skipped: %s", error)
        return 0


# ---------------------------------------------------------------------------
# Process control
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Artifacts, progress and stale scans
# ---------------------------------------------------------------------------

# Per-run intermediate files that are not needed once the final report exists.
# Final reports, progress files, the application model and learning patterns
# are kept (they are read by the API / later runs).
_INTERMEDIATE_PREFIXES = (
    "discovery_checkpoint_", "crawl_", "checkpoint_", "agent_decisions_",
    "test_plan_", "test_cases_", "regression_", "qa_findings_", "perf_a11y_",
    "execution_results_", "evidence_manifest_", "defects_", "api_test_results_",
)


def user_results_dir(user_id: str) -> str:
    return os.path.join(ROOT_DIR, "user_data", str(user_id), "results")


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


def delete_scan_artifacts(user_id: str, scan_id: str) -> int:
    """Remove every local file produced for a scan (reports, progress, screenshots)."""
    import glob
    import shutil
    removed = 0
    user_dir = os.path.join(ROOT_DIR, "user_data", str(user_id))
    patterns = [
        os.path.join(user_dir, "results", f"*{scan_id}*"),
        os.path.join(user_dir, f"*{scan_id}*"),
        os.path.join(ROOT_DIR, "results", f"*{scan_id}*"),
    ]
    for pattern in patterns:
        for path in glob.glob(pattern):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
                removed += 1
            except OSError:
                pass
    shots = os.path.join(user_dir, "screenshots", str(scan_id))
    if os.path.isdir(shots):
        shutil.rmtree(shots, ignore_errors=True)
        removed += 1
    return removed


def progress_file_path(user_id: str, scan_id: str) -> str:
    return os.path.join(user_results_dir(user_id), f"progress_{scan_id}.json")


def _progress_mtime(user_id: str, scan_id: str) -> Optional[float]:
    for path in (
        progress_file_path(user_id, scan_id),
        os.path.join(ROOT_DIR, "results", f"progress_{scan_id}.json"),
    ):
        try:
            return os.path.getmtime(path)
        except OSError:
            continue
    return None


def record_failure_reason(user_id: str, scan_id: str, message: str) -> None:
    """Write a user-facing failure reason to the scan's progress file so the
    scan page explains what happened. Keeps a more specific reason the
    pipeline itself already recorded (stage FAILED)."""
    path = progress_file_path(user_id, scan_id)
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


def reap_stale_scans(db, scans) -> int:
    """Mark orphaned pending/running scans as failed.

    A scan is left "running" forever when its worker is OOM-killed or the API
    process restarts mid-scan (local fallback). Uses the progress file's mtime
    as a heartbeat so long-but-alive scans are not reaped.
    """
    now = time.time()
    changed = 0
    reaped = []
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
            record_failure_reason(
                scan.user_id, scan.id,
                "The scan stopped responding and was marked as failed. Please start a new scan.",
            )
            reaped.append(scan.id)
            changed += 1
    if changed:
        try:
            db.query(ScanSecret).filter(ScanSecret.scan_id.in_(reaped)).delete(synchronize_session=False)
            db.commit()
        except Exception as error:
            db.rollback()
            logger.error("Could not persist stale-scan reaping: %s", error)
    return changed


def reap_all_stale_scans() -> int:
    """Periodic sweep over every pending/running scan (runs off the request path)."""
    try:
        with SessionLocal() as db:
            scans = db.query(Scan).filter(Scan.status.in_(("pending", "running"))).all()
            return reap_stale_scans(db, scans)
    except Exception as error:
        logger.debug("Stale-scan sweep skipped: %s", error)
        return 0


def relative_to_root(path: str) -> str:
    """Store report paths relative to the repo root so they stay portable."""
    if not path:
        return path
    try:
        return os.path.relpath(os.path.abspath(path), ROOT_DIR)
    except ValueError:
        return path


def resolve_report_path(stored_path: str) -> Optional[str]:
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


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def generate_pdf_from_json(json_path: str, output_path: str):
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


def generate_xlsx_from_json(json_path: str, output_path: str):
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


# ---------------------------------------------------------------------------
# Subprocess environment
# ---------------------------------------------------------------------------

# The pipeline (and the Chromium it drives, running --no-sandbox against
# attacker-controlled pages) only gets what it needs. Service-role keys,
# database credentials and webhook secrets stay in the parent.
_SUBPROCESS_ENV_KEYS = (
    "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR", "TMP", "TEMP", "USER", "LOGNAME",
    "PYTHONPATH", "PYTHONUNBUFFERED", "PYTHONIOENCODING", "PYTHONDONTWRITEBYTECODE", "VIRTUAL_ENV",
    "DISPLAY", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy",
    "AI_MODEL", "GEMINI_FALLBACK_MODELS", "ALLOW_LOCAL_TARGETS", "ENVIRONMENT", "LOG_LEVEL",
)
_SUBPROCESS_ENV_PREFIXES = ("PLAYWRIGHT_", "QA_", "XDG_", "CHROME", "CHROMIUM", "NODE_", "DEBUG")
_SUBPROCESS_ENV_BLOCKED = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "QA_AUTH_PASSWORD", "QA_AUTH_TOKEN", "QA_AI_KEYS_POOL")


def build_subprocess_env() -> dict:
    env = {}
    for key, value in os.environ.items():
        if key in _SUBPROCESS_ENV_BLOCKED:
            continue
        if key in _SUBPROCESS_ENV_KEYS or key.startswith(_SUBPROCESS_ENV_PREFIXES):
            env[key] = value
    env.setdefault("PATH", os.defpath)
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------

def _preflight_targets(scan_id: str, url: str, login_url: Optional[str], ai_keys_pool: list) -> tuple:
    """SSRF: the API validator only inspects the literal hostname. Resolve the
    scan targets and every provider endpoint here (worker side, off the
    request path) so DNS names pointing at internal addresses cannot be
    reached. Returns (ok, filtered_pool)."""
    try:
        from security.url_guard import local_targets_allowed, url_targets_private_network
    except Exception as guard_err:
        logger.warning("SSRF pre-flight check skipped for scan %s: %s", scan_id, guard_err)
        return True, ai_keys_pool
    if local_targets_allowed():
        return True, ai_keys_pool
    for target in (url, login_url):
        reason = url_targets_private_network(target) if target else None
        if reason:
            logger.warning("Scan %s rejected (SSRF guard): %s", scan_id, reason)
            return False, ai_keys_pool
    filtered = []
    for cfg in ai_keys_pool or []:
        endpoint = cfg.get("endpoint") if isinstance(cfg, dict) else None
        reason = url_targets_private_network(endpoint) if endpoint else None
        if reason:
            logger.warning("Scan %s: dropping provider endpoint %r (SSRF guard: %s)", scan_id, cfg.get("label"), reason)
            continue
        filtered.append(cfg)
    return True, filtered


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
    """Run the QA pipeline as a supervised subprocess.

    The queue message carries only identifiers; credentials (login password,
    bearer token, trial flag, provider choice) are read once from the
    encrypted ``scan_secrets`` row and the user's key pool is loaded from the
    database here.
    """
    if not update_scan(scan_id, "running"):
        logger.warning("Scan %s is missing or cancelled; pipeline not started", scan_id)
        return

    launch = pop_scan_secret(scan_id) or {}
    auth_token = auth_token or launch.get("auth_token")
    login_url = login_url or launch.get("login_url")
    username = username or launch.get("username")
    password = password or launch.get("password")
    provider_id = provider_id or launch.get("provider_id")
    model_name = model_name or launch.get("model_name")
    endpoint = endpoint or launch.get("endpoint")

    if launch.get("trial"):
        # Trial scans run on the server key only: an explicit one-entry pool
        # stops the worker from using keys the user may add later, which
        # would run a scan already charged to the trial on their key.
        gemini_api_key = trial_server_key()
        ai_keys_pool = [{
            "api_key": gemini_api_key,
            "provider_id": "gemini",
            "model": trial_model(),
            "endpoint": None,
            "label": "Free trial",
        }]
        provider_id, model_name, endpoint = "gemini", trial_model(), None
    elif not ai_keys_pool:
        try:
            with SessionLocal() as db:
                ai_keys_pool = user_key_pool(db, str(user_id))
        except Exception as e:
            logger.warning("Could not fetch ai_keys_pool from DB for user %s: %s", user_id, e)
            ai_keys_pool = []

    ok, ai_keys_pool = _preflight_targets(scan_id, url, login_url, ai_keys_pool or [])
    if not ok:
        record_failure_reason(user_id, scan_id, "The target address is not allowed to be scanned.")
        update_scan(scan_id, "failed")
        return

    if not gemini_api_key and ai_keys_pool:
        gemini_api_key = ai_keys_pool[0].get("api_key")
        provider_id = provider_id or ai_keys_pool[0].get("provider_id")
        model_name = model_name or ai_keys_pool[0].get("model")
        endpoint = endpoint or ai_keys_pool[0].get("endpoint")

    if endpoint:
        try:
            from security.url_guard import local_targets_allowed, url_targets_private_network
            if not local_targets_allowed() and url_targets_private_network(endpoint):
                logger.warning("Scan %s: primary endpoint rejected by SSRF guard", scan_id)
                endpoint = None
        except Exception:
            pass

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
    sub_env = build_subprocess_env()
    if password:
        sub_env["QA_AUTH_PASSWORD"] = password
    if gemini_api_key:
        sub_env["GEMINI_API_KEY"] = gemini_api_key
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

    secrets_to_redact = [v for v in (password, gemini_api_key, safe_token, trial_server_key()) if v]
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
        """Kill the pipeline on timeout or when the user cancels the scan."""
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
        record_failure_reason(
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
        record_failure_reason(
            user_id, scan_id,
            f"The scan took longer than {PIPELINE_TIMEOUT_SECONDS // 60} minutes and was stopped. "
            "Try again with fewer pages.",
        )
        update_scan(scan_id, "failed")
        logger.error("Scan %s timed out after %ss and was terminated.", scan_id, PIPELINE_TIMEOUT_SECONDS)
        return

    if json_path and md_path and result_returncode == 0:
        # Pre-render PDF and XLSX so all formats are immediately available without regeneration
        results_dir = user_results_dir(user_id)
        os.makedirs(results_dir, exist_ok=True)
        pdf_path = os.path.join(results_dir, f"final_qa_report_{scan_id}.pdf")
        xlsx_path = os.path.join(results_dir, f"final_qa_report_{scan_id}.xlsx")

        try:
            generate_pdf_from_json(json_path, pdf_path)
        except Exception as e:
            logger.warning("Could not pre-render PDF for scan %s: %s", scan_id, e)
            pdf_path = None

        try:
            generate_xlsx_from_json(json_path, xlsx_path)
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
            relative_to_root(md_path),
            relative_to_root(json_path),
        )
    else:
        if result_returncode is not None and result_returncode < 0:
            # Killed by a signal, most often the OOM killer on a small server
            reason = ("The scan was stopped by the server, possibly because it ran out of memory. "
                      "Try again with fewer pages.")
        else:
            reason = ("The scan could not finish. The site may be unreachable, "
                      "blocking automated browsers, or the AI provider may have rejected the request.")
        record_failure_reason(user_id, scan_id, reason)
        update_scan(scan_id, "failed")
        logger.error(
            "Scan %s failed. Return code: %s\nStdout tail:\n%s",
            scan_id,
            result_returncode,
            result_stdout[-2000:],
        )
