#!/usr/bin/env bash
# ==============================================================================
# JASUSS Server Status Checker
# Reports health, process status, listening ports, and HTTP responsiveness.
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/scripts/.jasuss_pids"

C_CYAN='\033[0;36m'
C_GREEN='\033[0;32m'
C_RED='\033[0;31m'
C_YELLOW='\033[1;33m'
C_BOLD='\033[1m'
C_RESET='\033[0m'

echo -e "${C_CYAN}${C_BOLD}"
echo "======================================================================="
echo "                     JASUSS RUNTIME STATUS REPORT                      "
echo "======================================================================="
echo -e "${C_RESET}"

# Check Backend API (:8000)
BACKEND_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs 2>/dev/null || echo "000")
BACKEND_PID=$(pgrep -f "uvicorn api.main:app" | head -n 1 || echo "NONE")
if [ "$BACKEND_HTTP" = "200" ]; then
    echo -e "${C_GREEN}[✓] Backend API (port 8000):   RUNNING (PID: $BACKEND_PID, HTTP 200)${C_RESET}"
else
    echo -e "${C_RED}[✕] Backend API (port 8000):   STOPPED / DOWN (HTTP $BACKEND_HTTP)${C_RESET}"
fi

# Check Frontend Web UI (:3000)
FRONTEND_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000 2>/dev/null || echo "000")
FRONTEND_PID=$(pgrep -f "next-server|next dev|next start" | head -n 1 || echo "NONE")
if [ "$FRONTEND_HTTP" = "200" ] || [ "$FRONTEND_HTTP" = "304" ]; then
    echo -e "${C_GREEN}[✓] Frontend Web UI (port 3000): RUNNING (PID: $FRONTEND_PID, HTTP $FRONTEND_HTTP)${C_RESET}"
else
    echo -e "${C_RED}[✕] Frontend Web UI (port 3000): STOPPED / DOWN (HTTP $FRONTEND_HTTP)${C_RESET}"
fi

# Check Celery Worker Process
WORKER_PID=$(pgrep -f "celery -A worker.celery_app" | head -n 1 || echo "NONE")
if [ "$WORKER_PID" != "NONE" ]; then
    echo -e "${C_GREEN}[✓] Celery Worker:             RUNNING (PID: $WORKER_PID)${C_RESET}"
else
    echo -e "${C_YELLOW}[!] Celery Worker:             NOT DETECTED (Fallback to Async Background Tasks)${C_RESET}"
fi

# Check Redis Server
REDIS_PID=$(pgrep -f "run_local_redis.py" | head -n 1 || echo "NONE")
if nc -z 127.0.0.1 6379 2>/dev/null || ss -lntp | grep -q ":6379"; then
    echo -e "${C_GREEN}[✓] Redis Broker (port 6379):  RUNNING (PID: $REDIS_PID)${C_RESET}"
else
    echo -e "${C_YELLOW}[!] Redis Broker (port 6379):  OFFLINE (Fallback to Async Background Tasks)${C_RESET}"
fi

# Check SQLite Database Persistence File
if [ -f "$ROOT_DIR/qa_agent.db" ]; then
    DB_SIZE=$(du -h "$ROOT_DIR/qa_agent.db" | cut -f1)
    echo -e "${C_GREEN}[✓] Database (qa_agent.db):    ACTIVE ($DB_SIZE)${C_RESET}"
else
    echo -e "${C_RED}[✕] Database (qa_agent.db):    MISSING${C_RESET}"
fi

echo -e "${C_CYAN}=======================================================================${C_RESET}"
