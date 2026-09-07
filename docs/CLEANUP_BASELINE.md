# JASUSS Codebase Cleanup Baseline

**Date**: September 7, 2026  
**Commit SHA**: `617af6a`  
**Branch**: `main`  
**Repository**: `https://github.com/jay-sambhu/QA-For-lms`

---

## Executive Summary
This document establishes the repository baseline prior to the Phase 30 complete codebase cleanup, fine-tuning, stabilization, and production readiness audit.

---

## 1. Repository Structure & Entry Points

```text
JASUSS Repository Root
├── api/                   # FastAPI Backend Application
│   ├── main.py            # Primary REST API entry point & route handlers
│   ├── admin.py           # Admin console API routes
│   ├── billing.py         # Subscription & billing API routes
│   └── rate_limiter.py    # IP & token rate limiting dependency
├── web/                   # Next.js 16 Web Application Frontend
│   ├── src/app/           # App Router pages (/, /dashboard, /admin, /auth/callback)
│   ├── src/components/    # React components (auth, dashboard, UI)
│   ├── src/context/       # AuthContext state management
│   └── src/lib/           # Supabase client configuration
├── worker/                # Celery Asynchronous Task Worker
│   ├── celery_app.py      # Celery app instance & Redis broker config
│   └── tasks.py           # QA pipeline task definitions (process_query_task)
├── core/                  # Core Autonomous QA Engine
│   ├── agent/             # Agent orchestrator & LLM interaction
│   ├── discovery/         # Resumable crawler & route normalizer
│   ├── oracle/            # Assertion engine & bug detector
│   ├── planning/          # Risk planner & test case generator
│   └── export_validator.py# Export report validator (JSON, MD, PDF, XLSX)
├── crawler/               # Playwright browser crawler engine
├── security/              # Data redactor & security controls
├── db.py                  # SQLAlchemy engine & session factory (qa_agent.db)
├── models.py              # Database models (Scan, Subscription, Plan, User)
├── scripts/               # Operational lifecycle scripts (start, stop, status)
├── tests/                 # Comprehensive Pytest suite (227 tests across 43 modules)
├── docs/                  # System documentation & validation history
└── your_application/      # WSGI/Render deployment fallback entry point
```

---

## 2. Architecture & Runtime Services

| Service | Port / Address | Tech Stack | Entry Point |
| :--- | :--- | :--- | :--- |
| **Frontend Web UI** | `http://127.0.0.1:3000` | Next.js 16 (React 19, Turbopack, Tailwind) | `web/src/app/page.tsx` |
| **Backend REST API** | `http://127.0.0.1:8000` | FastAPI / Uvicorn (Python 3.14) | `api/main.py:app` |
| **Worker Process** | Asynchronous Queue | Celery 5.4 | `worker.tasks.process_query_task` |
| **Broker & Result** | `redis://127.0.0.1:6379/0` | Redis 7+ | System Redis / `fakeredis` in tests |
| **Database** | SQLite / PostgreSQL | SQLAlchemy 2.0 | `qa_agent.db` / `DATABASE_URL` |
| **Authentication** | Supabase OAuth & JWT | Supabase Auth Client | `web/src/lib/supabaseClient.ts` |

---

## 3. Key Operational Commands

### Development Runtime Lifecycle
```bash
# Start Full Stack (FastAPI, Next.js, Celery, Redis)
bash scripts/start_jasuss.sh

# Check Service Health & Process PIDs
bash scripts/status_jasuss.sh

# Stop Full Stack Cleanly
bash scripts/stop_jasuss.sh
```

### Test Suite Execution
```bash
# Full Backend Test Suite
pytest -v --tb=short

# Celery & Redis Integration Test
pytest tests/test_redis_celery_integration.py -v

# OAuth Security Protection Suite
pytest tests/test_phase27_oauth_security.py tests/test_phase28_oauth_validation.py -v
```

### Frontend Build
```bash
npm run build --prefix web
```

---

## 4. Initial Baseline Metrics

- **Total Python Tests**: 227 passed (0 failed).
- **Frontend Compilation**: Next.js 16 build successful (0 errors).
- **Process Health**: 0 orphan `pytest` or `celery` worker processes.
- **Git Status**: Working tree clean on `main` at `617af6a`.
