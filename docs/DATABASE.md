# Database

SQLAlchemy models are the single source of truth; schema changes ship only through Alembic migrations.

- Development: SQLite (`sqlite:///./qa_agent.db`)
- Production: **PostgreSQL 15+** (required; SQLite is not supported in production)

## 1. Current schema (from the repository README)

```mermaid
erDiagram
    USERS ||--o{ SCANS : executes
    USERS ||--o{ SUBSCRIPTIONS : maintains
    USERS ||--o{ PAYMENT_TRANSACTIONS : pays

    USERS {
        uuid id PK
        string email UK
        string role "user | admin"
        string plan_tier "free | pro | enterprise"
        datetime created_at
    }
    SCANS {
        uuid id PK
        uuid user_id FK
        text url
        string status "pending | running | completed | failed | cancelled"
        boolean is_authenticated
        datetime created_at
        datetime completed_at
        text report_path
        text json_path
    }
    SUBSCRIPTIONS {
        uuid id PK
        uuid user_id FK
        string plan_id
        string status "active | past_due | cancelled"
        string gateway "stripe | lemonsqueezy | razorpay | paypal"
        string customer_id
        string subscription_id
        datetime current_period_end
        boolean cancel_at_period_end
        datetime created_at
    }
    PAYMENT_TRANSACTIONS {
        uuid id PK
        uuid user_id FK
        string gateway
        string transaction_id
        int amount_cents
        string currency
        string status "succeeded | failed"
        string plan_id
        datetime created_at
    }
```

## 2. Proposed production schema (Target State: Phase 3)

> **Note on Migration Status:** The current database migration head is `003_add_subscriptions_and_plans.py`. The additions marked below (`findings`, `scan_artifacts`, `webhook_events`, etc.) define the target production schema to be introduced via Alembic migrations in Phase 3.  
> **Note on Tenant Isolation & RLS:** The FastAPI backend currently enforces tenant isolation at the query level (`Scan.user_id == user.id`). Row Level Security (RLS) is an optional direct-client database defence-in-depth layer.

Additions marked **(new)** normalise findings out of JSON blobs, support regression diffing, make webhooks idempotent, and add auditability.

```mermaid
erDiagram
    USERS ||--o{ SCANS : executes
    USERS ||--o{ SUBSCRIPTIONS : maintains
    USERS ||--o{ PAYMENT_TRANSACTIONS : pays
    USERS ||--o{ API_KEYS : owns
    USERS ||--o{ AUDIT_LOG : generates
    SCANS ||--o{ SCAN_VIEWPORT_RESULTS : has
    SCANS ||--o{ FINDINGS : produces
    SCANS ||--o{ SCAN_ARTIFACTS : stores
    FINDINGS ||--o{ FINDING_EVIDENCE : backed_by
    SUBSCRIPTIONS ||--o{ PAYMENT_TRANSACTIONS : bills
    WEBHOOK_EVENTS }o--|| SUBSCRIPTIONS : updates

    USERS {
        uuid id PK
        string email UK
        string role
        string plan_tier
        int scans_used_this_period "new"
        datetime deleted_at "new, soft delete"
        datetime created_at
    }
    SCANS {
        uuid id PK
        uuid user_id FK
        text url
        string url_host "new, indexed"
        string status
        int progress_pct "new"
        boolean is_authenticated
        int quality_score "new, 0-100"
        string grade "new"
        string error_code "new"
        string celery_task_id "new"
        uuid baseline_scan_id FK "new, regression base"
        datetime started_at "new"
        datetime completed_at
        datetime created_at
    }
    SCAN_VIEWPORT_RESULTS {
        uuid id PK "new"
        uuid scan_id FK
        string viewport "desktop | mobile | tablet"
        int pages_crawled
        int overflow_count
        int duration_ms
    }
    FINDINGS {
        uuid id PK "new"
        uuid scan_id FK
        string fingerprint "stable hash for diffing"
        string category "http | js | layout | interaction | a11y"
        string severity "P0 to P4"
        string viewport
        text page_url
        text title
        text root_cause "AI"
        json repro_steps
        boolean is_regression
        datetime created_at
    }
    FINDING_EVIDENCE {
        uuid id PK "new"
        uuid finding_id FK
        string kind "screenshot | har | dom | console"
        text storage_key
    }
    SCAN_ARTIFACTS {
        uuid id PK "new"
        uuid scan_id FK
        string format "pdf | xlsx | json | md"
        text storage_key
        bigint size_bytes
        string sha256
    }
    SUBSCRIPTIONS {
        uuid id PK
        uuid user_id FK
        string plan_id
        string status
        string gateway
        string customer_id
        string subscription_id
        datetime current_period_end
        boolean cancel_at_period_end
    }
    PAYMENT_TRANSACTIONS {
        uuid id PK
        uuid user_id FK
        uuid subscription_id FK "new"
        string gateway
        string transaction_id
        int amount_cents
        string currency
        string status
    }
    WEBHOOK_EVENTS {
        uuid id PK "new"
        string gateway
        string event_id "unique per gateway"
        string type
        json payload
        string status "received | processed | failed"
        datetime received_at
        datetime processed_at
    }
    API_KEYS {
        uuid id PK "new"
        uuid user_id FK
        string prefix
        string hash "SHA-256, never store plaintext"
        datetime last_used_at
        datetime revoked_at
    }
    AUDIT_LOG {
        uuid id PK "new"
        uuid actor_id FK
        string action
        string entity
        string entity_id
        json meta
        string ip
        datetime created_at
    }
```

