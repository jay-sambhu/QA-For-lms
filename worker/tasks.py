import logging
from typing import Optional

try:
    from config import settings
    from worker.celery_app import celery_app
except ImportError:
    from ..config import settings
    from .celery_app import celery_app

logger = logging.getLogger("ai_qa_agent.worker")

def run_qa_pipeline(scan_id: str, user_id: str, url: str, max_pages: int, auth_token: Optional[str] = None):
    """Wrapper that resolves run_qa_pipeline from api.main."""
    try:
        from api.main import run_qa_pipeline as _run_pipeline
    except ImportError:
        from ..api.main import run_qa_pipeline as _run_pipeline
    return _run_pipeline(scan_id, user_id, url, max_pages, auth_token)

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
    auth_token: Optional[str] = None
):
    """Celery task wrapper for the QA pipeline.
    This runs in a separate worker process, keeping the API request thread fast.
    """
    try:
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


