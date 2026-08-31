from celery import Celery
import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve project root (two levels up from this file)
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT_DIR / ".env")

# Redis broker/backend URL (default to localhost if not set)
BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BACKEND_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("qa_worker", broker=BROKER_URL, backend=BACKEND_URL)

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
