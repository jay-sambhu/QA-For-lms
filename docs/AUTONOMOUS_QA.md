# JASUSS — Autonomous Quality Engineering Operational Manual

## Core Vision
JASUSS operates as an autonomous quality engineering platform. Given a target application URL, authentication credentials, and optional requirements, JASUSS autonomously:
1. Discovers the application topology (routes, interactive elements, forms, APIs).
2. Builds and maintains a persistent Application Intelligence Model.
3. Evaluates business risk weights to plan high-priority test suites (`P0` - `P3`).
4. Generates multi-category test cases (Functional, Auth, Authorization, Form, API, Security, Performance).
5. Executes tests with self-healing element locators and multi-source assertion oracles.
6. Verifies, deduplicates (SHA256 fingerprinting), and triages defects.
7. Evaluates regression memory and flaky test metrics against historical baselines.
8. Enforces CI/CD Quality Gates and outputs engineering reports.

## Execution Options
- **CLI Mode**: `python3 run_qa.py https://target-app.example.com --max-pages 30`
- **CI Mode**: `python3 run_qa.py https://target-app.example.com --ci`
- **SaaS API Mode**: `POST /api/v1/scans`
