import sys
import logging
from typing import Optional
from pathlib import Path

# Ensure repo root is in sys.path
_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from config import settings
    from worker.celery_app import celery_app
except ImportError:
    from .celery_app import celery_app

logger = logging.getLogger("ai_qa_agent.worker")

def run_qa_pipeline(*args, **kwargs):
    """Wrapper that resolves run_qa_pipeline from api.main."""
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from api.main import run_qa_pipeline as _run_pipeline
    return _run_pipeline(*args, **kwargs)

@celery_app.task(
    bind=True,
    name="worker.tasks.process_query",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={"max_retries": 3, "countdown": 5},
)
def process_query_task(
    self,
    scan_id: str,
    user_id: str,
    url: str,
    max_pages: int,
    auth_token: Optional[str] = None,
    login_url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    """Celery task wrapper for the QA pipeline.
    This runs in a separate worker process, keeping the API request thread fast.
    """
    try:
        if login_url is not None or username is not None or password is not None:
            run_qa_pipeline(
                scan_id,
                user_id,
                url,
                max_pages,
                auth_token,
                login_url,
                username,
                password,
            )
        else:
            run_qa_pipeline(scan_id, user_id, url, max_pages, auth_token)
    except Exception as exc:
        logger.exception("Task failed for scan %s: %s", scan_id, exc)
        # If the pipeline fails, mark the scan as failed.
        try:
            try:
                from api.main import update_scan
            except ImportError:
                from ..api.main import update_scan
            update_scan(scan_id, "failed")
        except Exception:
            pass
        raise exc


