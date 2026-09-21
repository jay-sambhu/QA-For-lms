#!/usr/bin/env python3
"""
watchdog.py — Uptime & Health Watchdog Microservice
=====================================================
Runs as a long-lived background worker on Render (or any Linux host).

Responsibilities
----------------
1. Keep-alive ping — Hits /healthz every PING_INTERVAL seconds (default
   900 = 15 min) so Render's free-tier web service never spins down from
   inactivity.

2. Failure detection & retry — On a failed ping, retries up to MAX_RETRIES
   times with exponential back-off (30s -> 60s -> 120s ...).
   After exhausting retries it logs a CRITICAL alert and waits for the
   next scheduled window.

3. Readiness probe — Also pings /readyz periodically and logs degraded
   components (DB, Redis) so operators can spot partial failures.

Environment variables (all optional)
--------------------------------------
    API_BASE_URL      Full base URL of the FastAPI service.
                      Default: https://ai-qa-api.onrender.com
    PING_INTERVAL     Seconds between successful pings. Default: 900 (15 min)
    REQUEST_TIMEOUT   Per-request HTTP timeout in seconds. Default: 30
    MAX_RETRIES       Retry attempts on failure. Default: 3
    WATCHDOG_LOG_LEVEL  Python log level string. Default: INFO

Running locally
---------------
    python -m worker.watchdog
    # or
    PING_INTERVAL=60 python worker/watchdog.py
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from typing import Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_LEVEL = os.environ.get("WATCHDOG_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s [WATCHDOG] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("watchdog")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def _build_base_url() -> str:
    """Resolve the API base URL from env vars or Render service conventions."""
    explicit = os.environ.get("API_BASE_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    # Render injects RENDER_SERVICE_NAME for every service; the web service is
    # named "ai-qa-api" in render.yaml => URL is https://ai-qa-api.onrender.com
    service_name = os.environ.get("RENDER_SERVICE_NAME", "ai-qa-api").strip()
    return f"https://{service_name}.onrender.com"


API_BASE_URL: str = _build_base_url()
PING_INTERVAL: int = int(os.environ.get("PING_INTERVAL", "900"))    # 15 min
REQUEST_TIMEOUT: float = float(os.environ.get("REQUEST_TIMEOUT", "30"))
MAX_RETRIES: int = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_BASE_DELAY: float = 30.0  # seconds; doubles on each retry

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
_shutdown_requested = False


def _handle_signal(signum: int, _frame) -> None:
    global _shutdown_requested
    logger.info("Received signal %s — shutting down watchdog cleanly.", signum)
    _shutdown_requested = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _get(url: str, timeout: float = REQUEST_TIMEOUT) -> tuple:
    """Perform a GET request; return (status_code, json_body_or_empty_dict)."""
    req = urllib.request.Request(url, headers={"User-Agent": "JASUSS-Watchdog/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
            return resp.status, body
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            body = {}
        return exc.code, body
    except urllib.error.URLError as exc:
        raise ConnectionError(f"Network error: {exc.reason}") from exc


def ping_healthz() -> bool:
    """Return True if /healthz responds 200, False otherwise."""
    url = f"{API_BASE_URL}/healthz"
    try:
        status, body = _get(url)
        if status == 200:
            logger.info("OK /healthz -> %s (HTTP %s)", body.get("status", "ok"), status)
            return True
        logger.warning("FAIL /healthz -> HTTP %s  body=%s", status, body)
        return False
    except ConnectionError as exc:
        logger.error("FAIL /healthz -> %s", exc)
        return False
    except Exception as exc:
        logger.error("FAIL /healthz -> unexpected error: %s", exc, exc_info=True)
        return False


def probe_readyz() -> Optional[dict]:
    """Probe /readyz and log any degraded components; returns body or None."""
    url = f"{API_BASE_URL}/readyz"
    try:
        status, body = _get(url)
        if status == 200:
            logger.info("OK /readyz -> all components healthy")
        else:
            degraded = {k: v for k, v in body.items() if "error" in str(v) or "unavailable" in str(v)}
            logger.warning("WARN /readyz -> HTTP %s  degraded=%s", status, degraded)
        return body
    except ConnectionError as exc:
        logger.error("FAIL /readyz -> %s", exc)
        return None
    except Exception as exc:
        logger.error("FAIL /readyz -> unexpected error: %s", exc, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Core watchdog loop
# ---------------------------------------------------------------------------
def ping_with_retry() -> bool:
    """
    Attempt to ping /healthz up to MAX_RETRIES+1 times with exponential
    back-off.  Returns True if any attempt succeeded.
    """
    delay = RETRY_BASE_DELAY
    for attempt in range(1, MAX_RETRIES + 2):
        if _shutdown_requested:
            return False
        success = ping_healthz()
        if success:
            return True
        if attempt <= MAX_RETRIES:
            logger.warning(
                "Ping attempt %d/%d failed — retrying in %.0f s ...",
                attempt,
                MAX_RETRIES + 1,
                delay,
            )
            _interruptible_sleep(delay)
            delay = min(delay * 2, 300)  # cap at 5 minutes
    logger.critical(
        "CRITICAL: All %d ping attempts failed. API may be down. "
        "Check https://status.render.com and Render service logs.",
        MAX_RETRIES + 1,
    )
    return False


def _interruptible_sleep(seconds: float) -> None:
    """Sleep in 1-second chunks so SIGTERM is handled promptly."""
    remaining = seconds
    while remaining > 0 and not _shutdown_requested:
        chunk = min(1.0, remaining)
        time.sleep(chunk)
        remaining -= chunk


def run() -> None:
    logger.info(
        "Watchdog starting — target: %s  interval: %ds  retries: %d",
        API_BASE_URL,
        PING_INTERVAL,
        MAX_RETRIES,
    )

    # Immediate ping on startup to catch config errors early.
    ping_with_retry()
    probe_readyz()

    cycle = 0
    while not _shutdown_requested:
        _interruptible_sleep(PING_INTERVAL)
        if _shutdown_requested:
            break

        cycle += 1
        logger.info("--- Watchdog cycle #%d ---", cycle)
        success = ping_with_retry()

        # Full readiness probe every 4 cycles (~1 hour) or after a failure.
        if cycle % 4 == 0 or not success:
            probe_readyz()

    logger.info("Watchdog stopped cleanly.")


if __name__ == "__main__":
    run()
