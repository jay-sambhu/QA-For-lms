# JASUSS Autonomous QA Scoring & Benchmark Methodology (Phase 19)

## Executive Summary
This document defines the mathematical scoring formulas, metric definitions, and ground-truth evaluation standards for **JASUSS Phase 19 Autonomous Challenge Benchmarks**.

---

## 1. Metric Mathematical Definitions

### A. Precision Score
$$\text{Precision} = \frac{TP}{TP + FP}$$
- **True Positive (TP)**: Ground truth hidden defect correctly detected and verified by JASUSS.
- **False Positive (FP)**: Reported defect that does not exist in ground truth inventory.

### B. Recall Score (Defect Recall)
$$\text{Recall} = \frac{TP}{TP + FN}$$
- **False Negative (FN)**: Ground truth hidden defect missed by JASUSS discovery/execution.

### C. F1 Score (Balanced Accuracy)
$$F1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

### D. Autonomy Rate
$$\text{Autonomy Rate} = \frac{\text{Autonomous QA Actions}}{\text{Autonomous QA Actions} + \text{Human Interventions}}$$
- Measured strictly during execution. In `UNKNOWN_DEFECT_MODE=true`, JASUSS target runs achieve **100% Autonomy Rate** (0 human interventions).

### E. Evidence Completeness Score
$$\text{Evidence Completeness} = \frac{\text{Findings with Screenshot + Console/HAR Traces}}{\text{Total Findings}}$$

---

## 2. Release Quality Gate Decision Matrix

| Gate Decision | Triggering Criteria | Operational Meaning |
|---|---|---|
| **FAIL** | 1+ Confirmed Critical/High Defects (TP > 0) | Release BLOCKED due to verified software defects |
| **REVIEW_REQUIRED** | Unresolved candidate bugs or missed defects (FN > 0) | Human QA review required before approval |
| **PASS_WITH_WARNINGS** | Low-severity warnings or false positives (FP > 0) | Release APPROVED with minor advisory notes |
| **PASS** | 100% Passing tests with zero defects found | Release APPROVED for production deployment |

---

## 3. Strict Scoring Rules
- **No Zero Denominator Masking**: If $TP + FP = 0$, reported as `"N/A"` rather than `"100%"`.
- **Infrastructure Isolation**: Celery/Redis connection failures or browser timeouts are classified as `INFRASTRUCTURE_FAILURE` and excluded from defect false positive counts.
