# JASUSS — CI/CD Quality Gates & Release Policy

## Policy Evaluation (`core/ci_quality_gate.py`)

JASUSS evaluates scan reports against strict release gates:

- **Deployment Blockers**:
  - Any P0 or Critical defect (`CI_FAIL_ON_NEW_CRITICAL=true`)
  - Any High severity regression (`CI_FAIL_ON_NEW_HIGH=true`)
  - Health score falling below threshold
- **Exit Codes**:
  - `0`: Quality Gate PASSED (deployable)
  - `1`: Quality Gate FAILED (deployment blocked)
  - `2`: Invalid report or execution error
