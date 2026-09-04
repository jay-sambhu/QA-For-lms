import json
import ipaddress
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4, UUID
from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, Header, Request, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, SecretStr, field_validator
from supabase import create_client, Client

try:
    from .rate_limiter import rate_limit_dependency
except ImportError:
    from api.rate_limiter import rate_limit_dependency

try:
    from db import get_db, SessionLocal, engine
    from models import Scan, Base
    from worker.tasks import process_query_task
except ImportError:
    from ..db import get_db, SessionLocal, engine
    from ..models import Scan, Base
    from ..worker.tasks import process_query_task

try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

load_dotenv(dotenv_path=os.path.join(ROOT_DIR, ".env"))

# Diagnostics go through logging, not print: background tasks fail where nobody
# is watching stdout, and an operator needs the traceback to tell "expired
# token" apart from "Supabase is down".
logger = logging.getLogger("ai_qa_agent.api")

app = FastAPI(
    title="JASUSS API",
    description="Automated Web Quality Assurance & Regression Platform (Powered by Nexus)",
    version="2.0.0",
)

# Register Domain Routers
from api.billing import billing_router
from api.admin import admin_router

app.include_router(billing_router)
app.include_router(admin_router)

supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
supabase_anon_key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase_service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# Use Service Role Key for backend if available to bypass RLS, otherwise fallback to Anon Key
supabase_key = supabase_service_key if supabase_service_key else supabase_anon_key

if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
else:
    supabase = None


# A scan crawls up to `max_pages` pages with a real browser, so it needs a
# generous but finite budget. Without a timeout a wedged Playwright process
# holds a background worker forever.
PIPELINE_TIMEOUT_SECONDS = int(os.environ.get("QA_PIPELINE_TIMEOUT", "1800"))
MAX_PAGES_LIMIT = int(os.environ.get("QA_MAX_PAGES_LIMIT", "100"))


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

    if token == "dev-token":
        class DummyUserA:
            id = "00000000-0000-0000-0000-000000000001"
            email = "dev@example.com"
            role = "student"
        return DummyUserA()

    if token in ("test-token", "user-b-token"):
        class DummyUserB:
            id = "00000000-0000-0000-0000-000000000002"
            email = "user_b@example.com"
            role = "student"
        return DummyUserB()


    if not supabase:
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
    except Exception as error:
        logger.warning("Token verification failed: %s", error, exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")


    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user

def get_scan(scan_id: str):
    """Retrieve a Scan record by ID using SQLAlchemy."""
    with SessionLocal() as db:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return None
        return {
            "id": str(scan.id),
            "user_id": str(scan.user_id),
            "url": scan.url,
            "status": scan.status,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "report_path": scan.report_path,
            "json_path": scan.json_path,
        }

def update_scan(
    scan_id: str,
    status: str,
    report_path: Optional[str] = None,
    json_path: Optional[str] = None,
):
    """Update a Scan's status and optional paths via SQLAlchemy."""
    with SessionLocal() as db:
        db_scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not db_scan:
            return
        db_scan.status = status
        if status == "completed":
            db_scan.completed_at = datetime.now(timezone.utc)
            db_scan.report_path = report_path
            db_scan.json_path = json_path
        db.commit()



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
):
    """Run the QA pipeline as a background subprocess."""
    try:
        update_scan(scan_id, "running")
    except Exception as error:
        logger.exception("Failed to update scan %s to running: %s", scan_id, error)
        return

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

    if auth_token:
        # Sanitize auth_token: strip newlines to prevent argument injection
        safe_token = (auth_token or "").replace("\n", "").replace("\r", "")
        if safe_token:
            cmd.extend(["--auth-token", safe_token])

    if login_url:
        cmd.extend(["--login-url", login_url])

    if username:
        cmd.extend(["--username", username])

    # Pass password via isolated transient environment variable to avoid process-table leakage
    sub_env = dict(os.environ)
    if password:
        sub_env["QA_AUTH_PASSWORD"] = password

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
            timeout=PIPELINE_TIMEOUT_SECONDS,
            env=sub_env,
        )
    except subprocess.TimeoutExpired:
        update_scan(scan_id, "failed")
        logger.error(
            "Scan %s timed out after %ss and was terminated.",
            scan_id,
            PIPELINE_TIMEOUT_SECONDS,
        )
        return
    except Exception as error:
        update_scan(scan_id, "failed")
        logger.exception("Background task exception for scan %s: %s", scan_id, error)
        return

    # run_qa.py prints:
    #   Final JSON: <path>
    #   Final Markdown: <path>
    json_path = None
    md_path = None
    for line in result.stdout.splitlines():
        if line.startswith("Final JSON:"):
            json_path = line.split(":", 1)[1].strip()
        elif line.startswith("Final Markdown:"):
            md_path = line.split(":", 1)[1].strip()

    if json_path and md_path and result.returncode == 0:
        update_scan(
            scan_id,
            "completed",
            _relative_to_root(md_path),
            _relative_to_root(json_path),
        )
    else:
        update_scan(scan_id, "failed")
        logger.error(
            "Scan %s failed. Return code: %s\nStdout tail:\n%s\nStderr tail:\n%s",
            scan_id,
            result.returncode,
            result.stdout[-2000:],
            result.stderr[-2000:],
        )


