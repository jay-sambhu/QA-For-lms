from ..config import settings
from ..run_qa import run_qa_pipeline
from .celery_app import celery_app

@celery_app.task(name="worker.tasks.process_query")
def process_query_task(scan_id: str, user_id: str, url: str, max_pages: int, auth_token: str | None = None):
    """Celery task wrapper for the QA pipeline.
    This runs in a separate worker process, keeping the API request thread fast.
    """
    # Delegates to the existing run_qa_pipeline function which handles
    # updating the supabase / database record.
    try:
        run_qa_pipeline(scan_id, user_id, url, max_pages, auth_token)
    except Exception as exc:
        # Logging inside run_qa_pipeline already captures errors; re‑raise to mark task as failed.
        raise exc
