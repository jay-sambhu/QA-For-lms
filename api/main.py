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
from pydantic import BaseModel, field_validator
from supabase import create_client, Client

try:
    from .rate_limiter import rate_limit_dependency
except ImportError:
    from api.rate_limiter import rate_limit_dependency

try:
    from db import get_db, SessionLocal
    from models import Scan
    from worker.tasks import process_query_task
except ImportError:
    from ..db import get_db, SessionLocal
    from ..models import Scan
    from ..worker.tasks import process_query_task

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

load_dotenv(dotenv_path=os.path.join(ROOT_DIR, ".env"))

# Diagnostics go through logging, not print: background tasks fail where nobody
# is watching stdout, and an operator needs the traceback to tell "expired
# token" apart from "Supabase is down".
logger = logging.getLogger("ai_qa_agent.api")

app = FastAPI(title="AI QA Agent SaaS API")

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


class ScanRequest(BaseModel):
    url: str
    max_pages: int = 10
    auth_token: Optional[str] = None

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

    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
    except Exception as error:
        # The caller still only learns "invalid token" -- but the operator gets
        # the real reason. Swallowing this silently made an unreachable Supabase
        # project indistinguishable from a genuinely bad token, which is the
        # difference between "sign in again" and "your auth provider is down".
        logger.warning("Token verification failed: %s", error, exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user

def get_scan(scan_id: str):
    """Retrieve a Scan record by ID using SQLAlchemy."""
    with SessionLocal() as db:
        return db.query(Scan).filter(Scan.id == scan_id).first()

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
    scan_id: str, user_id: str, url: str, max_pages: int, auth_token: Optional[str]
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

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
            timeout=PIPELINE_TIMEOUT_SECONDS,
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


@app.post("/api/scans")
async def create_scan(
    request: ScanRequest,
    user=Depends(require_user),
):
    scan_id = str(uuid4())
    user_id_val = str(getattr(user, "id", user))

    if supabase:
        supabase.table("scans").insert({
            "id": scan_id,
            "user_id": user_id_val,
            "url": request.url,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
    else:
        with SessionLocal() as db:
            db_scan = Scan(
                id=scan_id,
                user_id=user_id_val,
                url=request.url,
                status="pending",
            )
            db.add(db_scan)
            db.commit()

    # Enqueue asynchronous Celery task
    process_query_task.delay(scan_id, user_id_val, request.url, request.max_pages, request.auth_token)

    return {"scan_id": scan_id, "url": request.url, "status": "pending", "message": "Scan queued successfully."}



@app.get("/api/scans")
async def list_scans(user=Depends(require_user)):
    """List the caller's own scans, newest first."""
    response = (
        supabase.table("scans")
        .select("id,url,status,created_at,completed_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return {"scans": response.data or []}


@app.get("/api/scans/{scan_id}")
async def get_scan_status(scan_id: UUID, user=Depends(require_user)):
    scan = get_scan(str(scan_id))

    # Require ownership. This endpoint previously had no authentication at all,
    # so anyone who knew (or guessed) a scan id could read another user's
    # target URL and full report. A 404 is returned rather than 403 so the
    # endpoint does not confirm that an id exists.
    if not scan or scan.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Scan not found")

    # If completed, load the JSON results so the frontend can display them easily
    response = dict(scan)
    
    if scan.get("status") in ("running", "pending"):
        # Progress file is written inside the user's isolated output dir.
        # Check user_data path first, then fall back to legacy results/ for
        # scans started before the user_data migration.
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

@app.get("/api/scans/{scan_id}/download/{file_type}")
async def download_scan_file(scan_id: UUID, file_type: str, user=Depends(require_user)):
    if file_type not in ("json", "md"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be 'json' or 'md'")

    scan = get_scan(str(scan_id))
    if not scan or scan.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Scan is not completed")

    path_key = f"{file_type}_path"
    stored_path = scan.get(path_key)
    
    if not stored_path:
        raise HTTPException(status_code=404, detail="File not found")

    resolved = _resolve_report_path(stored_path)
    if not resolved or not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="File not found on disk")

    filename = os.path.basename(resolved)
    return FileResponse(
        path=resolved,
        filename=filename,
        media_type="application/json" if file_type == "json" else "text/markdown"
    )


@app.get("/")
def read_root():
    return {"message": "AI QA Agent SaaS API is running."}