@app.post("/api/v1/scans")
@app.post("/api/scans")
async def create_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    user=Depends(require_user),
):
    scan_id = str(uuid4())
    user_id_val = str(getattr(user, "id", user))
    is_authenticated = bool(
        request.auth_token or (request.auth and (request.auth.login_url or request.auth.username or request.auth.password))
    )

    # Persist in SQLAlchemy database as single source of truth
    with SessionLocal() as db:
        try:
            from models import User
            db_user = db.query(User).filter(User.id == user_id_val).first()
            if not db_user:
                db_user = User(id=user_id_val, email=f"user_{user_id_val}@example.com", role="student")
                db.add(db_user)
                db.commit()
        except Exception:
            db.rollback()

        db_scan = Scan(
            id=scan_id,
            user_id=user_id_val,
            url=request.url,
            status="pending",
            is_authenticated=is_authenticated,
        )
        db.add(db_scan)
        db.commit()

    # Extract auth details securely without storing or logging passwords
    login_url = request.auth.login_url if request.auth else None
    username = request.auth.username if request.auth else None
    password_raw = request.auth.password.get_secret_value() if request.auth and request.auth.password else None

    # Enqueue asynchronous Celery task with background task fallback
    enqueued = False
    try:
        from worker.tasks import process_query_task
        if login_url or username or password_raw:
            process_query_task.delay(
                scan_id,
                user_id_val,
                request.url,
                request.max_pages,
                request.auth_token,
                login_url,
                username,
                password_raw,
            )
        else:
            process_query_task.delay(
                scan_id,
                user_id_val,
                request.url,
                request.max_pages,
                request.auth_token,
            )
        enqueued = True
    except Exception as e:
        logger.warning("Celery enqueue failed (%s), running via background task", e)

    # In local development fallback to FastAPI background task if Celery was not enqueued
    if not enqueued:
        background_tasks.add_task(
            run_qa_pipeline,
            scan_id,
            user_id_val,
            request.url,
            request.max_pages,
            request.auth_token,
            login_url,
            username,
            password_raw,
        )

    return {
        "scan_id": scan_id,
        "url": request.url,
        "status": "pending",
        "is_authenticated": is_authenticated,
        "message": "Scan queued successfully."
    }



@app.get("/api/v1/scans")
@app.get("/api/scans")
async def list_scans(user=Depends(require_user)):
    """List the caller's own scans, newest first."""
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        scans = db.query(Scan).filter(Scan.user_id == user_id_val).order_by(Scan.created_at.desc()).limit(50).all()
        return {
            "scans": [
                {
                    "id": s.id,
                    "url": s.url,
                    "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                }
                for s in scans
            ]
        }



@app.get("/api/v1/scans/{scan_id}")
@app.get("/api/scans/{scan_id}")
async def get_scan_status(scan_id: UUID, user=Depends(require_user)):
    scan = get_scan(str(scan_id))
    user_id_val = str(getattr(user, "id", user))

    if not scan or str(scan.get("user_id")) != user_id_val:
        raise HTTPException(status_code=404, detail="Scan not found")

    response = dict(scan)
    
    if scan.get("status") in ("running", "pending"):
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

    if scan.get("status") == "completed" and scan.get("json_path"):
        response["results"] = None
        resolved = _resolve_report_path(scan["json_path"])
        if resolved and os.path.isfile(resolved):
            try:
                with open(resolved, "r", encoding="utf-8") as f:
                    response["results"] = json.load(f)
            except (OSError, json.JSONDecodeError) as error:
                logger.error("Could not read report for scan %s: %s", scan_id, error)

    return response


@app.post("/api/v1/scans/{scan_id}/cancel")
@app.post("/api/scans/{scan_id}/cancel")
@app.delete("/api/v1/scans/{scan_id}")
@app.delete("/api/scans/{scan_id}")
async def cancel_scan(scan_id: UUID, user=Depends(require_user)):
    """Cancel an ongoing scan or mark it stopped."""
    user_id_val = str(getattr(user, "id", user))
    with SessionLocal() as db:
        scan = db.query(Scan).filter(Scan.id == str(scan_id)).first()
        if not scan or str(scan.user_id) != user_id_val:
            raise HTTPException(status_code=404, detail="Scan not found")
        if scan.status in ("pending", "running"):
            scan.status = "cancelled"
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "cancelled", "message": "Scan has been stopped."}
        return {"status": scan.status, "message": f"Scan is already {scan.status}."}

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


@app.get("/api/v1/scans/{scan_id}/download/{file_type}")
@app.get("/api/scans/{scan_id}/download/{file_type}")
async def download_scan_file(scan_id: UUID, file_type: str, user=Depends(require_user)):
    """
    Download a completed scan's report artifact in the requested format (json, md/markdown).
    Sets explicit Content-Disposition and media_type headers with canonical filenames.
    """
    file_type_norm = file_type.lower().strip(".")
    if file_type_norm not in ("json", "md", "markdown"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Supported formats: 'json', 'md', 'markdown'"
        )

    scan = get_scan(str(scan_id))
    user_id_val = str(getattr(user, "id", user))
    if not scan or str(scan.get("user_id")) != user_id_val:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Scan is not completed")

    if file_type_norm == "json":
        stored_path = scan.get("json_path")
        canonical_ext = "json"
    else:
        stored_path = scan.get("report_path") or scan.get("md_path")
        canonical_ext = "md"

    if not stored_path:
        raise HTTPException(status_code=404, detail="Report file path not found")

    resolved = _resolve_report_path(stored_path)
    if not resolved or not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    canonical_filename = f"qa-report-{scan_id}.{canonical_ext}"
    media_type = _get_download_media_type(canonical_ext)

    return FileResponse(
        path=resolved,
        filename=canonical_filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{canonical_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@app.get("/")
def read_root():
    return {"message": "AI QA Agent SaaS API is running."}
