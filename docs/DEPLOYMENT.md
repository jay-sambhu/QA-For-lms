# Deployment

## Contents

1. [Environments](#1-environments)
2. [Production topology](#2-production-topology)
3. [Container images](#3-container-images)
4. [Docker Compose (single host)](#4-docker-compose-single-host)
5. [Environment variables](#5-environment-variables)
6. [Kubernetes (scale-out)](#6-kubernetes-scale-out)
7. [CI/CD pipeline](#7-cicd-pipeline)
8. [Release and rollback](#8-release-and-rollback)
9. [Cost and sizing](#9-cost-and-sizing)
10. [Repository hygiene](#10-repository-hygiene)

---

## 1. Environments

| Env | Purpose | Data | Notes |
| --- | --- | --- | --- |
| `local` | Development | SQLite or Compose Postgres | `./start.sh` or Compose |
| `ci` | Automated tests | Ephemeral Postgres + Redis services | GitHub Actions |
| `staging` | Pre-release validation | Anonymised/synthetic | Mirrors production topology, gateway sandbox modes |
| `production` | Customers | Real | HA data tier, backups, alerts |

## 2. Production topology

```mermaid
flowchart TB
    users["Users / CI"] --> dns["DNS"]
    dns --> cdn["CDN + WAF\nweb assets, DDoS, TLS"]
    cdn --> web["Next.js\nVercel or container"]
    cdn --> lb["Load balancer\nHTTPS, health checks"]

    subgraph VPC["Private network / VPC"]
        subgraph AppSubnet["App subnet"]
            lb --> api1["API replica 1"]
            lb --> api2["API replica 2"]
            lb --> apiN["API replica N"]
            beat["Celery beat x1"]
        end
        subgraph DataSubnet["Data subnet: no internet route"]
            pg[("PostgreSQL primary\n+ standby / replica")]
            redis[("Redis HA\nsentinel or managed")]
        end
        subgraph WorkerSubnet["Worker subnet: egress-filtered"]
            w1["Worker pool: default"]
            w2["Worker pool: priority"]
            w3["Worker pool: enterprise\ndedicated nodes"]
            proxy["Egress proxy\nblocks private ranges"]
        end
        api1 --> pg
        api2 --> pg
        apiN --> pg
        api1 --> redis
        redis --> w1
        redis --> w2
        redis --> w3
        beat --> redis
        w1 --> pg
        w2 --> pg
        w3 --> pg
        w1 --> proxy
        w2 --> proxy
        w3 --> proxy
    end

    proxy --> targets["Target websites"]
    api1 --> s3[("Object storage")]
    w1 --> s3
    api1 --> ext["Supabase, Gemini, payment gateways"]
    w1 --> ext
    obs["Prometheus, Grafana, Loki, Sentry"] -.-> api1
    obs -.-> w1
```

Notes:

- The current repo ships `render.yaml` and `render.yml` and a Vercel frontend; the diagram above is the target for a scaled production deployment. Render or a single VM with Compose is fine for early stage as long as Postgres, Redis and object storage are managed services.
- The API must be stateless. Do **not** rely on local disk for reports or evidence once more than one API/worker instance exists; set `STORAGE_BACKEND=s3`.

## 3. Container images

Build **separate** images so the API stays small and workers carry Chromium.

`deploy/docker/api.Dockerfile`

```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

FROM base AS deps
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM base AS runtime
COPY --from=deps /install /usr/local
COPY . .
RUN useradd -r -u 10001 app && chown -R app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["gunicorn", "api.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "60", "--graceful-timeout", "30"]
```

`deploy/docker/worker.Dockerfile`

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -r -u 10001 -m app && chown -R app /app
USER app
CMD ["celery", "-A", "worker.celery_app", "worker", "-Q", "qa_default", "-c", "2", "--loglevel=INFO", "--max-tasks-per-child=20"]
```

`deploy/docker/web.Dockerfile` (Next.js standalone output)

```dockerfile
FROM node:20-alpine AS build
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ .
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
RUN npm run build

FROM node:20-alpine
WORKDIR /web
ENV NODE_ENV=production
COPY --from=build /web/.next/standalone ./
COPY --from=build /web/.next/static ./.next/static
COPY --from=build /web/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
```

Pin the Playwright base image tag to the same version as the `playwright` package in `requirements.txt`. Use `--max-tasks-per-child` to recycle workers and contain Chromium memory leaks.

## 4. Docker Compose (single host)

`docker-compose.yml` (production-style; for staging or small deployments)

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: jasuss
      POSTGRES_USER: jasuss
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_password
    volumes: [pgdata:/var/lib/postgresql/data]
    secrets: [pg_password]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jasuss"]
      interval: 10s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes", "--maxmemory-policy", "noeviction"]
    volumes: [redisdata:/data]
    restart: unless-stopped

  migrate:
    build: { context: ., dockerfile: deploy/docker/api.Dockerfile }
    command: ["alembic", "upgrade", "head"]
    env_file: .env
    depends_on: { postgres: { condition: service_healthy } }
    restart: "no"

  api:
    build: { context: ., dockerfile: deploy/docker/api.Dockerfile }
    env_file: .env
    depends_on:
      migrate: { condition: service_completed_successfully }
      redis: { condition: service_started }
    ports: ["8000:8000"]
    restart: unless-stopped

  worker:
    build: { context: ., dockerfile: deploy/docker/worker.Dockerfile }
    env_file: .env
    depends_on: [redis, migrate]
    shm_size: "1gb"            # Chromium needs shared memory
    deploy: { resources: { limits: { memory: 3g, cpus: "2" } } }
    restart: unless-stopped

  beat:
    build: { context: ., dockerfile: deploy/docker/api.Dockerfile }
    command: ["celery", "-A", "worker.celery_app", "beat", "--loglevel=INFO"]
    env_file: .env
    depends_on: [redis]
    restart: unless-stopped

  web:
    build:
      context: .
      dockerfile: deploy/docker/web.Dockerfile
      args:
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
    ports: ["3000:3000"]
    restart: unless-stopped

volumes: { pgdata: {}, redisdata: {} }
secrets:
  pg_password: { file: ./secrets/pg_password.txt }
```

Run exactly **one** `beat` instance. Put a reverse proxy (Caddy/Nginx/Traefik) in front for TLS.

## 5. Environment variables

Provide `.env.example` in the repo with placeholders only.

```dotenv
# ---- Core ----
ENVIRONMENT=production                 # development | staging | production
LOG_LEVEL=INFO
LOG_FORMAT=json
CORS_ALLOWED_ORIGINS=https://app.example.com
PUBLIC_API_URL=https://api.example.com

# ---- Data ----
DATABASE_URL=postgresql+psycopg://jasuss:***@postgres:5432/jasuss
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
REDIS_URL=redis://redis:6379/0

# ---- Storage ----
STORAGE_BACKEND=s3                     # local | s3
S3_BUCKET=jasuss-artifacts
S3_REGION=us-east-1
S3_ENDPOINT_URL=                       # for MinIO/R2
ARTIFACT_URL_TTL_SECONDS=300

# ---- Auth (Supabase) ----
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWKS_URL=https://xxxx.supabase.co/auth/v1/.well-known/jwks.json
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=***
NEXT_PUBLIC_API_URL=https://api.example.com

# ---- AI ----
GEMINI_API_KEY=***
GEMINI_MODEL=gemini-2.5-flash
AI_MAX_COST_USD_PER_SCAN=0.25

# ---- Worker / scan limits ----
CELERY_TASK_SOFT_TIME_LIMIT=900
CELERY_TASK_TIME_LIMIT=1000
SCAN_MAX_PAGES_HARD_CAP=500
SCAN_PAGE_TIMEOUT_MS=30000
SSRF_ALLOWED_PORTS=80,443,8080,8443

# ---- Billing ----
STRIPE_SECRET_KEY=***
STRIPE_WEBHOOK_SECRET=***
LEMONSQUEEZY_API_KEY=***
LEMONSQUEEZY_WEBHOOK_SECRET=***
RAZORPAY_KEY_ID=***
RAZORPAY_KEY_SECRET=***
RAZORPAY_WEBHOOK_SECRET=***
PAYPAL_CLIENT_ID=***
PAYPAL_CLIENT_SECRET=***
PAYPAL_WEBHOOK_ID=***

# ---- Observability ----
SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=
```

Fail fast: `config.py` should validate required variables at startup with Pydantic Settings and refuse to boot in `production` if any secret is missing or if `DATABASE_URL` starts with `sqlite`.

## 6. Kubernetes (scale-out)

```mermaid
flowchart LR
    ing["Ingress + cert-manager"] --> svcapi["Service: api"]
    svcapi --> depapi["Deployment: api\nHPA on CPU and latency"]
    depwk["Deployment: worker-default\nKEDA on queue depth"] --> redis[("Redis")]
    depwk2["Deployment: worker-priority"] --> redis
    depwk3["Deployment: worker-enterprise\nnodeSelector: dedicated"] --> redis
    cron["CronJob: reaper, retention, reconcile"] --> pg[("PostgreSQL")]
    job["Job: alembic upgrade head\nHelm pre-upgrade hook"] --> pg
    np["NetworkPolicy: workers deny RFC1918 + 169.254.0.0/16"] -.-> depwk
```

Guidelines:

- **Autoscaling:** scale workers with KEDA on Redis list length of each queue; scale API on CPU/p95.
- **Resources:** worker requests `1 CPU / 2 Gi`, limits `2 CPU / 3 Gi`; mount `emptyDir` with `medium: Memory` at `/dev/shm`.
- **Probes:** API `livenessProbe: /healthz`, `readinessProbe: /readyz`. Workers: `celery inspect ping` exec probe.
- **Disruption:** `PodDisruptionBudget` for API; `terminationGracePeriodSeconds: 120` on workers and `acks_late` so in-flight scans are retried or gracefully finished.
- **Security:** `runAsNonRoot`, `readOnlyRootFilesystem`, drop all capabilities, `automountServiceAccountToken: false`.
- **Config:** Helm chart or Kustomize under `deploy/k8s`, secrets via External Secrets Operator.

## 7. CI/CD pipeline

```mermaid
flowchart LR
    pr["Pull request"] --> lint["Lint and format\nruff, eslint"]
    lint --> types["Type check\nmypy, tsc"]
    types --> unit["Unit tests\npytest, coverage gate"]
    unit --> integ["Integration tests\nPostgres + Redis services"]
    integ --> mig["Migration test\nfresh DB and N-1 snapshot"]
    mig --> sec["Security scans\npip-audit, npm audit, bandit, gitleaks"]
    sec --> build["Build images\napi, worker, web"]
    build --> scan["Trivy image scan"]
    scan --> gate["ci_quality_gate.py"]
    gate --> merge{"Review approved?"}
    merge -- "yes" --> main["Merge to main"]
    main --> push["Push images :sha to registry\nsign with cosign"]
    push --> stg["Deploy to staging"]
    stg --> smoke["Smoke and E2E\nrun a JASUSS scan against a demo site"]
    smoke --> approve{"Manual approval"}
    approve --> mig2["Run migrations\nrelease job"]
    mig2 --> prod["Rolling deploy to production"]
    prod --> verify["Post-deploy checks\nhealth, error rate, queue"]
    verify -- "fail" --> rb["Automatic rollback"]
```

Example GitHub Actions skeleton `.github/workflows/ci.yml`:

```yaml
name: ci
on:
  pull_request:
  push: { branches: [main] }

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_PASSWORD: postgres, POSTGRES_DB: test }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres" --health-interval 5s --health-retries 10
      redis:
        image: redis:7
        ports: ["6379:6379"]
    env:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/test
      REDIS_URL: redis://localhost:6379/0
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements.txt pytest-cov ruff mypy pip-audit bandit
      - run: playwright install --with-deps chromium
      - run: ruff check . && ruff format --check .
      - run: mypy api worker
      - run: alembic upgrade head
      - run: pytest -q --cov --cov-fail-under=80
      - run: pip-audit -r requirements.txt
      - run: bandit -q -r api worker billing security

  frontend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: web } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm, cache-dependency-path: web/package-lock.json }
      - run: npm ci
      - run: npm run lint
      - run: npm run build
      - run: npm audit --audit-level=high

  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
```

## 8. Release and rollback

```mermaid
sequenceDiagram
    autonumber
    participant CI as CI/CD
    participant R as Registry
    participant M as Migration job
    participant P as Production
    participant O as Monitoring

    CI->>R: Push images tagged with git SHA
    CI->>M: Run alembic upgrade head (expand-only)
    M-->>CI: OK
    CI->>P: Rolling update API (maxUnavailable 0)
    CI->>P: Rolling update workers (drain in-flight scans)
    P->>O: Health, error rate, queue depth
    alt healthy for 10 min
        CI-->>CI: Mark release good
    else regression
        CI->>P: Roll back to previous SHA
        Note over M,P: Schema stays expanded, so old code still works
    end
```

Rules:

- Semantic versioning with Git tags; changelog generated from Conventional Commits.
- Migrations are backward compatible with the previous release (expand/contract), so rollback never needs a DB downgrade.
- Feature flags for risky features (e.g. new AI model routing).

## 9. Cost and sizing

Starting point for ~1,000 scans/day (each scan ≈ 3–8 min, 1 Chromium):

| Component | Suggested size |
| --- | --- |
| API | 2 × (1 vCPU, 1 GiB) |
| Workers | 6–10 concurrent scan slots ≈ 4 × (2 vCPU, 4 GiB) with concurrency 2 |
| PostgreSQL | 2 vCPU, 8 GiB, 100 GiB SSD, standby |
| Redis | 1 GiB HA |
| Object storage | 200–500 GiB with 30-day lifecycle |

Levers: cap `max_pages`, reduce screenshot resolution/format (WebP), compress HAR, route low-risk triage to a cheaper model in `model_router.py`, and use spot/preemptible nodes for the default worker pool (safe with `acks_late` + retry).

## 10. Repository hygiene

Observed in the repository and recommended fixes before production:

| Finding | Action |
| --- | --- |
| `.venv312/` is committed | Remove from git (`git rm -r --cached .venv312`), add to `.gitignore`; consider history rewrite if it is large |
| Both `render.yaml` and `render.yml` exist | Keep one (`render.yaml`), delete the other to avoid drift |
| Python modules and `test_*.py` files at repo root, plus a `tests/` folder | Move into a package (`jasuss/`) and `tests/`; add `pyproject.toml` |
| `results/` directory in repo | Add to `.gitignore`; never commit scan output |
| No `.env.example` visible | Add one with placeholders |
| No `LICENSE`/`SECURITY.md`/`CODEOWNERS` verified | Add them (README links to `LICENSE`) |
| Single `Dockerfile` for everything | Split api/worker/web images as in section 3 |
| `runtime.txt` and Docker both pin Python | Keep Python version in one place (`pyproject.toml` + Dockerfile) |
| Unpinned or loosely pinned `requirements.txt` | Use a lockfile (`pip-tools`/`uv`) with hashes |
