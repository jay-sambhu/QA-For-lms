import os
import sys
import logging
from typing import Optional
from pathlib import Path

# Ensure repo root is in sys.path
_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from worker.celery_app import celery_app
except ImportError:
    from .celery_app import celery_app

logger = logging.getLogger("ai_qa_agent.worker")

# Scan states in which a (re)delivered task must not relaunch the pipeline.
_TERMINAL_STATES = {"failed", "completed", "cancelled"}


def run_qa_pipeline(*args, **kwargs):
    """Wrapper that resolves run_qa_pipeline from api.main."""
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from api.main import run_qa_pipeline as _run_pipeline
    return _run_pipeline(*args, **kwargs)


def _scan_status(scan_id: str) -> Optional[str]:
    try:
        from api.main import _get_scan_status_value
    except ImportError:
        return None
    try:
        return _get_scan_status_value(scan_id)
    except Exception:
        return None


def _final_report_exists(user_id: str, scan_id: str) -> bool:
    path = os.path.join(_repo_root, "user_data", str(user_id), "results", f"final_qa_report_{scan_id}.json")
    return os.path.isfile(path)


@celery_app.task(
    bind=True,
    name="worker.tasks.process_query",
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
    gemini_api_key: Optional[str] = None,
    ai_keys_pool: Optional[list] = None,
    provider_id: Optional[str] = None,
    model_name: Optional[str] = None,
    endpoint: Optional[str] = None,
):
    """Celery task wrapper for the QA pipeline.
    This runs in a separate worker process, keeping the API request thread fast.

    The pipeline is not idempotent (it crawls a customer's site and uploads
    reports), so there is no automatic retry: a scan that already reached a
    terminal state, or that already produced its final report (a redelivery
    after the worker died mid-run with acks_late), is left alone.
    """
    status = _scan_status(scan_id)
    if status in _TERMINAL_STATES:
        logger.info("Scan %s is already %s; not relaunching the pipeline.", scan_id, status)
        return
    if _final_report_exists(user_id, scan_id):
        logger.info("Scan %s already has a final report on disk; not relaunching the pipeline.", scan_id)
        return

    try:
        run_qa_pipeline(
            scan_id,
            user_id,
            url,
            max_pages,
            auth_token,
            login_url,
            username,
            password,
            gemini_api_key=gemini_api_key,
            ai_keys_pool=ai_keys_pool,
            provider_id=provider_id,
            model_name=model_name,
            endpoint=endpoint,
        )
    except Exception as exc:
        logger.exception("Task failed for scan %s: %s", scan_id, exc)
        # If the pipeline fails, mark the scan as failed.
        try:
            try:
                from api.main import update_scan
            except ImportError:
                from ..api.main import update_scan
            update_scan(scan_id, "failed")
        except Exception as update_err:
            # Previously swallowed silently, leaving the scan stuck "running"
            # with no trace of why.
            logger.error("Could not mark scan %s as failed: %s", scan_id, update_err)
        raise exc
