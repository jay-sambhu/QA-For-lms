# JASUSS Self-Healing Safety Audit & Principles (Phase 19)

## Executive Summary
This document establishes safety guidelines and audit requirements for the **Self-Healing Test Executor** ([`core/executor_v2.py`](file:///home/devxgamer/ai-qa-agent/core/executor_v2.py)) in JASUSS.

---

## 1. The Core Principle: Never Mask Application Defect as Test Pass

Self-healing is designed to recover from **locator drift** (e.g. element ID changed from `#submit-btn` to `[role='button'][name='Submit']`). It is **NOT** allowed to heal or mask true application defects.

### Distinction Matrix

| Event Scenario | Cause Type | Executor Action | Healing Record Generated? | Final Status |
|---|---|---|---|---|
| Selector `#submit` moved to `[role='button']` | Locator Drift (Test Issue) | Recover element locator | **YES** (`confidence=0.85`) | `PASS` (with healing audit log) |
| Button clicked $\rightarrow$ Page throws HTTP 500 | Application Defect | Record assertion failure | NO | **FAIL** |
| Button clicked $\rightarrow$ Uncaught JS TypeError | Application Defect | Record console error assertion | NO | **FAIL** |
| Navigation link returns HTTP 404 | Application Defect | Record HTTP status assertion | NO | **FAIL** |
| Target element missing because page failed to load | Infrastructure / App Defect | Record timeout assertion | NO | **FAIL** |

---

## 2. Audit Healing Record Structure

Every healed action generates an explicit audit log:

```json
{
  "step_index": 1,
  "original_locator": "button#submit-item",
  "recovered_locator": "button[type='submit']",
  "reason": "Original selector unavailable; matched semantic element role",
  "confidence": 0.85,
  "behavior_equivalent": true
}
```

---

## 3. Guarantees
1. **Healing Audit Trail**: All healed steps are explicitly surfaced in `execution_results.json` and reported in engineering scorecards.
2. **Review Requirement**: Any test run involving low-confidence healing (`confidence < 0.70`) is flagged as `REVIEW_REQUIRED` in the Quality Gate.
