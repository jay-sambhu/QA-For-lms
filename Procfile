web: uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
worker: celery -A worker.celery_app worker --loglevel=info -Q qa_queue,priority_queue,celery --concurrency=${WORKER_CONCURRENCY:-1} --without-gossip --without-mingle
