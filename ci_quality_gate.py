#!/usr/bin/env python3
"""
CI Quality Gate Evaluator

Evaluates the final QA report JSON against configurable regression rules.
Exits with 0 if no blocking findings are found, or 1 if blocking regressions are detected.
Also generates a Markdown summary suitable for GitHub Actions.
"""

import os
import json
import sys

def evaluate_quality_gate(report_path):
    if not os.path.exists(report_path):
        print(f"ERROR: Report file not found at {report_path}")
        return 2

    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load JSON report: {e}")
        return 2

    # Load thresholds (defaults: Critical=True, High=True, Medium=False)
    fail_on_critical = os.environ.get("CI_FAIL_ON_NEW_CRITICAL", "true").lower() == "true"
    fail_on_high = os.environ.get("CI_FAIL_ON_NEW_HIGH", "true").lower() == "true"
    fail_on_medium = os.environ.get("CI_FAIL_ON_NEW_MEDIUM", "false").lower() == "true"

    findings = report.get("findings", [])
    regression_summary = report.get("summary", {}).get("regression_summary", {})
    
    # Calculate counts (in case they differ slightly from summary)
    new_findings = [f for f in findings if f.get("regression_status") == "NEW"]
    persisting_findings = [f for f in findings if f.get("regression_status") == "UNCHANGED"]
    changed_findings = [f for f in findings if f.get("regression_status") in ("WORSENED", "IMPROVED")]
    
    fixed_count = regression_summary.get("fixed", 0)

    blocking_findings = []
    
    for f in new_findings:
        sev = f.get("severity", "info").lower()
        if sev == "critical" and fail_on_critical:
            blocking_findings.append(f)
        elif sev == "high" and fail_on_high:
            blocking_findings.append(f)
        elif sev == "medium" and fail_on_medium:
            blocking_findings.append(f)

    # Note: we might also want to fail on WORSENED if configured, but keeping it simple for now as requested.
    for f in changed_findings:
        sev = f.get("severity", "info").lower()
        if f.get("regression_status") == "WORSENED":
            if sev == "critical" and fail_on_critical:
                blocking_findings.append(f)
            elif sev == "high" and fail_on_high:
                blocking_findings.append(f)
            elif sev == "medium" and fail_on_medium:
                blocking_findings.append(f)

    # Generate Markdown summary
    target_url = report.get("report_metadata", {}).get("target", "Unknown")
    pages_crawled = report.get("report_metadata", {}).get("pages_crawled", 0)

    md = []
    md.append("AI QA REGRESSION CHECK")
    md.append("======================")
    md.append("")
    md.append("Target:")
    md.append(target_url)
    md.append("")
    md.append("Pages:")
    md.append(str(pages_crawled))
    md.append("")
    
    baseline_total = len(persisting_findings) + len(changed_findings) + fixed_count
    md.append("Baseline findings:")
    md.append(str(baseline_total))
    md.append("")
    md.append("Current findings:")
    md.append(str(len(findings)))
    md.append("")
    md.append("New:")
    md.append(str(len(new_findings)))
    md.append("")
    md.append("Fixed:")
    md.append(str(fixed_count))
    md.append("")
    md.append("Persisting:")
    md.append(str(len(persisting_findings)))
    md.append("")
    md.append("Changed:")
    md.append(str(len(changed_findings)))
    md.append("")
    
    quality_gate_passed = len(blocking_findings) == 0
    md.append("Quality Gate:")
    md.append("PASSED" if quality_gate_passed else "FAILED")
    md.append("")
    
    if blocking_findings:
        md.append("Blocking findings:")
        md.append("")
        for f in blocking_findings:
            status = f.get("regression_status", "NEW").upper()
            sev = f.get("severity", "INFO").upper()
            title = f.get("title", "Untitled")
            url = f.get("url", "")
            md.append(f"{status} {sev}")
            md.append(title)
            if url:
                md.append(url)
            md.append("")

    summary_text = "\n".join(md)
    print("\n" + summary_text + "\n")

    # Write to GitHub step summary if present
    gh_step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_step_summary:
        try:
            with open(gh_step_summary, "a", encoding="utf-8") as f:
                f.write(summary_text + "\n\n")
        except OSError as e:
            print(f"Warning: Failed to write to GITHUB_STEP_SUMMARY: {e}")

    return 0 if quality_gate_passed else 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ci_quality_gate.py <path_to_final_qa_report.json>")
        sys.exit(2)
        
    exit_code = evaluate_quality_gate(sys.argv[1])
    sys.exit(exit_code)
