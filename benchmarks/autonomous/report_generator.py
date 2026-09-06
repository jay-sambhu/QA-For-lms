"""
Multi-Format Report Generator for Phase 19 Autonomous Challenge Validation Suite.
Outputs detailed JSON and Markdown evaluation scorecards.
"""
import os
import json
from typing import List, Dict, Any
from benchmarks.autonomous.scoring import EvaluationScorecard


def generate_challenge_suite_report(
    scorecards: List[EvaluationScorecard],
    output_dir: str,
) -> Dict[str, str]:
    """Generates JSON and Markdown summary reports for the complete challenge suite."""
    os.makedirs(output_dir, exist_ok=True)
    
    json_path = os.path.join(output_dir, "autonomous_challenge_results.json")
    md_path = os.path.join(output_dir, "autonomous_challenge_results.md")

    # Overall Summary Metrics
    total_gt = sum(s.ground_truth_count for s in scorecards)
    total_tp = sum(s.true_positives for s in scorecards)
    total_fp = sum(s.false_positives for s in scorecards)
    total_fn = sum(s.false_negatives for s in scorecards)
    total_tn = sum(s.true_negatives for s in scorecards)

    overall_precision = round(total_tp / (total_tp + total_fp), 4) if (total_tp + total_fp) > 0 else 1.0
    overall_recall = round(total_tp / (total_tp + total_fn), 4) if (total_tp + total_fn) > 0 else 1.0
    overall_f1 = round(2 * (overall_precision * overall_recall) / (overall_precision + overall_recall), 4) if (overall_precision + overall_recall) > 0 else 1.0
    avg_autonomy = round(sum(s.autonomy_rate for s in scorecards) / len(scorecards), 4) if scorecards else 1.0

    report_data = {
        "summary": {
            "applications_tested": len(scorecards),
            "total_ground_truth_defects": total_gt,
            "true_positives": total_tp,
            "false_positives": total_fp,
            "false_negatives": total_fn,
            "true_negatives": total_tn,
            "overall_precision": overall_precision,
            "overall_recall": overall_recall,
            "overall_f1_score": overall_f1,
            "average_autonomy_rate": avg_autonomy,
        },
        "scorecards": [s.__dict__ for s in scorecards],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    # Markdown Report
    rows = []
    for s in scorecards:
        rows.append(
            f"| {s.app_name} | {s.ground_truth_count} | {s.true_positives} | {s.false_positives} | {s.false_negatives} | "
            f"{s.precision} | {s.recall} | {s.f1_score} | {s.autonomy_rate * 100:.1f}% | `{s.release_decision}` |"
        )
    table_content = "\n".join(rows)

    md_content = f"""# JASUSS Phase 19 Autonomous Challenge Suite Evaluation Report

## Executive Summary
This report summarizes the empirical performance of **JASUSS** evaluated against **6 autonomous challenge applications** in `UNKNOWN_DEFECT_MODE=true` without human-written test cases or hardcoded defect hints.

### Overall Benchmark Metrics
- **Applications Tested**: {len(scorecards)}
- **Ground Truth Hidden Defects**: {total_gt}
- **True Positives (TP)**: {total_tp}
- **False Positives (FP)**: {total_fp}
- **False Negatives (FN)**: {total_fn}
- **Overall Precision**: **{overall_precision * 100:.2f}%**
- **Overall Recall**: **{overall_recall * 100:.2f}%**
- **Overall F1 Score**: **{overall_f1 * 100:.2f}%**
- **Average Autonomy Rate**: **{avg_autonomy * 100:.1f}%**

---

## Challenge Application Scorecards

| Application | Ground Truth Defects | TP | FP | FN | Precision | Recall | F1 | Autonomy | Quality Gate |
|---|---|---|---|---|---|---|---|---|---|
{table_content}

---

## Detailed Application Breakdowns

"""
    for s in scorecards:
        md_content += f"""### {s.app_name} (`{s.app_key}`)
- **Ground Truth Defects**: {s.ground_truth_count}
- **Detected Defects**: {', '.join(s.detected_defect_ids) if s.detected_defect_ids else 'None'}
- **Missed Defects**: {', '.join(s.missed_defect_ids) if s.missed_defect_ids else 'None'}
- **Evidence Completeness**: {s.evidence_completeness * 100:.1f}%
- **Release Decision**: `{s.release_decision}`

"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return {"json": json_path, "markdown": md_path}
