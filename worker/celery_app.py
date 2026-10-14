from celery import Celery
import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve project root (one level up from this file's parent directory)
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT_DIR / ".env")

try:
    from config import settings
    _redis_url = settings.REDIS_URL or os.getenv("REDIS_URL", "redis://localhost:6379/0")
except Exception:
    _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

BROKER_URL = _redis_url
BACKEND_URL = _redis_url

celery_app = Celery(
    "qa_worker",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=["worker.tasks"],
)

from kombu import Queue

# Multi-queue routing for standard and priority scans
celery_app.conf.task_default_queue = "qa_queue"
celery_app.conf.task_queues = (
    Queue("qa_queue"),
    Queue("celery"),
    Queue("priority_queue"),
)
celery_app.conf.task_routes = {
    "worker.tasks.process_query": {"queue": "qa_queue"},
    "worker.tasks.process_query_priority": {"queue": "priority_queue"},
}

# Recommended production scalability settings
celery_app.conf.update(
    result_expires=3600,               # keep results for 1 hour
    task_time_limit=1800,              # hard limit (seconds)
    task_soft_time_limit=1700,         # soft limit for graceful shutdown
    worker_prefetch_multiplier=1,      # avoid task hoarding
    task_acks_late=True,               # ensure tasks are re‑queued on failure
    worker_max_tasks_per_child=int(os.getenv("CELERY_MAX_TASKS_PER_CHILD", 10)),       # recycle child to release browser-automation leaks
    worker_max_memory_per_child=int(os.getenv("CELERY_MAX_MEMORY_PER_CHILD_KB", 400000)), # recycle child above ~400MB RSS
    worker_concurrency=int(os.getenv("WORKER_CONCURRENCY", 1)),  # each scan runs Chromium; 1 fits a 1-2 GB droplet
    task_ignore_result=True,           # scan status lives in the DB; don't keep task payloads in Redis
    task_track_started=False,
    worker_send_task_events=False,
    broker_transport_options={"visibility_timeout": 3600},  # > task_time_limit so acks_late tasks aren't redelivered mid-run

    # Retry the broker on worker startup (Redis may come up after the worker)
    broker_connection_retry_on_startup=True,
    # Prevent delay() from hanging indefinitely if Redis is down
    broker_connection_max_retries=1,
    broker_connection_timeout=2.0,
    
    # Also prevent the result backend from retrying indefinitely
    redis_retry_on_timeout=False,
    redis_socket_timeout=2.0,
    result_backend_max_retries=1,
)

