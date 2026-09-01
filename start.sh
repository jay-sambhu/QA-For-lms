#!/usr/bin/env bash
# ==============================================================================
# NexusQA Enterprise Suite - Interactive Live Terminal Launcher
# ==============================================================================
# This script starts all backend and frontend services in the foreground so you
# can monitor live logs, debugging output, and exceptions directly in your terminal.
#
# Usage:
#   chmod +x start.sh
#   ./start.sh
# ==============================================================================

set -e

# Color definitions for live log streams
C_CYAN='\033[0;36m'
C_MAGENTA='\033[0;35m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[1;33m'
C_BLUE='\033[0;34m'
C_BOLD='\033[1m'
C_RESET='\033[0m'

echo -e "${C_CYAN}${C_BOLD}"
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                      JASUSS ENTERPRISE SUITE                          ║"
echo "║                    ( Powered by Nexus Engine )                        ║"
echo "║          Interactive Local Development & Debugging Terminal           ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo -e "${C_RESET}"

# Kill any existing background processes from previous runs
pkill -f "uvicorn api.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

# Cleanup child processes on exit (Ctrl+C)
cleanup() {
    echo -e "\n${C_YELLOW}[!] Shutting down all JASUSS services cleanly...${C_RESET}"
    kill $(jobs -p) 2>/dev/null || true
    echo -e "${C_GREEN}[✓] All processes stopped.${C_RESET}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo -e "${C_BLUE}[1/2] Starting FastAPI Backend on http://0.0.0.0:8000...${C_RESET}"
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | sed "s/^/$(echo -e "${C_CYAN}[API]${C_RESET} ")/" &
API_PID=$!

echo -e "${C_BLUE}[2/2] Starting Next.js Web Frontend on http://localhost:3000...${C_RESET}"
npm run dev --prefix web 2>&1 | sed "s/^/$(echo -e "${C_MAGENTA}[WEB]${C_RESET} ")/" &
WEB_PID=$!

echo ""
echo -e "${C_GREEN}${C_BOLD}✓ All Services Running in Foreground!${C_RESET}"
echo -e "${C_CYAN}  • Web Dashboard:  ${C_BOLD}http://localhost:3000${C_RESET}"
echo -e "${C_CYAN}  • API & Swagger:  ${C_BOLD}http://localhost:8000/docs${C_RESET}"
echo -e "${C_YELLOW}  • Press [Ctrl+C] anytime in this terminal to stop all servers.${C_RESET}"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Wait for background jobs so all logs stream continuously to the screen
wait $API_PID $WEB_PID
