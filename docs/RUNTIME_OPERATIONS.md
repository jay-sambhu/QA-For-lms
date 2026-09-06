# JASUSS Persistent Runtime Operations Guide

## Executive Overview
This document provides complete instructions for starting, monitoring, operating, and stopping the **JASUSS Autonomous Quality Engineering Platform** (`QA-For-lms`) in production and development environments.

---

## 1. System Architecture & Component Surface

| Service | Technology | Default Port | Health Endpoint / Verification |
|---|---|---|---|
| **Web Frontend** | Next.js 16 (Turbopack) | `3000` | `http://127.0.0.1:3000` |
| **Backend API** | FastAPI / Uvicorn | `8000` | `http://127.0.0.1:8000/docs` |
| **Worker Engine** | Celery / QA Pipeline | Background | Process table / Task logs |
| **Broker** | Redis | `6379` | TCP Ping / `run_local_redis.py` |
| **Database** | SQLite / PostgreSQL | Local File | `qa_agent.db` |

---

## 2. Server Operations & Lifecycle Management

### Starting JASUSS (Persistent Stack)
To launch all services persistently in the background:
```bash
# Option A: Built-in Operational Startup Script
bash scripts/start_jasuss.sh

# Option B: Persistent Daemons
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &
npm run dev --prefix web -- -p 3000 &
python3 -m celery -A worker.celery_app worker --loglevel=info -Q qa_queue &
python3 scripts/run_local_redis.py 6379 &
```

### Checking System Status
To view active process IDs, listening sockets, and HTTP health:
```bash
bash scripts/status_jasuss.sh
```

### Stopping JASUSS
To cleanly terminate running JASUSS processes:
```bash
bash scripts/stop_jasuss.sh
```

---

## 3. Production Build & Deployment

### Building Next.js Frontend
```bash
npm run build --prefix web
```

### Running Next.js Production Server
```bash
npm run start --prefix web
```

---

## 4. Verification & Testing

- **Real Browser Flow**: `python3 scripts/verify_ui_real_flow.py`
- **Pytest Suite**: `pytest -q`
