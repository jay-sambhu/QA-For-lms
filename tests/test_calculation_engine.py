#!/usr/bin/env python3
"""
Comprehensive Unit and Invariant Test Suite for QA Calculation Engine.

Validates all canonical QA metrics, invariants, deduplication rules,
grade boundaries, duration handling, zero-data edge cases, and large datasets.
"""

import unittest
from datetime import datetime, timezone
from pathlib import Path

from calculation_engine import (
    CalculationEngine,
    CanonicalQAMetrics,
    CrawlMetrics,
    FindingMetrics,
    InteractiveMetrics,
    QualityScore,
    TestCaseMetrics,
)
from qa_report_generator import QAReportGenerator


class TestCalculationEngine(unittest.TestCase):
    """Authoritative Calculation Engine test suite."""

    # =========================================================================
    # 1. TEST CASE COUNTS, STATUS NORMALIZATION & RATES
    # =========================================================================

    def test_test_cases_all_passed(self):
        """10 passed, 0 failed -> 100% pass, 0% fail."""
        test_cases = [{"id": f"TC-{i}", "status": "passed"} for i in range(10)]
        m = CalculationEngine.calculate_test_case_metrics(test_cases)

        self.assertEqual(m.total, 10)
        self.assertEqual(m.passed, 10)
        self.assertEqual(m.failed, 0)
        self.assertEqual(m.skipped, 0)
        self.assertEqual(m.blocked, 0)
        self.assertEqual(m.errored, 0)
        self.assertEqual(m.executed, 10)
        self.assertEqual(m.pass_rate, 100.0)
        self.assertEqual(m.fail_rate, 0.0)

    def test_test_cases_all_failed(self):
        """10 failed, 0 passed -> 0% pass, 100% fail."""
        test_cases = [{"id": f"TC-{i}", "status": "failed"} for i in range(10)]
        m = CalculationEngine.calculate_test_case_metrics(test_cases)

        self.assertEqual(m.total, 10)
        self.assertEqual(m.passed, 0)
        self.assertEqual(m.failed, 10)
        self.assertEqual(m.executed, 10)
        self.assertEqual(m.pass_rate, 0.0)
        self.assertEqual(m.fail_rate, 100.0)

    def test_test_cases_mixed_and_case_normalization(self):
        """Test status normalization (PASSED, Failed, manual_review, Blocked, ERRORED)."""
        test_cases = [
            {"id": "TC-1", "status": "PASSED"},
            {"id": "TC-2", "status": "Passed"},
            {"id": "TC-3", "status": "pass"},
            {"id": "TC-4", "status": "FAILED"},
            {"id": "TC-5", "status": "Failure"},
            {"id": "TC-6", "status": "manual_review"},  # skipped
            {"id": "TC-7", "status": "SKIPPED"},
            {"id": "TC-8", "status": "BLOCKED"},
            {"id": "TC-9", "status": "ERRORED"},
            {"id": "TC-10", "status": "unknown_status_xyz"},  # unknown classified as errored
        ]
        m = CalculationEngine.calculate_test_case_metrics(test_cases)

        self.assertEqual(m.total, 10)
        self.assertEqual(m.passed, 3)
        self.assertEqual(m.failed, 2)
        self.assertEqual(m.skipped, 2)
        self.assertEqual(m.blocked, 1)
        self.assertEqual(m.errored, 2)  # TC-9 + TC-10
        self.assertEqual(m.executed, 7)  # passed (3) + failed (2) + errored (2)

        # Invariant check
        self.assertEqual(m.passed + m.failed + m.skipped + m.blocked + m.errored, m.total)
        self.assertEqual(m.pass_rate, 30.0)
        self.assertEqual(m.fail_rate, 20.0)
        self.assertEqual(m.skip_rate, 20.0)
        self.assertEqual(m.block_rate, 10.0)
        self.assertEqual(m.errored_rate, 20.0)

    def test_test_cases_zero_total(self):
        """Zero test cases must produce exactly 0.0% without division-by-zero or NaN."""
        m = CalculationEngine.calculate_test_case_metrics([])

        self.assertEqual(m.total, 0)
        self.assertEqual(m.passed, 0)
        self.assertEqual(m.failed, 0)
        self.assertEqual(m.skipped, 0)
        self.assertEqual(m.blocked, 0)
        self.assertEqual(m.errored, 0)
        self.assertEqual(m.pass_rate, 0.0)
        self.assertEqual(m.fail_rate, 0.0)
        self.assertEqual(m.skip_rate, 0.0)
        self.assertEqual(m.block_rate, 0.0)
        self.assertEqual(m.errored_rate, 0.0)

    def test_rate_sum_invariant(self):
        """Rate sums equal 100.0% within floating tolerance."""
        test_cases = (
            [{"id": f"TC-P-{i}", "status": "passed"} for i in range(3)]
            + [{"id": f"TC-F-{i}", "status": "failed"} for i in range(3)]
            + [{"id": f"TC-S-{i}", "status": "skipped"} for i in range(3)]
            + [{"id": "TC-B-0", "status": "blocked"}]
        )
        m = CalculationEngine.calculate_test_case_metrics(test_cases)
        total_rate = m.pass_rate + m.fail_rate + m.skip_rate + m.block_rate + m.errored_rate

        self.assertAlmostEqual(total_rate, 100.0, places=1)

    # =========================================================================
    # 2. FINDING CALCULATIONS, NORMALIZATION & INVARIANTS
    # =========================================================================

    def test_findings_severity_and_priority_invariants(self):
        """Test invariant: P0..P4 == total, critical..info == total with mixed casing."""
        findings = [
            {"id": "F1", "severity": "CRITICAL", "priority": "P0"},
            {"id": "F2", "severity": "High", "priority": "p1"},
            {"id": "F3", "severity": "MEDIUM", "priority": "P2"},
            {"id": "F4", "severity": "Low", "priority": "p3"},
            {"id": "F5", "severity": "INFO", "priority": "P4"},
            {"id": "F6", "severity": "INVALID_SEV", "priority": "INVALID_PRI"},  # fallback info / P3
            {"id": "F7", "severity": None, "priority": None},  # fallback info / P3
        ]
        m = CalculationEngine.calculate_finding_metrics(findings)

        self.assertEqual(m.total, 7)
        self.assertEqual(sum(m.by_severity.values()), m.total)
        self.assertEqual(sum(m.by_priority.values()), m.total)
        self.assertEqual(m.by_severity["critical"], 1)
        self.assertEqual(m.by_severity["high"], 1)
        self.assertEqual(m.by_severity["medium"], 1)
        self.assertEqual(m.by_severity["low"], 1)
        self.assertEqual(m.by_severity["info"], 3)
        self.assertEqual(m.by_priority["P0"], 1)
        self.assertEqual(m.by_priority["P1"], 1)
        self.assertEqual(m.by_priority["P2"], 1)
        self.assertEqual(m.by_priority["P3"], 3)
        self.assertEqual(m.by_priority["P4"], 1)

    def test_findings_zero_total(self):
        """Zero findings returns all zeros safely."""
        m = CalculationEngine.calculate_finding_metrics([])
        self.assertEqual(m.total, 0)
        self.assertEqual(m.critical_high, 0)
        for s in CalculationEngine.SEVERITY_LEVELS:
            self.assertEqual(m.by_severity[s], 0)
        for p in CalculationEngine.PRIORITY_LEVELS:
            self.assertEqual(m.by_priority[p], 0)

    # =========================================================================
    # 3. DEDUPLICATION RULES
    # =========================================================================

    def test_deduplication_exact_duplicate(self):
        """Exact duplicate findings are collapsed."""
        findings = [
            {"id": "BUG-001", "title": "Missing alt tag", "severity": "low"},
            {"id": "BUG-001", "title": "Missing alt tag", "severity": "low"},
        ]
        m = CalculationEngine.calculate_finding_metrics(findings)
        self.assertEqual(m.total, 1)

    def test_deduplication_reordered_fields(self):
        """Duplicate with reordered dictionary keys are collapsed."""
        findings = [
            {"id": "BUG-002", "severity": "high", "title": "Broken link", "url": "https://example.com"},
            {"title": "Broken link", "id": "BUG-002", "url": "https://example.com", "severity": "high"},
        ]
        m = CalculationEngine.calculate_finding_metrics(findings)
        self.assertEqual(m.total, 1)

    def test_deduplication_same_title_different_location(self):
        """Same title on different pages/URLs are preserved as separate findings."""
        findings = [
            {"title": "Button Broken", "url": "https://example.com/page1", "type": "click_error"},
            {"title": "Button Broken", "url": "https://example.com/page2", "type": "click_error"},
        ]
        m = CalculationEngine.calculate_finding_metrics(findings)
        self.assertEqual(m.total, 2)

    def test_deduplication_same_location_different_issue(self):
        """Same location with different issue types are preserved."""
        findings = [
            {"title": "Console Error", "url": "https://example.com/login", "type": "console_error"},
            {"title": "HTTP 500", "url": "https://example.com/login", "type": "http_error"},
        ]
        m = CalculationEngine.calculate_finding_metrics(findings)
        self.assertEqual(m.total, 2)

    def test_deduplication_missing_optional_fields(self):
        """Findings with missing optional fields are safely handled."""
        findings = [
            {"id": "UNKNOWN", "candidate": {"fingerprint": "fp-123"}},
            {"id": "UNKNOWN", "candidate": {"fingerprint": "fp-123"}},
            {"id": "UNKNOWN", "url": "https://example.com"},
        ]
        m = CalculationEngine.calculate_finding_metrics(findings)
        self.assertEqual(m.total, 2)

    # =========================================================================
    # 4. PAGE CRAWL METRICS
    # =========================================================================

    def test_crawl_metrics_distinct_values(self):
        """Clearly distinguish discovered, crawled, failed, and max_pages."""
        crawl_data = {
            "pages_discovered": 15,
            "pages_crawled": 8,
            "pages_failed": 2,
            "max_pages": 20,
        }
        m = CalculationEngine.calculate_crawl_metrics(crawl_data, max_pages=20)

        self.assertEqual(m.pages_discovered, 15)
        self.assertEqual(m.pages_crawled, 8)
        self.assertEqual(m.pages_failed, 2)
        self.assertEqual(m.max_pages, 20)

    def test_crawl_metrics_never_defaults_crawled_to_max(self):
        """Crawler never uses max_pages as pages_crawled."""
        m = CalculationEngine.calculate_crawl_metrics(None, max_pages=50)
        self.assertEqual(m.pages_crawled, 0)
        self.assertEqual(m.max_pages, 50)

    # =========================================================================
    # 5. DURATION CALCULATION
    # =========================================================================

    def test_duration_datetime_objects(self):
        """Duration from naive and aware datetime objects."""
        t1 = datetime(2026, 9, 1, 10, 0, 0)
        t2 = datetime(2026, 9, 1, 10, 1, 30)
        self.assertEqual(CalculationEngine.normalize_duration(t1, t2), 90.0)

    def test_duration_iso_strings(self):
        """Duration from ISO strings with timezone."""
        t1 = "2026-09-01T10:00:00Z"
        t2 = "2026-09-01T10:02:15.500Z"
        self.assertEqual(CalculationEngine.normalize_duration(t1, t2), 135.5)

    def test_duration_negative_clamped_to_zero(self):
        """Negative duration clamped to 0.0."""
        t1 = datetime(2026, 9, 1, 10, 5, 0)
        t2 = datetime(2026, 9, 1, 10, 0, 0)
        self.assertEqual(CalculationEngine.normalize_duration(t1, t2), 0.0)

    def test_duration_missing_or_invalid(self):
        """Missing or invalid timestamps return 0.0."""
        self.assertEqual(CalculationEngine.normalize_duration(None, datetime.now()), 0.0)
        self.assertEqual(CalculationEngine.normalize_duration("invalid", "invalid2"), 0.0)

    # =========================================================================
    # 6. QUALITY SCORE & GRADE BOUNDARIES
    # =========================================================================

    def test_quality_score_clean_scan(self):
        """Clean scan gets 100 and Grade A."""
        f = FindingMetrics()
        t = TestCaseMetrics(total=5, passed=5, pass_rate=100.0)
        qs = CalculationEngine.calculate_quality_score(f, t)
        self.assertEqual(qs.score, 100)
        self.assertEqual(qs.grade, "A")
        self.assertEqual(qs.summary, "Excellent")

    def test_quality_score_formula_penalties(self):
        """
        Verify: 100 - (25*crit) - (15*high) - (5*med) - (1*low) - (0.3*fail_rate)
        1 crit (-25), 1 high (-15), 1 med (-5), 1 low (-1), fail_rate 50% (-15)
        Expected score = 100 - 25 - 15 - 5 - 1 - 15 = 39 (Grade F)
        """
        f = FindingMetrics(by_severity={"critical": 1, "high": 1, "medium": 1, "low": 1, "info": 0})
        t = TestCaseMetrics(total=10, failed=5, fail_rate=50.0)
        qs = CalculationEngine.calculate_quality_score(f, t)
        self.assertEqual(qs.score, 39)
        self.assertEqual(qs.grade, "F")

    def test_quality_score_grade_boundaries(self):
        """Test exact grade boundaries: 100, 99, 90, 89, 80, 79, 70, 69, 60, 59, 0."""
        boundaries = [
            (100, "A"),
            (99, "A"),
            (90, "A"),
            (89, "B"),
            (80, "B"),
            (79, "C"),
            (70, "C"),
            (69, "D"),
            (60, "D"),
            (59, "F"),
            (0, "F"),
        ]
        for target_score, expected_grade in boundaries:
            # Construct a finding set to hit the target score exactly
            deduction = 100 - target_score
            f = FindingMetrics(by_severity={"critical": 0, "high": 0, "medium": 0, "low": deduction, "info": 0})
            t = TestCaseMetrics(total=0)
            qs = CalculationEngine.calculate_quality_score(f, t)
            self.assertEqual(qs.score, target_score, f"Failed score for target {target_score}")
            self.assertEqual(qs.grade, expected_grade, f"Failed grade for score {target_score}")

    # =========================================================================
    # 7. ZERO-DATA TESTS
    # =========================================================================

    def test_zero_data_empty_scan(self):
        """Empty scan input produces safe defaults without crashing."""
        canonical = CalculationEngine.calculate_canonical_metrics(
            raw_data={},
            crawl_data=None,
            interactive_data=None,
            test_cases=None,
            test_results=None,
            start_time=None,
            end_time=None,
        )
        self.assertEqual(canonical.target, "Unknown")
        self.assertEqual(canonical.duration_seconds, 0.0)
        self.assertEqual(canonical.findings.total, 0)
        self.assertEqual(canonical.test_cases.total, 0)
        self.assertEqual(canonical.crawl.pages_crawled, 0)
        self.assertEqual(canonical.interactive.interactions_attempted, 0)
        self.assertEqual(canonical.quality_score.score, 100)
        self.assertEqual(canonical.quality_score.grade, "A")

    # =========================================================================
    # 8. LARGE DATASET BENCHMARK
    # =========================================================================

    def test_large_dataset_benchmark(self):
        """5,000 findings + 5,000 test cases process deterministically and quickly."""
        findings = [{"id": f"BUG-{i}", "severity": "medium", "priority": "P2"} for i in range(5000)]
        tests = [{"id": f"TC-{i}", "status": "passed" if i % 2 == 0 else "failed"} for i in range(5000)]

        start = datetime.now()
        canonical = CalculationEngine.calculate_canonical_metrics(
            raw_data={"target": "https://benchmark.example.com", "findings": findings},
            test_cases=tests,
        )
        elapsed = (datetime.now() - start).total_seconds()

        self.assertEqual(canonical.findings.total, 5000)
        self.assertEqual(canonical.test_cases.total, 5000)
        self.assertEqual(canonical.test_cases.passed, 2500)
        self.assertEqual(canonical.test_cases.failed, 2500)
        self.assertEqual(canonical.test_cases.pass_rate, 50.0)
        self.assertEqual(canonical.test_cases.fail_rate, 50.0)
        self.assertLess(elapsed, 1.5)

    # =========================================================================
    # 9. REPORT GENERATOR INTEGRATION
    # =========================================================================

    def test_report_generator_integration(self):
        """Verify QAReportGenerator delegates to CalculationEngine."""
        gen = QAReportGenerator()
        raw_data = {
            "target": "https://example.com",
            "findings": [
                {"id": "F-1", "severity": "critical", "priority": "P0", "classification": "confirmed_bug"},
                {"id": "F-2", "severity": "low", "priority": "P3", "classification": "informational"},
            ]
        }
        report = gen.generate_json_report(Path("dummy.json"), raw_data)

        self.assertEqual(report["summary"]["total_candidates"], 2)
        self.assertEqual(report["summary"]["confirmed_bugs"], 1)
        self.assertEqual(report["severity"]["critical"], 1)
        self.assertEqual(report["severity"]["low"], 1)
        self.assertIn("qa_metrics", report)
        self.assertEqual(report["qa_metrics"]["quality_score"]["score"], 74)  # 100 - 25 - 1 = 74
        self.assertEqual(report["qa_metrics"]["quality_score"]["grade"], "C")


if __name__ == "__main__":
    unittest.main()
