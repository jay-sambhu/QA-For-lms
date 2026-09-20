# Architecture

All diagrams use [Mermaid](https://mermaid.js.org/) and render natively on GitHub.

## Contents
1. [System context (C4 level 1)](#1-system-context-c4-level-1)
2. [Container view (C4 level 2)](#2-container-view-c4-level-2)
3. [Backend component view (C4 level 3)](#3-backend-component-view-c4-level-3)
4. [Data flow diagrams](#4-data-flow-diagrams)
5. [Scan pipeline](#5-scan-pipeline)
6. [Sequence: scan lifecycle](#6-sequence-scan-lifecycle)
7. [Scan state machine](#7-scan-state-machine)
8. [Multi-viewport concurrency model](#8-multi-viewport-concurrency-model)
9. [Design decisions](#9-design-decisions)
10. [Scaling model](#10-scaling-model)

---

## 1. System context (C4 level 1)

```mermaid
flowchart TB
    user["QA engineer / Developer"]
    ci["CI/CD pipeline"]
    admin["Platform admin"]

    subgraph J["JASUSS platform"]
        core["Web QA platform"]
    end

    target["Target web application under test"]
    gemini["Google Gemini API"]
    supa["Supabase Auth"]
    pay["Payment gateways: Stripe, LemonSqueezy, Razorpay, PayPal"]
    email["Email / notification provider"]

    user -->|"Submit scans, view reports"| core
    ci -->|"Trigger scans via API key"| core
    admin -->|"Monitor tenants and revenue"| core
    core -->|"Crawl and test"| target
    core -->|"Root-cause triage"| gemini
    core -->|"Validate JWT"| supa
    core -->|"Checkout and webhooks"| pay
    core -.->|"Scan-complete alerts (proposed)"| email
```

## 2. Container view (C4 level 2)

```mermaid
flowchart TB
    subgraph Client["Client"]
        browser["Browser"]
        cli["CLI: run_qa.py"]
    end

    subgraph Edge["Edge"]
        cdn["CDN / WAF"]
    end

    subgraph App["Application tier"]
        web["Next.js 16 web app\nApp Router, React 19"]
        api["FastAPI service\nREST /api/v1"]
        worker["Celery workers\nPlaywright Chromium"]
        beat["Celery beat\nreaper and retention jobs"]
    end

    subgraph Data["Data tier"]
        pg[("PostgreSQL")]
        redis[("Redis\nbroker, rate limits, cache")]
        s3[("Object storage\nPDF, XLSX, JSON, screenshots, HAR")]
    end

    subgraph Ext["External"]
        supa["Supabase Auth"]
        gem["Gemini API"]
        gw["Payment gateways"]
        tgt["Target websites"]
    end

    browser --> cdn --> web
    web -->|"REST + Bearer JWT"| api
    cli --> api
    api --> pg
    api --> redis
    api -->|"presigned URLs"| s3
    api -->|"validate token"| supa
    api --> gw
    gw -->|"webhooks"| api
    redis --> worker
    beat --> redis
    worker --> pg
    worker --> s3
    worker --> gem
    worker --> tgt
```

## 3. Backend component view (C4 level 3)

Maps the modules that exist in the repository to their responsibilities.

```mermaid
flowchart LR
    subgraph API["api/"]
        main["main.py\nscan routes"]
        billing_r["billing.py\ncheckout and webhooks"]
        admin_r["admin.py\ntelemetry"]
        rl["rate_limiter.py"]
    end

    subgraph Worker["worker/"]
        celery["celery_app.py"]
        tasks["tasks.py\nrun_scan task"]
    end

    subgraph Engine["Nexus Engine"]
        crawler["crawler/crawler.py\nmulti-viewport"]
        inter["interactive_tester.py"]
        detect["bug_detector.py"]
        triage["bug_triage.py"]
        evidence["evidence_engine.py"]
        regress["regression_detector.py"]
        gemini["gemini_analyzer.py"]
        router["model_router.py"]
        calc["calculation_engine.py"]
        report["qa_report_generator.py"]
        tcgen["test_case_generator.py / executor"]
    end

    subgraph Shared["Shared"]
        models["models.py + db.py\nSQLAlchemy"]
        cfg["config.py"]
        redact["security/redactor.py"]
        gw["billing/gateways.py\nadapters"]
    end

    main --> celery --> tasks
    tasks --> crawler --> inter --> detect --> triage
    triage --> evidence --> regress --> gemini --> calc --> report
    gemini --> router
    tcgen --> inter
    tasks --> models
    main --> models
    billing_r --> gw
    billing_r --> models
    admin_r --> models
    main --> rl
    tasks --> redact
    report --> redact
```

## 4. Data flow diagrams

### 4.1 Level 0: context DFD

```mermaid
flowchart LR
    U(["User"]) -->|"URL, credentials, options"| P["0. JASUSS QA platform"]
    P -->|"Scan status, score, reports"| U
    P -->|"Page requests"| T(["Target site"])
    T -->|"HTML, JS, network responses"| P
    P -->|"Sanitised findings"| G(["Gemini"])
    G -->|"Root cause, severity, repro steps"| P
    U -->|"Payment details"| PG(["Payment gateway"])
    PG -->|"Webhook events"| P
```

### 4.2 Level 1: main processes

```mermaid
flowchart TD
    U(["User"]) -->|"scan request"| P1["1.0 Authenticate and authorise"]
    P1 -->|"user id, plan"| P2["2.0 Validate and enqueue scan"]
    P2 -->|"scan row"| D1[("D1 Scans and Users")]
    P2 -->|"job"| D2[("D2 Redis queue")]
    D2 --> P3["3.0 Crawl and interact"]
    P3 <-->|"pages"| T(["Target site"])
    P3 -->|"raw observations"| P4["4.0 Detect and triage"]
    P4 -->|"findings"| P5["5.0 Evidence and regression"]
    D3[("D3 Previous scan results")] --> P5
    P5 -->|"enriched findings"| P6["6.0 AI synthesis"]
    P6 <-->|"redacted context"| G(["Gemini"])
    P6 -->|"classified findings"| P7["7.0 Score and report"]
    P7 -->|"results"| D1
    P7 -->|"artifacts"| D4[("D4 Object storage")]
    D1 --> P8["8.0 Serve results and exports"]
    D4 --> P8
    P8 --> U
```

## 5. Scan pipeline

```mermaid
flowchart TD
    A["Scan request accepted"] --> B{"Plan quota and\ncrawl depth OK?"}
    B -- "no" --> R1["Reject: 402 / 429"]
    B -- "yes" --> C{"URL passes\nSSRF guard?"}
    C -- "no" --> R2["Reject: 422"]
    C -- "yes" --> D["Create scan: pending, enqueue"]
    D --> E["Worker picks up job: running"]
    E --> F["Stage 1: crawl x3 viewports"]
    F --> G["Stage 2: interactive testing"]
    G --> H["Stage 3: deterministic defect detection"]
    H --> I["Stage 4: evidence and regression diff"]
    I --> J{"Gemini available\nand within budget?"}
    J -- "yes" --> K["Stage 5: AI triage"]
    J -- "no" --> L["Deterministic triage only"]
    K --> M["Stage 6: canonical scoring"]
    L --> M
    M --> N["Render reports: PDF, XLSX, JSON, MD"]
    N --> O["Persist and upload artifacts"]
    O --> P["Scan: completed"]
    F -. "cancel / timeout / crash" .-> X["Scan: cancelled / failed\nPartial results kept"]
    G -.-> X
    H -.-> X
```

## 6. Sequence: scan lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant W as Next.js
    participant A as FastAPI
    participant S as Supabase Auth
    participant Q as Redis
    participant K as Celery worker
    participant T as Target site
    participant G as Gemini
    participant D as PostgreSQL
    participant O as Object storage

    U->>W: Enter URL, click Scan
    W->>A: POST /api/v1/scans (Bearer JWT)
    A->>S: Verify JWT (JWKS, cached)
    A->>D: Check plan quota, insert scan (pending)
    A->>Q: Enqueue run_scan(scan_id)
    A-->>W: 202 Accepted {scan_id}
    loop Poll every 2s or SSE
        W->>A: GET /scans/{id}
        A->>D: Read status and progress
        A-->>W: status, progress %
    end
    Q->>K: Deliver job
    K->>D: status = running
    par Desktop / Mobile / Tablet
        K->>T: Crawl and interact
        T-->>K: Pages, network, console
    end
    K->>O: Upload screenshots and HAR
    K->>G: Redacted findings for triage
    G-->>K: Root cause, severity, steps
    K->>K: Compute score and grade
    K->>O: Upload PDF, XLSX, JSON, MD
    K->>D: status = completed, store results
    W->>A: GET /scans/{id}/report?format=pdf
    A->>O: Presign URL
    A-->>W: 302 to presigned URL
    W-->>U: Download report
```

### Cancellation

```mermaid
sequenceDiagram
    actor U as User
    participant A as FastAPI
    participant D as PostgreSQL
    participant R as Redis
    participant K as Worker

    U->>A: POST /scans/{id}/cancel
    A->>D: Verify ownership, status = cancelling
    A->>R: SET cancel:{id} = 1 (TTL)
    A-->>U: 202
    loop Between pages and stages
        K->>R: GET cancel:{id}
    end
    K->>K: Close browser contexts
    K->>D: status = cancelled, keep partial results
```

## 7. Scan state machine

```mermaid
stateDiagram-v2
    [*] --> pending: POST /scans
    pending --> running: worker picks up
    pending --> cancelled: user cancels
    running --> completed: all stages done
    running --> failed: error, timeout, or reaper
    running --> cancelling: user cancels
    cancelling --> cancelled: worker acknowledges
    failed --> pending: retry (manual or auto, max 2)
    completed --> [*]
    cancelled --> [*]
    failed --> [*]
```

## 8. Multi-viewport concurrency model

```mermaid
flowchart TB
    T["Celery task: run_scan"] --> B["One Chromium browser process"]
    B --> C1["Context: Desktop 1920x1080"]
    B --> C2["Context: iPhone 13 390x844"]
    B --> C3["Context: iPad Gen 7 820x1180"]
    C1 --> P1["Pages, bounded by semaphore"]
    C2 --> P2["Pages, bounded by semaphore"]
    C3 --> P3["Pages, bounded by semaphore"]
    P1 --> M["Merge and de-duplicate findings"]
    P2 --> M
    P3 --> M
    M --> Z["Responsive matrix"]
```

Isolation rules: one browser context per viewport, no shared cookies, contexts destroyed on task exit (including on exception), hard task time limit, and memory ceiling per worker container.

## 9. Design decisions

| Decision | Rationale | Trade-off |
|---|---|---|
| FastAPI + Celery instead of running scans in the API process | Browser work is CPU/RAM heavy and long-running; isolates failures and enables horizontal scaling | Requires Redis and worker operations |
| Deterministic detection first, AI second | Reproducible findings, lower cost, AI failures do not break the scan | AI adds value only on triage and explanation |
| `calculation_engine.py` as the single scoring source | Prevents score drift between UI, PDF, Excel and JSON | All consumers must call it, never recompute |
| SQLAlchemy as sole source of truth, Alembic migrations | Auditable schema history | Migration discipline required |
| Pydantic `SecretStr` for credentials, redaction layer | Zero credential leakage into DB, logs, reports, prompts | Credentials exist only in worker memory for the scan duration |
| Object storage for artifacts (proposed) | Multiple workers and API replicas cannot share local disk | Extra dependency |

## 10. Scaling model

| Component | Scales by | Signal |
|---|---|---|
| Web (Next.js) | Replicas / edge | CPU, latency |
| API | Replicas (stateless) | p95 latency, CPU |
| Workers | Replicas per queue | Queue depth and wait time |
| Redis | Managed HA | Memory, ops/s |
| PostgreSQL | Vertical + read replica | Connections, IOPS |

Queues (proposed): `qa_default`, `qa_priority` (Pro), `qa_enterprise` (dedicated node pool), `qa_reports`. Each worker container runs low concurrency (1–2 scans) because each scan owns a Chromium process.
