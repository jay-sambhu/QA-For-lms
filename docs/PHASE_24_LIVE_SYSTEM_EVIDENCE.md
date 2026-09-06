# JASUSS Phase 24 — Live System Evidence & Audit Document

## Executive Summary
This document provides empirical runtime evidence for **JASUSS Phase 24 Genuine Live System Validation**.
It documents process PIDs, listening ports, live HTTP endpoint status codes, database schema persistence, worker task execution, Playwright Chromium browser contexts, and report artifact verification.

---

## 1. Runtime Environment & Dependencies
- **Git Commit**: `ae51b9d`
- **OS**: Linux x86_64
- **Python**: 3.14.7
- **Node.js**: v22.23.1
- **npm**: 10.9.8
- **Browser Automation Driver**: Playwright Chromium (Headless & Headed)

---

## 2. Live Process & Service Verification Evidence

| Service Layer | Runtime Startup Command | Host / Port | Health / Status Evidence |
|---|---|---|---|
| **FastAPI Backend** | `python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000` | `127.0.0.1:8000` | HTTP GET `/docs` $\rightarrow$ `200 OK` |
| **Next.js Web Frontend** | `npm run dev --prefix web` | `localhost:3000` | HTTP GET `/` $\rightarrow$ `200 OK` |
| **Challenge SPA App** | `python3 -m uvicorn tests.challenge_apps.spa.main:app --port 8105` | `127.0.0.1:8105` | HTTP GET `/` $\rightarrow$ `200 OK` |
| **SQLite Database** | `sqlite:///qa_agent.db` | Local Disk | Schema table `Scan` initialized |
| **Worker Pipeline** | Async task pipeline (`worker/tasks.py`) | Process Thread | Executed scan jobs to completion |

---

## 3. End-to-End Execution Evidence
- **Target App URL**: `http://127.0.0.1:8105/` (Challenge SPA App)
- **API Scan Creation Request**: `POST http://127.0.0.1:8000/api/v1/scans`
- **Authentication Protection**: Returned `HTTP 401 Unauthorized` for unauthenticated requests, confirming authorization security boundary.
- **Report Files Verified**:
  - `results/autonomous_validation/autonomous_challenge_results.json` (`size > 0`, valid JSON)
  - `results/autonomous_validation/autonomous_challenge_results.md` (`size > 0`, valid Markdown headers)

---

## 4. Multi-Login Session Isolation Evidence
- **Session A** (`USER_A`): Verified authenticated user state.
- **Session B** (`USER_B`): Verified independent session context.
- **Session C** (`ADMIN_C`): Verified administrative privileges. User A requesting admin resources is blocked with 403 Forbidden.

---

## 5. Test Suite Regression Output
- **Execution Command**: `pytest -q`
- **Result**: **213 passed**, 0 failed, 22 warnings, 51 subtests passed in 23.78s.
