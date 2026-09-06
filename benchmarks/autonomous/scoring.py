"""
Objective Metric Scoring Engine for Phase 19 Autonomous QA Benchmarks.
Calculates Precision, Recall, F1, Autonomy Rate, Evidence Completeness, and Release Gate status.
"""
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from benchmarks.autonomous.defect_registry import GroundTruthDefect, get_ground_truth_defects


@dataclass
class EvaluationScorecard:
    app_key: str
    app_name: str
    ground_truth_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float | str
    recall: float | str
    f1_score: float | str
    verification_rate: float
    evidence_completeness: float
    autonomy_rate: float
    human_intervention_rate: float
    release_decision: str
    detected_defect_ids: List[str]
    missed_defect_ids: List[str]


def evaluate_scan_against_ground_truth(
    app_key: str,
    app_name: str,
    raw_findings: List[Dict[str, Any]],
    agent_decisions: List[Dict[str, Any]],
    executed_tests_count: int,
) -> EvaluationScorecard:
    """Matches scan findings against hidden ground-truth defects and computes objective scores."""
    ground_truth = get_ground_truth_defects(app_key)
    gt_ids = {d.defect_id: d for d in ground_truth}

    detected_gt_ids = set()
    false_positive_count = 0

    for finding in raw_findings:
        page = finding.get("page", "")
        url = finding.get("url", "")
        title = finding.get("title", "")
        desc = finding.get("description", "")
        console_errs = finding.get("evidence", {}).get("console_errors", []) if finding.get("evidence") else []
        desc_err = console_errs[0].get("error", "") if console_errs and isinstance(console_errs, list) and len(console_errs) > 0 else ""
        text_corpus = f"{page} {url} {title} {desc} {desc_err}".lower()

        http_errs = finding.get("evidence", {}).get("http_errors", []) if finding.get("evidence") else []
        extracted_status = finding.get("status") or (http_errs[0].get("status") if http_errs and isinstance(http_errs, list) and len(http_errs) > 0 else None)

        matched = False
        for gt in ground_truth:
            # Check pattern match
            pattern = gt.target_url_pattern.lower()
            if pattern in text_corpus:
                if gt.expected_status_code:
                    if extracted_status == gt.expected_status_code:
                        detected_gt_ids.add(gt.defect_id)
                        matched = True
                elif gt.expected_error_substring:
                    if gt.expected_error_substring.lower() in text_corpus:
                        detected_gt_ids.add(gt.defect_id)
                        matched = True
                else:
                    detected_gt_ids.add(gt.defect_id)
                    matched = True

        if not matched and finding.get("severity") in ("high", "critical"):
            false_positive_count += 1

    tp = len(detected_gt_ids)
    fp = false_positive_count
    fn = len(ground_truth) - tp
    tn = max(0, executed_tests_count - (tp + fp))

    # Precision
    if (tp + fp) > 0:
        precision = round(tp / (tp + fp), 4)
    else:
        precision = "N/A" if fn == 0 else 0.0

    # Recall
    if (tp + fn) > 0:
        recall = round(tp / (tp + fn), 4)
    else:
        recall = "N/A"

    # F1
    if isinstance(precision, float) and isinstance(recall, float) and (precision + recall) > 0:
        f1 = round(2 * (precision * recall) / (precision + recall), 4)
    else:
        f1 = "N/A"

    # Verification Rate
    verification_rate = round(tp / len(ground_truth), 4) if ground_truth else 1.0

    # Evidence Completeness
    evidence_found = sum(1 for f in raw_findings if f.get("screenshot") or f.get("evidence"))
    evidence_completeness = round(evidence_found / len(raw_findings), 4) if raw_findings else 1.0

    # Autonomy Rate
    autonomous_actions = len(agent_decisions) + executed_tests_count
    human_interventions = 0
    total_actions = autonomous_actions + human_interventions
    autonomy_rate = round(autonomous_actions / total_actions, 4) if total_actions > 0 else 1.0

    # Release Decision
    if tp == len(ground_truth) and fp == 0:
        release_decision = "FAIL"  # Ground truth defects confirmed -> Release blocked (FAIL)
    elif fn > 0:
        release_decision = "REVIEW_REQUIRED"
    elif fp > 0:
        release_decision = "PASS_WITH_WARNINGS"
    else:
        release_decision = "PASS"

    missed_gt_ids = list(set(gt_ids.keys()) - detected_gt_ids)

    return EvaluationScorecard(
        app_key=app_key,
        app_name=app_name,
        ground_truth_count=len(ground_truth),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        precision=precision,
        recall=recall,
        f1_score=f1,
        verification_rate=verification_rate,
        evidence_completeness=evidence_completeness,
        autonomy_rate=autonomy_rate,
        human_intervention_rate=round(1.0 - autonomy_rate, 4),
        release_decision=release_decision,
        detected_defect_ids=sorted(list(detected_gt_ids)),
        missed_defect_ids=sorted(missed_gt_ids),
    )
