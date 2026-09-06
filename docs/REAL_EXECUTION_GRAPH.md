# JASUSS Real Execution Graph & Integration Audit (Phase 18)

**Date**: September 6, 2026
**Product**: JASUSS — Autonomous Quality Engineering Platform

---

## 1. Runtime Call Graph (`POST /api/v1/scans` $\rightarrow$ Final Engineering Report)

```
POST /api/v1/scans (api/main.py:create_scan)
│
├── 1. Database Record Persistence: SQLAlchemy Scan(status="pending")
├── 2. Queue Async Execution: Celery process_query_task.delay() or BackgroundTasks
│
└── Background Worker (run_qa.py:run_pipeline)
    │
    ├── [STATE 1: CREATED -> DISCOVERING]
    │   ├── PipelineStateMachine (core/state_machine.py)
    │   ├── AgentOrchestrator (core/agent/agent_orchestrator.py) -> DiscoveryAgent
    │   └── ResumableDiscoveryEngine (core/discovery/resumable_crawler.py)
    │       ├── WebsiteCrawler (crawler/crawler.py) -> Playwright Headless Browser
    │       └── RouteNormalizer (core/discovery/route_normalizer.py) -> /route/:id templates
    │
    ├── [STATE 2: MODELING]
    │   └── ApplicationKnowledgeManager (core/application_model/manager.py)
    │       └── Persists application_model.json
    │
    ├── [STATE 3: PLANNING]
    │   └── RiskPlannerEngine (core/planning/risk_planner.py)
    │       └── Generates P0-P3 test_plan_<scan_id>.json
    │
    ├── [STATE 4: GENERATING]
    │   └── AutonomousTestGenerator (core/test_generator_v2.py)
    │       └── Generates multi-category test_cases_<scan_id>.json
    │
    ├── [STATE 5: EXECUTING & ASSERTING]
    │   └── SelfHealingExecutor (core/executor_v2.py)
    │       ├── Multi-tier locator resolution & controlled recovery
    │       └── AssertionEngine (core/oracle/assertion_engine.py) -> Multi-source assertions
    │
    ├── [STATE 6: VERIFYING & TRIAGING]
    │   ├── DefectVerificationEngine (core/defect_verification.py)
    │   │   └── SHA256 Fingerprint Deduplication -> defects_<scan_id>.json
    │   ├── ApiTestingEngine (core/api_testing/api_tester.py)
    │   └── PerfA11yEngine (core/performance/perf_a11y_engine.py)
    │
    ├── [STATE 7: REGRESSION & LEARNING]
    │   ├── RegressionMemoryEngine (core/regression_v2.py)
    │   └── HistoricalLearningEngine (core/learning/pattern_extractor.py)
    │
    ├── [STATE 8: SCORING & QUALITY GATE]
    │   ├── evaluate_quality_gate (core/ci_quality_gate.py)
    │   └── CalculationEngine (core/calculation_engine.py)
    │
    └── [STATE 9: COMPLETED]
        ├── QAReportGenerator (core/qa_report_generator.py) -> JSON, MD, PDF, Excel
        └── Database Update: Scan(status="completed", report_path=..., json_path=...)
```

---

## 2. Platform Component Integration Audit Matrix

| Engine / Component | Exists | Imported | Integrated | Executed E2E | Produces Real Output | Tested Against Real App |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pipeline State Machine** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Application Knowledge Model** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Resumable Discovery Engine** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Route Normalization** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Risk-Based Test Planner** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Multi-Category Test Generator** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Multi-Source Assertion Oracle** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Self-Healing Test Executor** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Defect Deduplication (SHA256)** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Regression Memory Engine** | Yes | Yes | Yes | Yes | Yes | Yes |
| **API Contract Tester** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Perf & Accessibility Auditor** | Yes | Yes | Yes | Yes | Yes | Yes |
| **AI Agent Orchestrator** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Historical Learning Engine** | Yes | Yes | Yes | Yes | Yes | Yes |
| **CI/CD Quality Gate** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Engineering Report Generator** | Yes | Yes | Yes | Yes | Yes | Yes |
