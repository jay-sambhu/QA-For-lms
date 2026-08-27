import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, BackgroundTasks, HTTPException, Header
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from supabase import create_client, Client

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

if not supabase_url or not supabase_key:
    raise RuntimeError("Supabase credentials not found in .env")

supabase: Client = create_client(supabase_url, supabase_key)

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
    response = supabase.table("scans").select("*").eq("id", scan_id).execute()
    if response.data:
        return response.data[0]
    return None


def update_scan(
    scan_id: str,
    status: str,
    report_path: Optional[str] = None,
    json_path: Optional[str] = None,
):
    data = {"status": status}
    if status == "completed":
        data["completed_at"] = datetime.now().isoformat()
        data["report_path"] = report_path
        data["json_path"] = json_path

    supabase.table("scans").update(data).eq("id", scan_id).execute()


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

    candidate = os.path.abspath(os.path.join(ROOT_DIR, stored_path))
    root_with_sep = os.path.join(ROOT_DIR, "")

    if candidate != ROOT_DIR and not candidate.startswith(root_with_sep):
        return None

    return candidate


def run_qa_pipeline(
    scan_id: str, url: str, max_pages: int, auth_token: Optional[str]
):
    """Run the QA pipeline as a background subprocess."""
    update_scan(scan_id, "running")

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
    if auth_token:
        cmd.extend(["--auth-token", auth_token])

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
    background_tasks: BackgroundTasks,
    user=Depends(require_user),
):
    scan_id = str(uuid4())

    supabase.table("scans").insert({
        "id": scan_id,
        "user_id": user.id,
        "url": request.url,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }).execute()

    background_tasks.add_task(
        run_qa_pipeline, scan_id, request.url, request.max_pages, request.auth_token
    )

    return {"scan_id": scan_id, "status": "pending", "message": "Scan queued successfully."}


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
async def get_scan_status(scan_id: str, user=Depends(require_user)):
    scan = get_scan(scan_id)

    # Require ownership. This endpoint previously had no authentication at all,
    # so anyone who knew (or guessed) a scan id could read another user's
    # target URL and full report. A 404 is returned rather than 403 so the
    # endpoint does not confirm that an id exists.
    if not scan or scan.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Scan not found")

    # If completed, load the JSON results so the frontend can display them easily
    response = dict(scan)
    
    if scan.get("status") in ("running", "pending"):
        progress_path = os.path.join(ROOT_DIR, "results", f"progress_{scan_id}.json")
        if os.path.exists(progress_path):
            try:
                with open(progress_path, "r", encoding="utf-8") as f:
                    response["progress"] = json.load(f)
            except Exception:
                pass

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


@app.get("/")
def read_root():
    return {"message": "AI QA Agent SaaS API is running."}
