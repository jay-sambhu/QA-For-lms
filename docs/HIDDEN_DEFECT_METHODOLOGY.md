# JASUSS Hidden Defect Benchmark Methodology (Phase 19)

## Executive Summary
This document defines the methodology for evaluating **JASUSS** against **Hidden Seeded Defects** across multiple independent web applications without providing prior hints to the agent.

---

## 1. Core Principles of Hidden Defect Testing

1. **Zero Prior Knowledge**: The JASUSS engine is initialized with `UNKNOWN_DEFECT_MODE=true`. It receives ONLY the target application URL.
2. **Dynamic Service Spawning**: Challenge applications are dynamically launched on isolated ports (`8101` to `8106`).
3. **Seeded Defect Inventory Isolation**: The ground-truth defect registry ([`benchmarks/autonomous/defect_registry.py`](file:///home/devxgamer/ai-qa-agent/benchmarks/autonomous/defect_registry.py)) is imported ONLY by the evaluator (`scoring.py`) during post-execution scoring.
4. **Multi-Domain Diversity**: Challenge applications represent 6 distinct software paradigms (CRUD, E-Commerce, LMS, Admin Dashboard, SPA, and Complex Forms).

---

## 2. Seeded Defect Spectrum

| Category | Typical Manifestation | Verification Oracle Signal |
|---|---|---|
| **Functional** | Operation failure (e.g. Delete item 999 500 error) | HTTP 500 status & error response payload |
| **UI / Responsive** | Horizontal viewport overflow (+5000px element width) | Bounding box scrollWidth vs clientWidth |
| **Security** | Privilege escalation via query param / missing auth check | 200 OK access on protected `/admin` or `/instructor` routes |
| **API / Async** | Unhandled promise rejection / async 500 response | Console error log & HAR status code |
| **JavaScript** | Uncaught TypeError / ReferenceError on click | Console exception stack trace |
| **Validation** | Negative price allowed / invalid email accepted | Form submission accepted without error state |
| **Navigation** | Dead link / 404 resource | HTTP 404 response on navigation link |
