# JASUSS Autonomous Quality Engineering Architecture (Phase 19)

## Executive Summary
This document defines the production architecture of **JASUSS**, an Autonomous Quality Engineering Platform capable of operating in `UNKNOWN_DEFECT_MODE=true` against arbitrary web applications without manual test scripts.

---

## 1. System Dataflow & Pipeline State Machine

```
Target URL (+ Optional Auth/Roles)
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Pipeline State Machine (core/state_machine.py)              │
└─────────────────────────────────────────────────────────────┘
  ├── 1. DISCOVERING ──► ResumableDiscoveryEngine (Playwright BFS)
  ├── 2. MODELING    ──► ApplicationKnowledgeManager (State Graphs)
  ├── 3. PLANNING    ──► RiskPlannerEngine (Multi-Factor Formula)
  ├── 4. GENERATING  ──► AutonomousTestGenerator (36 Tests)
  ├── 5. EXECUTING   ──► SelfHealingExecutor (Safe Fallbacks)
  ├── 6. ASSERTING   ──► BehaviorOracle (Multi-Signal Invariants)
  ├── 7. VERIFYING   ──► DefectVerificationEngine (3x Reproduction)
  ├── 8. TRIAGING    ──► GeminiQAOrchestrator (Evidence Analysis)
  ├── 9. REGRESSION  ──► RegressionMemoryEngine (SHA256 Fingerprints)
  ├── 10. SCORING    ──► ReleaseQualityGate (Deterministic Release Gate)
  └── 11. COMPLETED  ──► QAReportGenerator & Web Dashboard
```

---

## 2. Core Architecture Subsystems

### A. Autonomous Discovery Engine
- **Strategy**: Multi-viewport Playwright crawler (Desktop, Mobile, Tablet).
- **Navigation Graph**: Constructs stateful transition graphs (Auth $\rightarrow$ Dashboard $\rightarrow$ Resource $\rightarrow$ Action).
- **Form & Route Templates**: Normalizes parameterized routes (`/items/:id/edit`) using URL tokenization.

### B. Multi-Factor Risk Planner
- Calculates risk scores using the formula:
  $$\text{risk\_score} = \text{business\_criticality} + \text{mutation\_risk} + \text{security\_risk} + \text{complexity} + \text{historical\_failure\_risk}$$
- Allocates test budgets to P0 (Critical auth/pay/admin), P1 (Core CRUD), P2 (Forms), and P3 (Static content).

### C. Multi-Signal Behavior Oracle
- Enforces behavior invariants across multiple data sources:
  1. **HTTP Layer**: Status codes, response headers, HAR payloads.
  2. **DOM Layer**: Element visibility, text matches, input attributes.
  3. **Console Layer**: Uncaught JS TypeErrors, unhandled promise rejections.
  4. **Layout Layer**: Viewport bounding box calculations (scrollWidth vs clientWidth).
  5. **Security Layer**: Authorization check responses for privilege escalation paths.

### D. Evidence Chain & Manifest
- Every verified finding produces a tamper-proof package:
  - SHA256 Root-Cause Fingerprint
  - Viewport Screenshot (.png)
  - Raw HAR Network Trace
  - Console Stack Trace
  - Reproducibility Count (3x verification)
