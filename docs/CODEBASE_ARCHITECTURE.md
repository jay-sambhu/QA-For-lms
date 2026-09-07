# JASUSS System Architecture & Component Specification

This document provides a canonical architectural specification of **JASUSS** (Just Another Smart QA System for LMS & Web Apps).

---

## 1. High-Level System Architecture

```text
                               ┌─────────────────────────┐
                               │   Next.js 16 Web UI     │
                               │   (Port 3000)           │
                               └────────────┬────────────┘
                                            │ HTTP / REST & JWT
                                            ▼
                               ┌─────────────────────────┐
                               │     FastAPI Backend     │
                               │   (Port 8000 / Uvicorn) │
                               └───────┬────────────┬────┘
                                       │            │
                         Auth & JWT    │            │ Task Dispatch
                        Verification   │            │ Queue
                                       ▼            ▼
                   ┌─────────────────────┐   ┌───────────────────────┐
                   │    Supabase Auth    │   │  Redis 7+ Queue       │
                   │ (OAuth & Session)   │   │  (qa_queue)           │
                   └─────────────────────┘   └──────────┬────────────┘
                                                        │
                                                        │ Async Worker
                                                        ▼
                                             ┌───────────────────────┐
                                             │ Celery Worker Engine  │
                                             │ (worker.celery_app)   │
                                             └──────────┬────────────┘
                                                        │
                                                        ▼
                                             ┌───────────────────────┐
                                             │ Core Autonomous QA    │
                                             │ Pipeline Engine       │
                                             └──────────┬────────────┘
                                                        │
                                    ┌───────────────────┼───────────────────┐
                                    ▼                   ▼                   ▼
                         ┌─────────────────────┐┌───────────────┐┌─────────────────────┐
                         │ Playwright Browser  ││ SQLAlchemy DB ││ Export Validator    │
                         │ Crawler & Evidence  ││ (qa_agent.db) ││ (JSON, MD, PDF, XLSX│
                         └─────────────────────┘└───────────────┘└─────────────────────┘
```

---

## 2. Core Components & Responsibilities

### 2.1 Web UI (`web/`)
- **Technology**: Next.js 16 (React 19, Turbopack, TailwindCSS).
- **Key Modules**:
  - `src/app/page.tsx`: Modern landing page with feature cards, CTA, and pricing navigation.
  - `src/app/dashboard/page.tsx`: Overview of recent scans, live progress indicators, and scan launcher.
  - `src/app/dashboard/scan/[id]/page.tsx`: Detailed scan view with defect timeline, evidence viewer, and export downloads.
  - `src/components/auth/AuthModal.tsx`: Authentication modal providing Email/Password and Google/GitHub social login.
  - `src/context/AuthContext.tsx`: Client-side authentication state manager backed by Supabase JS SDK.

### 2.2 Backend API (`api/`)
- **Technology**: FastAPI, Uvicorn, Pydantic v2.
- **Key Routes**:
  - `POST /api/v1/scans`: Validate request payload (SSRF protection, URL normalization), authenticate caller via `require_user`, create database record, and dispatch `process_query_task` to Celery.
  - `GET /api/v1/scans/{id}`: Fetch scan status, progress, findings, and artifact URIs.
  - `GET /api/v1/scans/{id}/export/{format}`: Stream authorized scan exports (JSON, Markdown, PDF, XLSX).
  - `/api/billing`: Subscription plans, checkout sessions, and webhook processing.
  - `/api/admin`: Admin stats, user management, and system metrics.

### 2.3 Asynchronous Queue & Worker (`worker/`)
- **Technology**: Celery 5.4, Kombu, Redis 7+.
- **Key Files**:
  - `worker/celery_app.py`: Celery instance configuration, broker/backend URL resolution, task default queue (`qa_queue`).
  - `worker/tasks.py`: Asynchronous task execution entry point (`process_query_task`), pipeline orchestration, error boundary handling, and SQLite status synchronization.

### 2.4 Autonomous QA Engine (`core/`)
- **Pipeline Progression**:
  1. `crawler/crawler.py`: Crawl target domain using Playwright headless Chromium.
  2. `core/discovery/resumable_crawler.py` & `route_normalizer.py`: State discovery and route deduplication.
  3. `core/planning/risk_planner.py`: Generate targeted test plans based on discovered UI elements.
  4. `core/interactive_tester.py`: Execute form inputs, button clicks, and SPA state transitions while capturing console/network events.
  5. `core/evidence_engine.py`: Capture screenshots, HTTP payloads, and reproduction steps for findings.
  6. `core/bug_detector.py` & `bug_triage.py`: Classify defects (Critical, High, Medium, Info) and compute quality score.
  7. `core/export_validator.py`: Generate and validate JSON, Markdown, PDF, and XLSX report exports.

### 2.5 Security & Data Isolation
- **SSRF Protection**: `ScanRequest` validator blocks loopback (`127.0.0.1`), link-local (`169.254.169.254`), private IP subnets, and cloud metadata hostnames (`metadata.google.internal`).
- **Dev Token Guard**: Dev tokens (`dev-token`, `test-token`) are strictly forbidden when `ENVIRONMENT=production`.
- **Identity Isolation**: Backend enforces user identity via Supabase JWT or authorized bearer headers.

---

## 3. Data Model (`models.py`)

- **`Scan`**: Stores `scan_id` (UUID), `url`, `status` (`pending`, `running`, `completed`, `failed`), `max_pages`, `user_id`, `created_at`, `completed_at`, `findings` (JSON), `metrics` (JSON), `report_url` (JSON), and `quality_score` (Float).
- **`User`**: User profile, role (`student`, `pro`, `enterprise`), and subscription metadata.
- **`Subscription`** & **`Plan`**: SaaS subscription management and billing tier limits.
