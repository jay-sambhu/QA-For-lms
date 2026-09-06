# JASUSS — Observability & Artifact System

## Scan Artifact Structure (`results/` & `user_data/<user_id>/`)
Each scan generates a standardized, auditable set of artifacts:
- `checkpoint_<scan_id>.json`: Pipeline stage machine progress checkpoint
- `discovery_checkpoint_<scan_id>.json`: Resumable discovery result
- `application_model.json`: Persistent application intelligence graph
- `test_plan_<scan_id>.json`: Risk-weighted test execution plan
- `test_cases_<scan_id>.json`: Multi-category generated test cases
- `execution_results_<scan_id>.json`: Assertion outcomes and self-healing audit records
- `defects_<scan_id>.json`: Deduplicated defect records with SHA256 fingerprints
- `regression_<scan_id>.json`: Baseline regression analysis
- `progress_<scan_id>.json`: Live progress status for API polling
