#!/usr/bin/env bash
# ==============================================================================
# JASUSS Graceful Server Shutdown Script
# Safely terminates running JASUSS processes (backend, frontend, worker).
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/scripts/.jasuss_pids"

C_YELLOW='\033[1;33m'
C_GREEN='\033[0;32m'
C_RESET='\033[0m'

echo -e "${C_YELLOW}[!] Stopping all JASUSS processes...${C_RESET}"

# Stop processes recorded in PID file
if [ -f "$PID_FILE" ]; then
    while IFS= read -r line; do
        PID=$(echo "$line" | cut -d'=' -f2)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
fi

# Cleanup matching process names safely
pkill -f "uvicorn api.main:app" 2>/dev/null || true
pkill -f "celery -A worker.celery_app worker" 2>/dev/null || true
pkill -f "next-server|next dev" 2>/dev/null || true

echo -e "${C_GREEN}[✓] All JASUSS services stopped cleanly.${C_RESET}"
