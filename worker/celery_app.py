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

# Simple routing – all QA jobs go to the "qa_queue"
celery_app.conf.task_routes = {"worker.tasks.process_query": {"queue": "qa_queue"}}

# Recommended production settings
celery_app.conf.update(
    result_expires=3600,               # keep results for 1 hour
    task_time_limit=1800,              # hard limit (seconds)
    task_soft_time_limit=1700,         # soft limit for graceful shutdown
    worker_prefetch_multiplier=1,      # avoid task hoarding
    task_acks_late=True,               # ensure tasks are re‑queued on failure
)