## 3. Indexes and constraints

| Table | Index / constraint | Reason |
|---|---|---|
| `scans` | `(user_id, created_at DESC)` | Dashboard history |
| `scans` | `(status)` partial where status in (`pending`,`running`) | Reaper and admin inspector |
| `scans` | `(url_host, completed_at DESC)` | Baseline lookup for regression |
| `findings` | `(scan_id, severity)` | Report rendering |
| `findings` | `(fingerprint)` | Regression diff |
| `webhook_events` | unique `(gateway, event_id)` | Idempotent webhook handling |
| `subscriptions` | unique `(gateway, subscription_id)` | Prevent duplicates |
| `payment_transactions` | unique `(gateway, transaction_id)` | Prevent double-recording |
| `users` | unique `lower(email)` | Case-insensitive uniqueness |
| all FKs | `ON DELETE` explicit (`CASCADE` for scan children, `RESTRICT` for payments) | Data integrity |

## 4. Migration policy

1. Every schema change is an Alembic revision; never edit models without one.
2. CI runs `alembic upgrade head` on an empty DB **and** on a snapshot of the previous release (`test_database_migrations.py`).
3. Use **expand / contract** for zero-downtime: add nullable column, deploy code that writes both, backfill, switch reads, drop old column in a later release.
4. Migrations run as a separate release step (job), not on API start-up, once more than one API replica exists.
5. Each revision must be reversible or explicitly marked irreversible in its docstring.

## 5. Retention and privacy

| Data | Retention | Notes |
|---|---|---|
| Scan rows and findings | Per plan: Free 30 days, Pro 12 months, Enterprise configurable | Nightly retention job |
| Screenshots / HAR | 30 days default | Contain target-site content; treat as customer data |
| Reports (PDF/XLSX/JSON/MD) | Same as scan | Object-storage lifecycle rule |
| Webhook payloads | 90 days | Strip PII where possible |
| Audit log | 13 months minimum | Append-only |
| Credentials for authenticated crawls | **Never persisted** | Held in worker memory only |

Account deletion: soft-delete immediately, hard-delete personal data and artifacts within 30 days; financial records retained as required by law.

## 6. Connection management

- Pool per process: `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=1800`.
- Use PgBouncer (transaction mode) when API replicas × workers exceed roughly 100 connections.
- Workers open short transactions; do not hold a DB session across the whole scan.
- Statement timeout 15 s for API, 60 s for workers.

## 7. Backup and recovery

| Item | Target |
|---|---|
| Backups | Daily full + continuous WAL archiving (PITR) |
| RPO | ≤ 5 minutes |
| RTO | ≤ 1 hour |
| Restore drill | Quarterly, documented in [OPERATIONS.md](OPERATIONS.md) |
