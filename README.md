# 🛡️ JASUSS — Enterprise Web Quality Assurance Platform

**Continuous automated testing, multi-viewport verification and AI-assisted defect triage.**
Powered by the **Nexus Engine**.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12+-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![Next.js](https://img.shields.io/badge/Next.js-16-black)
![Playwright](https://img.shields.io/badge/Playwright-Chromium-45ba4b)
![Celery](https://img.shields.io/badge/Celery-Redis-37814A)

---

## Table of contents

1. [What JASUSS does](#1-what-jasuss-does)
2. [Architecture at a glance](#2-architecture-at-a-glance)
3. [Documentation map](#3-documentation-map)
4. [Quick start (Docker)](#4-quick-start-docker)
5. [Local development (no Docker)](#5-local-development-no-docker)
6. [Configuration](#6-configuration)
7. [API overview](#7-api-overview)
8. [Plans and billing](#8-plans-and-billing)
9. [Testing and quality gates](#9-testing-and-quality-gates)
10. [Production readiness checklist](#10-production-readiness-checklist)
11. [Repository structure](#11-repository-structure)
12. [Contributing](#12-contributing)
13. [License](#13-license)

---

## 1. What JASUSS does

JASUSS audits a web application end to end. Given a target URL (and optional login credentials) it:

1. **Crawls** the site in three viewports in parallel: Desktop 1920×1080, iPhone 13 390×844, iPad Gen 7 820×1180.
2. **Exercises** the UI with synthetic interactions: buttons, links, forms, dialogs.
3. **Detects defects** deterministically: HTTP 4xx/5xx, unhandled JS exceptions, layout overflow and clipping.
4. **Collects evidence**: screenshots, network/HAR telemetry, and diffs against previous scans (regression detection).
5. **Triages with AI**: Gemini-assisted root-cause analysis, P0–P4 severity, reproduction steps.
6. **Scores** the site with a canonical 0–100 quality score and letter grade (A+ … F).
7. **Exports** PDF, Excel, JSON and Markdown reports.

## 2. Architecture at a glance

```mermaid
flowchart LR
    U["User / CI pipeline"] --> WEB["Next.js dashboard"]
    WEB -->|"HTTPS + JWT"| API["FastAPI API"]
    API -->|"enqueue"| RQ[("Redis broker")]
    RQ --> W["Celery workers + Playwright"]
    W --> T["Target website"]
    W --> AI["Gemini API"]
    API <--> DB[("PostgreSQL")]
    W --> DB
    W --> OBJ[("Object storage: reports and evidence")]
    API --> PAY["Stripe / LemonSqueezy / Razorpay / PayPal"]
    WEB --> AUTH["Supabase Auth"]
```

Full C4 diagrams, sequence diagrams and state machines: see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 3. Documentation map

| Document | Purpose |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Context, container, component, DFD, sequence and state diagrams |
| [docs/DATABASE.md](docs/DATABASE.md) | ERD (current and proposed), indexes, retention, migrations |
| [docs/API.md](docs/API.md) | REST contract, auth, errors, rate limits, webhooks |
| [docs/SECURITY.md](docs/SECURITY.md) | Threat model, SSRF defence, secrets, RBAC, compliance |
| [docs/BILLING.md](docs/BILLING.md) | Multi-gateway checkout, webhook idempotency, subscription lifecycle |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Topology, Docker, Kubernetes, CI/CD, environment variables |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | SLOs, metrics, alerts, runbooks, backup and DR |
| [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md) | Production audit matrix, code vs docs truth alignment, baseline test results |

## 4. Quick start (Docker)

Prerequisites: Docker 24+ and Docker Compose v2.

```bash
git clone https://github.com/jay-sambhu/QA-For-lms.git
cd QA-For-lms
cp .env.example .env          # then edit values, see section 6
docker compose up --build -d
docker compose exec api alembic upgrade head
```

| Service | URL |
|---|---|
| Web dashboard | http://localhost:3000 |
| API (Swagger UI) | http://localhost:8000/docs |
| Health | http://localhost:8000/healthz |

Run a scan from the CLI without the UI:

```bash
docker compose exec api python run_qa.py --url https://example.com
```

## 5. Local development (no Docker)

Prerequisites: Python 3.12, Node.js 18+, Redis.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
npm install --prefix web
alembic upgrade head
chmod +x start.sh && ./start.sh      # API :8000, web :3000, worker
```

## 6. Configuration

All configuration is via environment variables (12-factor). Never commit `.env`.
The complete, annotated list lives in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#5-environment-variables); the essentials:

| Variable | Required | Description |
|---|---|---|
| `ENVIRONMENT` | yes | `development` / `staging` / `production` |
| `DATABASE_URL` | yes | PostgreSQL DSN in production (`postgresql+psycopg://…`) |
| `REDIS_URL` | yes | Broker and rate-limit store |
| `GEMINI_API_KEY` | yes | AI triage; if unset, deterministic-only mode |
| `SUPABASE_JWT_SECRET` / JWKS URL | yes | JWT validation |
| `CORS_ALLOWED_ORIGINS` | yes | Comma-separated exact origins, never `*` in production |
| `STORAGE_BACKEND` | prod | `local` or `s3` (use `s3` when more than one worker node) |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | optional | Billing |

## 7. API overview

Base path `/api/v1`. All routes require `Authorization: Bearer <JWT>` except health and payment webhooks.

| Method | Path | Description |
|---|---|---|
| `POST` | `/scans` | Create and enqueue a scan |
| `GET` | `/scans` | List the caller's scans |
| `GET` | `/scans/{id}` | Status and results |
| `POST` | `/scans/{id}/cancel` | Cancel a running scan |
| `GET` | `/scans/{id}/report?format=pdf\|xlsx\|json\|md` | Download report |
| `POST` | `/billing/checkout` | Start a checkout session |
| `POST` | `/billing/webhooks/{gateway}` | Gateway webhook receiver |
| `GET` | `/admin/metrics` | Admin telemetry (role `admin`) |

Details, schemas and error model: [docs/API.md](docs/API.md).

## 8. Plans and billing

| Plan | Price | Scans / month | Crawl depth | Highlights |
|---|---|---|---|---|
| Community Starter | $0 | 10 | 10 pages | Multi-viewport, triage, quality score |
| Professional QA | $49/mo | 200 | 50 pages | Authenticated crawl, PDF/Excel export, priority queue |
| Enterprise Suite | $199/mo | Unlimited | Deep | Dedicated workers, custom auth, SLA |

Gateways: Stripe, LemonSqueezy, Razorpay, PayPal. See [docs/BILLING.md](docs/BILLING.md).

## 9. Testing and quality gates

```bash
pytest -q                                   # backend suite
pytest -q --cov=. --cov-report=term-missing # with coverage
ruff check . && ruff format --check .       # lint / format
mypy .                                      # type check
npm run lint --prefix web && npm run build --prefix web
python ci_quality_gate.py                   # project quality gate
```

Every pull request must pass: lint, type check, unit and integration tests, migration test (`test_database_migrations.py`), frontend build, dependency and container vulnerability scan. See the CI pipeline in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#7-cicd-pipeline).

## 10. Implementation status
 
For an audited breakdown of implemented versus planned capabilities across SSRF defense, JWT verification, tenant isolation, rate limiting, payment webhooks, Celery, database migrations, and observability, see:
- 📊 **[Production Implementation Status Matrix](docs/IMPLEMENTATION_STATUS.md)**

## 11. Production readiness checklist

Use this before go-live. Items marked ⚠️ are the most common gaps.

**Security**
- [ ] ⚠️ Crawler blocks private/link-local/metadata IPs (SSRF), including after redirects and DNS rebinding ([SECURITY.md](docs/SECURITY.md#3-ssrf-defence-for-the-crawler))
- [ ] ⚠️ Workers run as non-root, in a network-restricted sandbox
- [ ] ⚠️ Webhook signatures verified for every gateway, events deduplicated
- [ ] Secrets in a secret manager, not in the image or repo
- [ ] CORS locked to exact origins; HTTPS and HSTS enforced
- [ ] Rate limits backed by Redis (not in-process memory)
- [ ] Dependency, secret and container scans green in CI

**Reliability**
- [ ] PostgreSQL (not SQLite), automated backups, restore tested
- [ ] Reports and evidence in object storage, not local disk
- [ ] Celery: `acks_late`, visibility timeout, per-task time limits, retry with backoff
- [ ] Stuck-scan reaper marks orphaned `running` scans as `failed`
- [ ] Health, readiness and liveness probes configured

**Observability**
- [ ] Structured JSON logs with `request_id` and `scan_id`
- [ ] Prometheus metrics, dashboards and alerts ([OPERATIONS.md](docs/OPERATIONS.md))
- [ ] Error tracking (Sentry or equivalent)

**Delivery**
- [ ] Immutable, tagged container images; migrations run as a release step
- [ ] Staging environment mirrors production
- [ ] Rollback procedure rehearsed

## 11. Repository structure

Current layout has Python modules and tests at the repository root. The recommended production layout (see [Restructuring notes](docs/DEPLOYMENT.md#10-repository-hygiene)) is:

```
jasuss/
├── apps/
│   ├── api/            # FastAPI: routers, schemas, dependencies
│   ├── worker/         # Celery app and tasks
│   └── web/            # Next.js frontend
├── jasuss/             # Core python package
│   ├── crawler/  interactive/  detection/  triage/  evidence/
│   ├── scoring/        # calculation_engine
│   ├── reporting/      # pdf, xlsx, json, md
│   ├── billing/        # gateway adapters
│   └── security/       # redactor, ssrf guard
├── alembic/
├── tests/              # unit/, integration/, e2e/
├── deploy/             # docker, k8s, terraform
├── docs/
├── .github/workflows/
├── pyproject.toml
├── docker-compose.yml
└── .env.example
```

## 12. Contributing

1. Fork and create a branch: `git checkout -b feat/short-description`
2. Follow [Conventional Commits](https://www.conventionalcommits.org/)
3. Ensure `pytest -q`, lint and `npm run build --prefix web` pass
4. Open a pull request using the template; at least one review required

## 13. License

MIT. See [LICENSE](LICENSE).
