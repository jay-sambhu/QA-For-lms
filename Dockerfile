# One image for both the API (uvicorn) and the Celery worker (Playwright).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    # Fewer glibc malloc arenas: noticeably lower RSS for Python + threads
    MALLOC_ARENA_MAX=2

WORKDIR /app

# psycopg2-binary ships wheels, so no compiler/libpq-dev is needed.
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* /root/.cache

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/results /app/screenshots /app/user_data \
    && chown -R app:app /app

COPY --chown=app:app . .
USER app

EXPOSE 8000

# Single uvicorn process: the API is I/O bound and scans run in the worker.
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
