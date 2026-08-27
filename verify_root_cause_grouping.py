#!/usr/bin/env python3
"""
Comprehensive verification of root-cause grouping implementation.

This is a structural self-check, not a snapshot test. It verifies invariants
that must hold for *any* crawl (evidence preserved, IDs unique, counts add up)
rather than asserting the specific numbers produced by one historical run.
"""

import argparse
import json
import sys
from pathlib import Path


def _fmt_ratio(raw_total, total_candidates):
    if not total_candidates:
        return "n/a"
    return f"{raw_total / total_candidates:.1f}x"


def verify_implementation(findings_path=None, results_dir="results"):
    """Verify the root-cause grouping implementation."""

    print("\n" + "=" * 100)
    print("ROOT-CAUSE GROUPING IMPLEMENTATION VERIFICATION")
    print("=" * 100)

    if findings_path:
        latest_findings = Path(findings_path)
        if not latest_findings.exists():
            print(f"ERROR: Findings file not found: {latest_findings}")
            return False
    else:
        findings_dir = Path(results_dir)
        # By mtime, not name: run ids may be UUIDs (from the API) rather than
        # timestamps, so filename order is not chronological order. The name is
        # the tiebreak because mtime granularity is coarse enough that two files
        # written in the same tick would otherwise order arbitrarily.
        findings_files = sorted(
            findings_dir.glob("qa_findings_*.json"),
            key=lambda path: (path.stat().st_mtime, path.name),
            reverse=True,
        )

        if not findings_files:
            print(f"ERROR: No qa_findings_*.json files found in {findings_dir}/")
            return False

        latest_findings = findings_files[0]

    print(f"\nLoading: {latest_findings}")

    try:
        with open(latest_findings, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: Could not read findings file: {error}")
        return False

    summary = data.get("summary", {})
    page_findings = data.get("page_level_findings", [])
    candidates = data.get("root_cause_candidates", [])

    # ========================================================================
    # 1. RAW EVENTS VERIFICATION
    # ========================================================================
    print("\n" + "-" * 100)
    print("1. RAW EVENTS (from crawler)")
    print("-" * 100)

    raw_http = summary.get("raw_http_errors", 0)
    raw_console = summary.get("raw_console_errors", 0)
    raw_network = summary.get("raw_network_failures", 0)
    raw_total = summary.get("raw_events", 0)

    print(f"\nHTTP errors:      {raw_http}")
    print(f"Console errors:   {raw_console}")
    print(f"Network failures: {raw_network}")
    print(f"{'-' * 50}")
    print(f"TOTAL RAW EVENTS: {raw_total}")

    # ========================================================================
    # 2. PAGE-LEVEL FINDINGS VERIFICATION
    # ========================================================================
    print("\n" + "-" * 100)
    print("2. PAGE-LEVEL FINDINGS (level 1: deduplication by page+url+status)")
    print("-" * 100)

    by_type = summary.get("page_findings_by_type", {})
    http_findings = by_type.get("http_error", 0)
    console_findings = by_type.get("console_error", 0)
    network_findings = by_type.get("network_failure", 0)
    total_page_findings = summary.get("deduplicated_page_findings", len(page_findings))

    print(f"\nHTTP findings:      {http_findings}")
    print(f"Console findings:   {console_findings}")
    print(f"Network findings:   {network_findings}")
    print(f"{'-' * 50}")
    print(f"TOTAL PAGE FINDINGS: {total_page_findings}")

    if page_findings:
        print("\nPage-level findings samples:")
        for i, finding in enumerate(page_findings[:3], 1):
            print(
                f"  {i}. {finding.get('id')}: {finding.get('url', 'N/A')} "
                f"[{finding.get('status')}] on {finding.get('page', 'N/A')}"
            )

    # ========================================================================
    # 3. ROOT-CAUSE CANDIDATES VERIFICATION
    # ========================================================================
    print("\n" + "-" * 100)
    print("3. ROOT-CAUSE CANDIDATES (level 2: grouping by root-cause key)")
    print("-" * 100)

    total_candidates = summary.get("root_cause_candidates", len(candidates))
    severity_dist = summary.get("severity_distribution", {})

    print(f"\nTOTAL ROOT-CAUSE CANDIDATES: {total_candidates}")
    print("\nSeverity distribution:")
    for level in ("critical", "high", "medium", "low", "info"):
        if level in severity_dist:
            print(f"  {level.upper():<9}{severity_dist[level]}")

    print("\nRoot-cause candidate details:")
    for i, candidate in enumerate(candidates, 1):
        print(f"\n  {i}. {candidate.get('id')}")
        print(f"     Type:           {candidate.get('type')}")
        print(f"     Root-cause key: {candidate.get('root_cause_key')}")
        print(f"     URL:         {candidate.get('url') or 'N/A'}")
        print(f"     Status:      {candidate.get('status') if candidate.get('status') is not None else 'N/A'}")
        print(f"     Method:      {candidate.get('method') or 'N/A'}")
        print(f"     Occurrences: {candidate.get('occurrences', 0)}")
        print(f"     Severity:    {candidate.get('severity')}")
        print(f"     Confidence:  {candidate.get('confidence')}")

        evidence = candidate.get("evidence", {})
        print("     Evidence:")
        print(f"       - HTTP errors in candidate:      {len(evidence.get('http_errors', []))}")
        print(f"       - Console errors in candidate:   {len(evidence.get('console_errors', []))}")
        print(f"       - Network failures in candidate: {len(evidence.get('network_failures', []))}")

        affected_pages = candidate.get("affected_pages", [])
        print(f"     Affected pages: {len(affected_pages)}")
        if len(affected_pages) <= 3:
            for page in affected_pages:
                print(f"       - {page}")
        else:
            for page in affected_pages[:2]:
                print(f"       - {page}")
            print(f"       ... and {len(affected_pages) - 2} more")

    # ========================================================================
    # 4. DEDUPLICATION ANALYSIS
    # ========================================================================
    print("\n" + "-" * 100)
    print("4. DEDUPLICATION ANALYSIS")
    print("-" * 100)

    dedup_ratio_text = _fmt_ratio(raw_total, total_candidates)
    print(f"\nRaw events:       {raw_total}")
    print(f"Root candidates:  {total_candidates}")
    print(f"Dedup ratio:      {dedup_ratio_text}")
    if total_candidates:
        print(
            f"\nMeaning: {raw_total} raw events collapsed into "
            f"{total_candidates} root-cause candidates"
        )

    # ========================================================================
    # 5. GROUPING VERIFICATION
    # ========================================================================
    print("\n" + "-" * 100)
    print("5. GROUPING VERIFICATION")
    print("-" * 100)

    # Grouping is verified structurally: any candidate covering more than one
    # page-level finding proves collapsing works, and distinct root-cause keys
    # prove distinct issues stay separate. Naming specific endpoints here would
    # only pass for one particular target site.
    grouped = [c for c in candidates if c.get("occurrences", 0) > 1]
    distinct_keys = {c.get("root_cause_key") for c in candidates}

    print(f"\nCandidates covering more than one raw event: {len(grouped)}")
    for candidate in grouped[:5]:
        label = candidate.get("url") or candidate.get("error_text") or candidate.get("id")
        print(
            f"  - {label} "
            f"[{candidate.get('occurrences')} occurrences across "
            f"{candidate.get('affected_page_count', len(candidate.get('affected_pages', [])))} page(s)]"
        )

    print(f"\nDistinct root-cause keys: {len(distinct_keys)} for {len(candidates)} candidate(s)")

    # ========================================================================
    # 6. EVIDENCE PRESERVATION
    # ========================================================================
    print("\n" + "-" * 100)
    print("6. EVIDENCE PRESERVATION")
    print("-" * 100)

    print("\nEvidence items per candidate:")
    for candidate in candidates:
        evidence = candidate.get("evidence", {})
        total_evidence = (
            len(evidence.get("http_errors", []))
            + len(evidence.get("console_errors", []))
            + len(evidence.get("network_failures", []))
        )
        print(f"  - {candidate.get('id')}: {total_evidence} evidence items collected")

    print("\nAffected pages per candidate:")
    for candidate in candidates:
        print(
            f"  - {candidate.get('id')}: "
            f"{len(candidate.get('affected_pages', []))} affected pages"
        )

    print("\nScreenshots per candidate:")
    for candidate in candidates:
        print(
            f"  - {candidate.get('id')}: "
            f"{len(candidate.get('screenshots', []))} unique screenshots"
        )

    # ========================================================================
    # 7. FEATURE CHECKLIST
    # ========================================================================
    print("\n" + "-" * 100)
    print("7. INVARIANT CHECKLIST")
    print("-" * 100)

    # Every check below is an invariant of the algorithm rather than a snapshot
    # of one crawl. A clean site legitimately produces zero findings, so
    # "something was found" is not treated as a requirement.
    checks = [
        (
            "Summary raw-event total is internally consistent",
            raw_total == (raw_http + raw_console + raw_network),
        ),
        (
            "Page-finding count matches the page_level_findings array",
            total_page_findings == len(page_findings),
        ),
        (
            "Candidate count matches the root_cause_candidates array",
            total_candidates == len(candidates),
        ),
        (
            "Every page-level finding is represented in a candidate",
            sum(len(c.get("evidence", {}).get("http_errors", []))
                + len(c.get("evidence", {}).get("console_errors", []))
                + len(c.get("evidence", {}).get("network_failures", []))
                for c in candidates) >= len(page_findings),
        ),
        (
            "Grouping never inflates: candidates <= page findings",
            total_candidates <= max(total_page_findings, 0) or not page_findings,
        ),
        (
            "Every candidate carries at least one evidence item",
            all(
                len(c.get("evidence", {}).get("http_errors", []))
                + len(c.get("evidence", {}).get("console_errors", []))
                + len(c.get("evidence", {}).get("network_failures", []))
                > 0
                for c in candidates
            ),
        ),
        (
            "Every candidate names at least one affected page",
            all(len(c.get("affected_pages", [])) > 0 for c in candidates),
        ),
        (
            "Occurrences are never fewer than affected pages",
            all(
                c.get("occurrences", 0) >= len(c.get("affected_pages", []))
                for c in candidates
            ),
        ),
        (
            "page_screenshots pairing is aligned with affected_pages",
            # Absence is tolerated: findings files written before
            # page_screenshots existed are still valid inputs, and failing them
            # here would make the script report a defect in old artifacts rather
            # than in the current code.
            all(
                [p.get("page") for p in c["page_screenshots"]]
                == c.get("affected_pages", [])
                for c in candidates
                if "page_screenshots" in c
            ),
        ),
        (
            "Root-cause keys are structured and deterministic",
            all("|" in (c.get("root_cause_key") or "") for c in candidates),
        ),
        (
            "Root-cause keys are unique per candidate",
            len(distinct_keys) == len(candidates),
        ),
        (
            "Candidate IDs are unique",
            len({c.get("id") for c in candidates}) == len(candidates),
        ),
        (
            "Every candidate has a severity and confidence",
            all(c.get("severity") and c.get("confidence") for c in candidates),
        ),
        (
            "All finding types can become candidates",
            not page_findings
            or {f.get("type") for f in page_findings}
            == {c.get("type") for c in candidates},
        ),
    ]

    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {check_name}")

    all_passed = all(result for _, result in checks)

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "=" * 100)
    print("FINAL SUMMARY")
    print("=" * 100)

    print(f"\nInvariant status: {'ALL CHECKS PASSED' if all_passed else 'CHECKS FAILED'}")

    print("\nKey Metrics:")
    print(f"  - Raw events (from crawler):      {raw_total}")
    print(f"  - Page-level findings:            {total_page_findings}")
    print(f"  - Root-cause candidates:          {total_candidates}")
    print(f"  - Deduplication ratio:            {dedup_ratio_text}")

    print(f"\nOutput File: {latest_findings}")
    try:
        print(f"File size: {latest_findings.stat().st_size / 1024:.1f} KB")
    except OSError:
        pass

    print("\n" + "=" * 100 + "\n")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Verify root-cause grouping invariants in a qa_findings file"
    )
    parser.add_argument(
        "findings", nargs="?", help="Path to a qa_findings_*.json file"
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Directory to search when no findings file is given",
    )
    args = parser.parse_args()

    success = verify_implementation(
        findings_path=args.findings, results_dir=args.results_dir
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
