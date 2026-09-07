#!/usr/bin/env bash
# ==============================================================================
# JASUSS Persistent Server Startup Script
# Starts FastAPI Backend (:8000), Next.js Frontend (:3000), and Celery Worker
# Saves PIDs to scripts/.jasuss_pids for persistent lifecycle management.
# ==============================================================================

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/scripts/.jasuss_pids"

# Color definitions
C_CYAN='\033[0;36m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[1;33m'
C_RED='\033[0;31m'
C_BOLD='\033[1m'
C_RESET='\033[0m'

echo -e "${C_CYAN}${C_BOLD}"
echo "======================================================================="
echo "                  JASUSS PERSISTENT RUNTIME LAUNCHER                  "
echo "======================================================================="
echo -e "${C_RESET}"

# Stop any existing JASUSS processes if running
if [ -f "$PID_FILE" ]; then
    bash "$ROOT_DIR/scripts/stop_jasuss.sh" >/dev/null 2>&1 || true
fi
rm -f "$PID_FILE"

# 1. Start FastAPI Backend on port 8000
echo -e "${C_CYAN}[1/3] Starting FastAPI Backend on http://127.0.0.1:8000...${C_RESET}"
nohup setsid python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 > "$ROOT_DIR/scripts/backend.log" 2>&1 &
BACKEND_PID=$!
disown $BACKEND_PID 2>/dev/null || true
echo "BACKEND_PID=$BACKEND_PID" >> "$PID_FILE"

# Wait for backend HTTP socket readiness
BACKEND_READY=false
for i in {1..30}; do
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs | grep -q "200"; then
        BACKEND_READY=true
        break
    fi
    sleep 0.5
done

if [ "$BACKEND_READY" = "true" ]; then
    echo -e "${C_GREEN}[✓] FastAPI Backend running (PID: $BACKEND_PID)${C_RESET}"
else
    echo -e "${C_RED}[✕] FastAPI Backend failed to respond on port 8000${C_RESET}"
    cat "$ROOT_DIR/scripts/backend.log"
    exit 1
fi

# 2. Start Celery Worker
echo -e "${C_CYAN}[2/3] Starting Celery Worker...${C_RESET}"
nohup setsid python3 -m celery -A worker.celery_app worker --loglevel=info -Q qa_queue > "$ROOT_DIR/scripts/worker.log" 2>&1 &
WORKER_PID=$!
disown $WORKER_PID 2>/dev/null || true
echo "WORKER_PID=$WORKER_PID" >> "$PID_FILE"
echo -e "${C_GREEN}[✓] Celery Worker started (PID: $WORKER_PID)${C_RESET}"

# 3. Start Next.js Frontend on port 3000
echo -e "${C_CYAN}[3/3] Starting Next.js Web Frontend on http://127.0.0.1:3000...${C_RESET}"
nohup setsid npm run dev --prefix web > "$ROOT_DIR/scripts/frontend.log" 2>&1 &
FRONTEND_PID=$!
disown $FRONTEND_PID 2>/dev/null || true
echo "FRONTEND_PID=$FRONTEND_PID" >> "$PID_FILE"

# Wait for frontend HTTP socket readiness
FRONTEND_READY=false
for i in {1..40}; do
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000 | grep -qE "200|304"; then
        FRONTEND_READY=true
        break
    fi
    sleep 0.5
done

if [ "$FRONTEND_READY" = "true" ]; then
    echo -e "${C_GREEN}[✓] Next.js Frontend running (PID: $FRONTEND_PID)${C_RESET}"
else
    echo -e "${C_RED}[✕] Next.js Frontend failed to respond on port 3000${C_RESET}"
    cat "$ROOT_DIR/scripts/frontend.log"
    exit 1
fi

echo -e "\n${C_GREEN}${C_BOLD}=======================================================================${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}✓ ALL JASUSS SERVICES RUNNING PERSISTENTLY${C_RESET}"
echo -e "${C_CYAN}  • Web UI:       ${C_BOLD}http://127.0.0.1:3000${C_RESET}"
echo -e "${C_CYAN}  • API Docs:     ${C_BOLD}http://127.0.0.1:8000/docs${C_RESET}"
echo -e "${C_CYAN}  • Backend PID:  $BACKEND_PID${C_RESET}"
echo -e "${C_CYAN}  • Frontend PID: $FRONTEND_PID${C_RESET}"
echo -e "${C_CYAN}  • Worker PID:   $WORKER_PID${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}=======================================================================${C_RESET}"
