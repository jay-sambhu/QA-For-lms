# 🛡️ JASUSS — Enterprise Web Quality Assurance Platform
### *Continuous Automated Testing, Multi-Viewport Verification & Defect Triage*
**Powered by Nexus Engine**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.3-black.svg?logo=next.js&logoColor=white)](https://nextjs.org)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-green.svg?logo=playwright&logoColor=white)](https://playwright.dev)
[![Celery](https://img.shields.io/badge/Celery-Distributed%20Queue-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Pytest](https://img.shields.io/badge/Tests-167%20Passing-brightgreen.svg?logo=pytest&logoColor=white)](https://pytest.org)

---

## 📖 Table of Contents

- [Overview](#-overview)
- [System Architecture & Data Flow Diagram (DFD)](#-system-architecture--data-flow-diagram-dfd)
- [Database Schema (Entity-Relationship Diagram)](#-database-schema-entity-relationship-diagram)
- [Key Features & Capabilities](#-key-features--capabilities)
- [Subscription & Multi-Payment Gateways](#-subscription--multi-payment-gateways)
- [Technology Stack](#-technology-stack)
- [Repository Structure & Conventions](#-repository-structure--conventions)
- [Getting Started & Local Development](#-getting-started--local-development)
- [Admin Console & Telemetry](#-admin-console--telemetry)
- [Running Automated Tests](#-running-automated-tests)
- [Contributing & Open Source Guidelines](#-contributing--open-source-guidelines)

---

## 🌟 Overview

**JASUSS** is an end-to-end automated web quality assurance suite designed for software development teams, QA engineers, and high-velocity SaaS products. Powered by the **Nexus Engine**, JASUSS autonomously audits web applications across multiple viewports (Desktop, Mobile, Tablet), executes synthetic interactive journeys, intercepts client-side and network defects, performs AI-assisted root cause triage, and delivers compliance audit reports with a single click.

---

## 📐 System Architecture & Data Flow Diagram (DFD)

The following diagram illustrates how JASUSS orchestrates multi-viewport crawling, synthetic user interactions, defect triage, AI synthesis, and report exports:

```mermaid
flowchart TD
    subgraph ClientLayer["🖥️ Presentation & Client Layer"]
        A["User / CI Pipeline"] -->|"Submit Target URL"| B["Next.js 16 App Router\n(JASUSS UI)"]
        B -->|"REST API / Auth Bearer"| C["FastAPI Gateway\n(/api/v1/scans)"]
    end

    subgraph DistributedExecution["⚡ Asynchronous Processing & Workers"]
        C -->|"Enqueue Scan Task"| D[("Redis Message Broker\n(qa_queue)")]
        D -->|"Consume Job"| E["Celery Worker Pool\n(Isolated Contexts)"]
    end

    subgraph QAPipeline["🔍 Core Multi-Stage QA Engine"]
        E --> S1["Stage 1: Multi-Viewport Crawler\n• Desktop Chrome (1920x1080)\n• iPhone 13 (390x844)\n• iPad Gen 7 (820x1180)"]
        S1 --> S2["Stage 2: Synthetic Interactive Tester\n• Button & Link Discovery\n• Form Assertions\n• Dialog Dismissal"]
        S2 --> S3["Stage 3: Deterministic Defect Detector\n• HTTP 4xx/5xx Errors\n• Unhandled JS Exceptions\n• Layout Overflows"]
        S3 --> S4["Stage 4: Evidence & Regression Engine\n• DOM Screenshots\n• Network HAR Telemetry\n• Historical Diffing"]
        S4 --> S5["Stage 5: AI-Enriched Quality Synthesis\n• Gemini Root-Cause Triage\n• P0-P4 Severity Classification\n• Reproduction Steps"]
        S5 --> S6["Stage 6: Canonical Calculation Engine\n• Canonical Quality Score (0-100)\n• Letter Grade (A+ to F)\n• Executive Summary"]
    end

    subgraph StorageLayer["💾 Unified Persistence & Artifacts"]
        S6 --> DB[("PostgreSQL / SQLite Database\n(SQLAlchemy Sole Truth)")]
        S6 --> FS["Local Output Artifacts\n• PDF Audit Reports\n• Multi-Tab Excel Sheets\n• Raw JSON Telemetry\n• Markdown Summary"]
    end

    subgraph Exporters["📊 Reporting & Webhooks"]
        FS --> EXP1["📄 PDF Exporter (ReportLab)"]
        FS --> EXP2["📑 Excel Exporter (OpenPyXL)"]
        FS --> EXP3["📝 Markdown / JSON Exporter"]
    end
```

---

## 🗄️ Database Schema (Entity-Relationship Diagram)

SQLAlchemy is the sole source of truth for all users, scans, subscriptions, and financial transactions:

```mermaid
erDiagram
    USERS ||--o{ SCANS : executes
    USERS ||--o{ SUBSCRIPTIONS : maintains
    USERS ||--o{ PAYMENT_TRANSACTIONS : pays

    USERS {
        string id PK "UUID Primary Key"
        string email UK "Unique User Email"
        string role "Role ('user', 'admin')"
        string plan_tier "Tier ('free', 'pro', 'enterprise')"
        datetime created_at "Registration Timestamp"
    }

    SCANS {
        string id PK "Scan UUID Primary Key"
        string user_id FK "References USERS(id)"
        text url "Target Website URL"
        string status "Status ('pending', 'running', 'completed', 'failed', 'cancelled')"
        boolean is_authenticated "Authenticated Crawl Flag"
        datetime created_at "Creation Timestamp"
        datetime completed_at "Completion Timestamp"
        text report_path "Relative Markdown Path"
        text json_path "Relative JSON Telemetry Path"
    }

    SUBSCRIPTIONS {
        string id PK "Subscription UUID"
        string user_id FK "References USERS(id)"
        string plan_id "Plan ID ('free', 'pro', 'enterprise')"
        string status "Status ('active', 'past_due', 'cancelled')"
        string gateway "Gateway ('stripe', 'lemonsqueezy', 'razorpay', 'paypal')"
        string customer_id "Gateway Customer ID"
        string subscription_id "Gateway Subscription ID"
        datetime current_period_end "Renewal Date"
        boolean cancel_at_period_end "Cancel Flag"
        datetime created_at "Creation Timestamp"
    }

    PAYMENT_TRANSACTIONS {
        string id PK "Transaction UUID"
        string user_id FK "References USERS(id)"
        string gateway "Gateway Name"
        string transaction_id "Gateway Charge Reference"
        int amount_cents "Amount in Cents"
        string currency "Currency Code (USD, EUR, INR)"
        string status "Status ('succeeded', 'failed')"
        string plan_id "Plan Purchased"
        datetime created_at "Payment Timestamp"
    }
```

---

## 🚀 Key Features & Capabilities

1. **Multi-Viewport Cross-Device Crawling**:
   - Simultaneous parallel crawling across **Desktop (1920×1080)**, **iPhone 13 (390×844)**, and **iPad Gen 7 (820×1180)**.
   - Evaluates horizontal layout overflows, element clipping, and viewport breakpoints.

2. **Deterministic Interactive Testing**:
   - Automatically uncovers interactive controls (buttons, links, form inputs) and verifies state changes, client-side routing, and modal transitions.

3. **Secure Authenticated Crawling**:
   - Supports form-based authentication (`login_url`, `username`, `password`) using Pydantic `SecretStr` transient memory. Zero password leakage into databases, server logs, or report artifacts.

4. **Canonical Calculation Engine**:
   - Single source of truth for QA metrics (`core/calculation_engine.py`):
     - Normalized Pass/Fail rates.
     - Deterministic Health Score (0–100) and Letter Grade (A+, A, B, C, D, F).
     - Weighted severity penalties (Critical: 25 pts, High: 15 pts, Medium: 7 pts, Low: 2 pts).

5. **Executive Multi-Format Exports**:
   - One-click downloads for:
     - **PDF Reports**: Formal executive audit with visual score gauges and remediation tables.
     - **Excel Workbooks**: Structured multi-tab spreadsheets (`Overview`, `Findings`, `Test Cases`, `Responsive Matrix`).
     - **JSON & Markdown**: Complete raw telemetry for CI/CD integrations.

6. **Interactive Stop / Cancel Scan**:
   - Real-time scan abort controls directly from the scanning monitor via `POST /api/v1/scans/{id}/cancel`.

---

## 💳 Subscription & Multi-Payment Gateways

JASUSS includes built-in multi-gateway payment processing supporting **Stripe**, **LemonSqueezy**, **Razorpay**, and **PayPal**:

| Plan Tier | Price | Scans / Month | Page Crawl Depth | Key Features |
| :--- | :--- | :--- | :--- | :--- |
| **Community Starter** | **$0** (Free) | 10 Scans | Up to 10 Pages | Multi-viewport crawling, defect triage, web quality score |
| **Professional QA** | **$49 / mo** | 200 Scans | Up to 50 Pages | Authenticated crawling, PDF & Excel exports, priority queue |
| **Enterprise Suite** | **$199 / mo** | Unlimited | Deep Discovery | Dedicated worker node, custom auth, 24/7 SLA, custom rules |

### Supported Gateways:
- 💳 **Stripe**: Credit/Debit Cards, Apple Pay, Google Pay (`StripeAdapter`).
- 🛍️ **LemonSqueezy**: Merchant of Record with global tax handling (`LemonSqueezyAdapter`).
- ⚡ **Razorpay**: UPI, NetBanking, International Cards (`RazorpayAdapter`).
- 💵 **PayPal**: PayPal Wallet & Express Checkout (`PayPalAdapter`).

---

## 🛠️ Technology Stack

- **Backend Framework**: Python 3.12+, FastAPI, Pydantic V2, Uvicorn
- **Browser Automation**: Playwright (Headless Chromium)
- **Task Queue & Broker**: Celery, Redis
- **Database & ORM**: SQLAlchemy, PostgreSQL / SQLite, Alembic Migrations
- **AI Synthesis**: Google Gemini AI (`gemini-2.5-flash` / `gemini-3-flash-preview`)
- **Reporting Engines**: ReportLab (PDF), OpenPyXL (Excel)
- **Frontend Architecture**: Next.js 16 (Turbopack, App Router), React 19, TypeScript
- **Styling & Animations**: Vanilla CSS Modules (Glassmorphism & Luxury Dark Mode), Framer Motion, Lucide Icons
- **Authentication**: Supabase Auth (JWT Bearer Token Validation)

---

## 📂 Repository Structure & Conventions

```text
ai-qa-agent/
├── api/                        # FastAPI Route Controllers & API Endpoints
│   ├── __init__.py
│   ├── main.py                 # Core API & Scan Pipeline Orchestrator
│   ├── billing.py              # Subscription & Multi-Gateway Checkout Endpoints
│   ├── admin.py                # Admin Telemetry & Platform Metrics
│   └── rate_limiter.py         # Client IP & User Rate Limiting
├── billing/                    # Payment Gateway Adapters
│   ├── __init__.py
│   └── gateways.py             # Stripe, LemonSqueezy, Razorpay, PayPal Adapters
├── core/                       # Core QA Pipeline Engines & Stage Modules
│   ├── __init__.py
│   ├── bug_detector.py         # Deterministic Anomaly & Defect Trapper
│   ├── bug_triage.py           # Severity, Confidence & Priority Triage Engine
│   ├── calculation_engine.py   # Sole Backend Source of Truth for QA Metrics
│   ├── ci_quality_gate.py      # Automated CI/CD Regression Gate Evaluator
│   ├── evidence_engine.py      # Screenshot & Network Evidence Engine
│   ├── explorer.py             # LLM Site Exploration Engine
│   ├── gemini_analyzer.py      # AI Root-Cause & Verification Engine
│   ├── interactive_tester.py   # Synthetic Interaction Runner
│   ├── model_router.py         # Adaptive Gemini Model Router
│   ├── qa_report_generator.py  # PDF, Excel, JSON & Markdown Exporters
│   ├── regression_detector.py  # Historical Baseline Regression Diffing
│   ├── test_case_executor.py   # Test Case Execution Engine
│   └── test_case_generator.py  # Test Case Discovery & Generation
├── crawler/                    # Multi-Viewport Playwright Crawler
│   ├── __init__.py
│   ├── crawler.py              # Playwright Desktop, Mobile, Tablet Engine
│   ├── network.py              # Network HAR & Traffic Monitor
│   └── viewport.py             # Viewport Configurations
├── security/                   # Sensitive Data Sanitization & Redaction
│   ├── __init__.py
│   └── redactor.py             # Zero-Leakage SecretStr & PII Redactor
├── worker/                     # Asynchronous Celery Queue Workers
│   ├── __init__.py
│   ├── celery_app.py           # Celery Broker & Queue Configuration
│   └── tasks.py                # Distributed Scan Task Runner
├── web/                        # Next.js 16 App Router Frontend Web Application
│   ├── src/
│   │   ├── app/                # Dedicated App Router Routes
│   │   │   ├── page.tsx        # Landing & Marketing Showcase Route (/)
│   │   │   ├── dashboard/      # User QA Dashboard Route (/dashboard)
│   │   │   │   ├── page.tsx
│   │   │   │   └── scan/[id]/  # Scan Detail & Live Monitor Route (/dashboard/scan/[id])
│   │   │   │       └── page.tsx
│   │   │   ├── pricing/        # Pricing & Gateways Route (/pricing)
│   │   │   │   └── page.tsx
│   │   │   ├── admin/          # Admin Telemetry Console Route (/admin)
│   │   │   │   └── page.tsx
│   │   │   ├── layout.tsx      # Global App Layout with AuthProvider & NavBar
│   │   │   └── page.module.css # Luxury Dark Mode & Responsive CSS Module
│   │   ├── components/         # Reusable Modular UI Components
│   │   │   ├── layout/         # Persistent NavBar, Footer
│   │   │   ├── auth/           # Production AuthModal (Sign In / Sign Up)
│   │   │   ├── scan/           # ScanForm, ScanMonitor, ScanResults, DeviceDeck
│   │   │   ├── admin/          # AdminMetrics, TenantTable, PipelineInspector, SystemTelemetry
│   │   │   └── pricing/        # PricingCards & Multi-Gateway Selector
│   │   ├── context/            # React AuthContext (Session & Subscription State)
│   │   ├── types/              # Strongly-Typed QA & Scan Contracts (qa.ts)
│   │   └── utils/              # Client-Side Exporters & Supabase Client
│   └── next.config.ts          # Turbopack & Dynamic API Proxy Rewrites
├── alembic/                    # Database Migrations (001 -> 002 -> 003)
├── tests/                      # Consolidated Pytest Test Suite (167+ Tests)
├── config.py                   # Global Pydantic Environment Configuration
├── db.py                       # SQLAlchemy Session Factory & DB Connection
├── models.py                   # SQLAlchemy Models (User, Scan, Subscription, Transaction)
├── run_qa.py                   # Standalone CLI QA Automation Pipeline
├── start.sh                    # Foreground Interactive Development Launcher
├── Dockerfile                  # Production Container Definition
├── render.yaml                 # Render Cloud Deployment Blueprint
├── .env.example                # Environment Template (Secrets Omitted)
└── README.md                   # Platform Documentation
```

### 📌 Project Structure Conventions
- **Pipeline Stages**: All individual pipeline stages and analysis algorithms reside in `core/`.
- **API Endpoints**: All FastAPI route handlers reside in `api/`.
- **Worker Tasks**: Asynchronous Celery task wrappers reside in `worker/`.
- **Testing Suite**: All automated unit and integration test modules reside exclusively in `tests/`.
- **Frontend Routes**: Every top-level page lives in its own `web/src/app/<route>/page.tsx` directory.
- **Frontend Components**: Reusable UI components live in `web/src/components/<domain>/`.
- **Local Output Directories**: The `results/`, `reports/`, `screenshots/`, and `user_data/` directories are local-only transient output artifacts and are strictly `.gitignore`d (never committed to git history).

---

## ⚡ Getting Started & Local Development

### 1. Prerequisites
- Python `3.10+` (Python `3.12` recommended)
- Node.js `18+` and `npm`
- Redis (or local mock broker)

### 2. Clone & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/jay-sambhu/QA-For-lms.git
cd QA-For-lms

# Install Python dependencies & Playwright Chromium
pip install -r requirements.txt
playwright install chromium

# Install Next.js frontend dependencies
npm install --prefix web
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### 4. Start Interactive Development Servers
Use the included foreground terminal launcher to monitor live API requests and compilation logs:
```bash
chmod +x start.sh
./start.sh
```

- 🌐 **Web Application**: `http://localhost:3000`
- 🔌 **API Documentation (Swagger UI)**: `http://localhost:8000/docs`

---

## 📊 Admin Console & Telemetry

Navigate to `/admin` or click **"Admin"** in the top navigation bar:
- **MRR & Financial Analytics**: Real-time revenue, active paid subscriptions, and transaction logs.
- **Tenant Management**: View registered users, active plan tiers (`Free`, `Pro`, `Enterprise`), and scan history.
- **Global Scan Pipeline Inspector**: Live visibility into all running, completed, and failed scans.
- **System Telemetry**: Real-time CPU load, memory utilization, and Celery worker node health.

---

## 🧪 Running Automated Tests

Run the full pytest suite across calculation engines, database migrations, security sanitizers, payment gateways, and report exporters:

```bash
# Run entire test suite (167+ tests passing)
pytest -q

# Run specific test modules
pytest -q tests/test_billing_gateways.py tests/test_admin_api.py
pytest -q tests/test_calculation_engine.py tests/test_auth_crawl.py
```

---

## 🤝 Contributing & Open Source Guidelines

We welcome contributions from developers worldwide!

1. **Fork the Repository**.
2. **Create a Feature Branch** (`git checkout -b feat/amazing-feature`).
3. **Commit your Changes** (`git commit -m 'feat: add amazing feature'`).
4. **Push to the Branch** (`git push origin feat/amazing-feature`).
5. **Open a Pull Request**.

Please ensure all tests pass (`pytest -q`) and Next.js builds cleanly (`npm run build --prefix web`) before submitting your PR.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

*Engineered with precision by the JASUSS Team · Powered by Nexus.*
