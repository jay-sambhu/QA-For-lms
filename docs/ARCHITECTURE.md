# JASUSS Autonomous Quality Engineering — Platform Architecture

**Engine**: Nexus Engine
**Version**: 2.0.0

## System Architecture

JASUSS is built as a stateful, autonomous Quality Engineering Platform that transforms web QA scanning into continuous quality assurance.

```
+-------------------------------------------------------------------------------+
|                               JASUSS API Layer                                |
|  - FastAPI (REST & Webhooks)                                                  |
|  - Celery / Async Worker Queue                                                |
|  - Supabase & SQLAlchemy Engine                                               |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                        Pipeline State Machine Engine                          |
|  CREATED -> DISCOVERING -> MODELING -> PLANNING -> GENERATING -> EXECUTING    |
|  -> VERIFYING -> TRIAGING -> REGRESSION -> SCORING -> COMPLETED               |
+-------------------------------------------------------------------------------+
                                       |
    +----------------------------------+-----------------------------------+
    |                                  |                                   |
    v                                  v                                   v
+-----------------------+   +-----------------------+   +-----------------------+
|  Discovery Engine     |   |  Application Model    |   |  Risk Test Planner    |
|  - Multi-Viewport     |   |  - Route Topology     |   |  - Risk Prioritization|
|  - Dynamic Route Mapping| |  - State Transitions  |   |  - Critical Path Score|
|  - API Traffic Monitor|   |  - Auth Role Matrix   |   |  - Category Strategy  |
+-----------------------+   +-----------------------+   +-----------------------+
    |                                  |                                   |
    +----------------------------------+-----------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                      Autonomous Test Generation Engine                        |
|  - Multi-Category Tests: Functional, Auth, API, Security, Performance        |
|  - Multi-Source Observable Assertion Engine (Pass / Fail / Needs Review)     |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                   Self-Healing Executor & Defect Verification                 |
|  - Multi-tier Locator Resolution (Role -> Label -> Test ID -> Semantic Text)  |
|  - 7-Step Verification Loop (Detect -> Capture -> Reproduce -> Classify)      |
|  - SHA256 Fingerprint Deduplication                                           |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                    Quality Gate & Next.js Quality Dashboard                   |
+-------------------------------------------------------------------------------+
```

## Internal Data Contracts (`core/schemas/`)
- `discovery.py`: `DiscoveryResultModel`, `PageModel`, `ElementModel`, `ApiEndpointModel`.
- `application_model.py`: `ApplicationKnowledgeModel`, `WorkflowModel`, `StateTransitionModel`.
- `test_case.py`: `TestCaseModel`, `TestCategory`, `TestPriority`.
- `execution_result.py`: `TestExecutionResultModel`, `TestResultStatus`, `HealingRecordModel`.
- `defect.py`: `DefectModel`, `DefectSeverity`, `DefectVerificationStatus`.
- `regression.py`: `RegressionAnalysisModel`, `FlakyMetricModel`.
- `quality.py`: `QualityGateResultModel`, `OverallQualityStatus`.
