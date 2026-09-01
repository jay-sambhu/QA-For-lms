#!/usr/bin/env python3
"""
Authoritative QA Calculation Engine

Single backend source of truth for all QA calculation metrics,
including test case execution, findings by severity and priority, crawl
metrics, interactive testing metrics, pass/fail rates, durations, and
deterministic site health scoring.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union


@dataclass
class TestCaseMetrics:
    __test__ = False
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0  # includes safety skips and manual review policies
    blocked: int = 0
    errored: int = 0
    executed: int = 0  # passed + failed + errored
    pass_rate: float = 0.0  # percentage 0.0 - 100.0 (2 decimal places)
    fail_rate: float = 0.0  # percentage 0.0 - 100.0 (2 decimal places)
    skip_rate: float = 0.0  # percentage 0.0 - 100.0 (2 decimal places)
    block_rate: float = 0.0  # percentage 0.0 - 100.0 (2 decimal places)
    errored_rate: float = 0.0  # percentage 0.0 - 100.0 (2 decimal places)
    duration_ms: int = 0


@dataclass
class FindingMetrics:
    total: int = 0
    by_severity: Dict[str, int] = field(default_factory=lambda: {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
    })
    by_priority: Dict[str, int] = field(default_factory=lambda: {
        "P0": 0,
        "P1": 0,
        "P2": 0,
        "P3": 0,
        "P4": 0,
    })
    by_classification: Dict[str, int] = field(default_factory=lambda: {
        "confirmed_bug": 0,
        "high_confidence_candidate": 0,
        "needs_manual_review": 0,
        "expected_behavior": 0,
        "informational": 0,
        "duplicate": 0,
        "ignored": 0,
    })
    by_regression: Dict[str, int] = field(default_factory=lambda: {
        "new": 0,
        "fixed": 0,
        "unchanged": 0,
        "worsened": 0,
        "improved": 0,
    })
    critical_high: int = 0
    analysis_failures: int = 0


@dataclass
class CrawlMetrics:
    pages_discovered: int = 0
    pages_crawled: int = 0
    pages_failed: int = 0
    max_pages: int = 0
    devices_tested: int = 3
    responsive_findings: int = 0
    device_breakdown: Dict[str, int] = field(default_factory=lambda: {
        "desktop": 0,
        "iphone": 0,
        "ipad": 0,
    })


@dataclass
class InteractiveMetrics:
    elements_discovered: int = 0
    interactions_attempted: int = 0
    passed: int = 0
    failed: int = 0
    manual_review: int = 0
    pass_rate: float = 0.0


@dataclass
class QualityScore:
    score: int = 100
    grade: str = "A"
    summary: str = "Healthy"


@dataclass
class CanonicalQAMetrics:
    target: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_seconds: float = 0.0
    crawl: CrawlMetrics = field(default_factory=CrawlMetrics)
    test_cases: TestCaseMetrics = field(default_factory=TestCaseMetrics)
    findings: FindingMetrics = field(default_factory=FindingMetrics)
    interactive: InteractiveMetrics = field(default_factory=InteractiveMetrics)
    quality_score: QualityScore = field(default_factory=QualityScore)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to fully serializable dictionary."""
        return asdict(self)


class CalculationEngine:
    """Core Authoritative Calculation Engine for all QA metrics."""

    SEVERITY_LEVELS = ("critical", "high", "medium", "low", "info")
    PRIORITY_LEVELS = ("P0", "P1", "P2", "P3", "P4")
    CLASSIFICATION_LEVELS = (
        "confirmed_bug",
        "high_confidence_candidate",
        "needs_manual_review",
        "expected_behavior",
        "informational",
        "duplicate",
        "ignored",
    )
    REGRESSION_LEVELS = ("new", "fixed", "unchanged", "worsened", "improved")

    @classmethod
    def calculate_rate(cls, count: int, total: int, decimals: int = 2) -> float:
        """
        Calculate percentage safely avoiding division-by-zero, NaN, or Infinity.
        When total == 0 or count <= 0, returns exactly 0.0.
        """
        if not total or total <= 0 or not count or count <= 0:
            return 0.0
        return round((float(count) / float(total)) * 100.0, decimals)

    @classmethod
    def normalize_severity(cls, raw_sev: Optional[str]) -> str:
        """
        Normalize severity string to standard set: critical, high, medium, low, info.
        Case-insensitive with safe fallback to 'info'.
        """
        if not raw_sev:
            return "info"
        s = str(raw_sev).strip().lower()
        if s in cls.SEVERITY_LEVELS:
            return s
        if "crit" in s:
            return "critical"
        if "high" in s:
            return "high"
        if "med" in s:
            return "medium"
        if "low" in s:
            return "low"
        if "info" in s:
            return "info"
        return "info"

    @classmethod
    def normalize_priority(cls, raw_pri: Optional[str]) -> str:
        """
        Normalize priority string to standard set P0-P4.
        Case-insensitive with safe fallback to 'P3'.
        """
        if not raw_pri:
            return "P3"
        p = str(raw_pri).strip().upper()
        if p in cls.PRIORITY_LEVELS:
            return p
        if "P0" in p or "CRITICAL" in p or "BLOCKER" in p:
            return "P0"
        if "P1" in p or "HIGH" in p:
            return "P1"
        if "P2" in p or "MED" in p:
            return "P2"
        if "P3" in p or "LOW" in p:
            return "P3"
        if "P4" in p or "TRIVIAL" in p:
            return "P4"
        return "P3"

    @classmethod
    def normalize_classification(cls, raw_cls: Optional[str]) -> str:
        """Normalize classification string with safe fallback."""
        if not raw_cls:
            return "ignored"
        c = str(raw_cls).strip().lower()
        if c in cls.CLASSIFICATION_LEVELS:
            return c
        if "confirmed" in c:
            return "confirmed_bug"
        if "candidate" in c or "likely" in c:
            return "high_confidence_candidate"
        if "manual" in c or "review" in c:
            return "needs_manual_review"
        if "expected" in c:
            return "expected_behavior"
        if "info" in c:
            return "informational"
        if "dup" in c:
            return "duplicate"
        return "ignored"

    @classmethod
    def normalize_duration(
        cls,
        start_time: Optional[Union[datetime, str, float, int]],
        end_time: Optional[Union[datetime, str, float, int]],
    ) -> float:
        """
        Compute duration in seconds safely.
        Handles datetime objects (naive/aware), ISO timestamp strings,
        or numeric timestamps. Clamps negative durations to 0.0.
        """
        if start_time is None or end_time is None:
            return 0.0

        def to_datetime(val: Any) -> Optional[datetime]:
            if isinstance(val, datetime):
                return val
            if isinstance(val, (int, float)):
                try:
                    return datetime.fromtimestamp(val, tz=timezone.utc)
                except (OverflowError, ValueError):
                    return None
            if isinstance(val, str):
                val_str = val.strip()
                if not val_str:
                    return None
                try:
                    # ISO format parsing
                    if val_str.endswith("Z"):
                        val_str = val_str[:-1] + "+00:00"
                    return datetime.fromisoformat(val_str)
                except ValueError:
                    return None
            return None

        dt_start = to_datetime(start_time)
        dt_end = to_datetime(end_time)

        if not dt_start or not dt_end:
            return 0.0

        # Align timezones if one is aware and one is naive
        if dt_start.tzinfo is not None and dt_end.tzinfo is None:
            dt_end = dt_end.replace(tzinfo=dt_start.tzinfo)
        elif dt_start.tzinfo is None and dt_end.tzinfo is not None:
            dt_start = dt_start.replace(tzinfo=dt_end.tzinfo)

        duration = (dt_end - dt_start).total_seconds()
        return max(0.0, round(duration, 2))

    @classmethod
    def deduplicate_findings(cls, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate findings deterministically.
        Stable deduplication key based on finding ID, candidate fingerprint,
        or unique tuple (URL, finding type, title, location).
        Does NOT accidentally merge genuinely different bugs.
        """
        if not findings:
            return []
        seen_keys: Set[str] = set()
        unique_findings: List[Dict[str, Any]] = []

        for f in findings:
            fid = f.get("id")
            cand = f.get("candidate") or {}
            fp = f.get("fingerprint") or cand.get("fingerprint")
            url = f.get("url") or cand.get("url") or ""
            ftype = f.get("type") or cand.get("type") or f.get("finding_type") or ""
            title = f.get("title") or cand.get("title") or ""
            page = f.get("page") or (cand.get("affected_pages", [""])[0] if cand.get("affected_pages") else "")

            if fid and fid != "UNKNOWN":
                dedup_key = f"id:{fid}"
            elif fp:
                dedup_key = f"fp:{fp}"
            else:
                # Disambiguate by URL, page location, issue type, and title
                dedup_key = f"tuple:{url.strip().lower()}|{page.strip().lower()}|{ftype.strip().lower()}|{title.strip().lower()}"

            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                unique_findings.append(f)

        return unique_findings

    @classmethod
    def deduplicate_test_cases(cls, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate test cases by test ID or target spec."""
        if not test_cases:
            return []
        seen_keys: Set[str] = set()
        unique_tc: List[Dict[str, Any]] = []

        for tc in test_cases:
            tcid = tc.get("id")
            source = tc.get("source_page", "")
            target_el = tc.get("target_element") or {}
            selector = target_el.get("selector", "")
            title = tc.get("title", "")

            if tcid:
                dedup_key = f"id:{tcid}"
            else:
                dedup_key = f"spec:{source}|{selector}|{title}"

            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                unique_tc.append(tc)

        return unique_tc

    @classmethod
    def calculate_test_case_metrics(
        cls,
        test_cases: Optional[List[Dict[str, Any]]],
        test_results: Optional[List[Dict[str, Any]]] = None,
    ) -> TestCaseMetrics:
        """
        Calculate comprehensive test execution metrics.
        
        Canonical states:
        - PASSED
        - FAILED
        - SKIPPED (including manual_review policy)
        - BLOCKED
        - ERRORED
        
        Invariant:
        passed + failed + skipped + blocked + errored == total
        
        Deterministic policy:
        Unknown / invalid statuses are classified as ERRORED.
        """
        m = TestCaseMetrics()
        if not test_cases:
            return m

        dedup_cases = cls.deduplicate_test_cases(test_cases)
        m.total = len(dedup_cases)

        results_by_id = {}
        if test_results:
            for r in test_results:
                tid = r.get("test_id") or r.get("id")
                if tid:
                    results_by_id[tid] = r

        total_duration = 0

        for tc in dedup_cases:
            tid = tc.get("id")
            res = results_by_id.get(tid, {}) if tid else {}
            
            # Determine status with priority: result status -> test_case status -> execution_policy
            raw_status = res.get("status") or tc.get("status") or tc.get("execution_policy", "manual_review")
            status = str(raw_status).strip().lower() if raw_status is not None else "skipped"

            duration = res.get("duration_ms", 0) or tc.get("duration_ms", 0)
            total_duration += duration if isinstance(duration, (int, float)) and duration > 0 else 0

            if status in ("passed", "pass", "success"):
                m.passed += 1
            elif status in ("failed", "fail", "failure"):
                m.failed += 1
            elif status in ("manual_review", "skipped", "skip"):
                m.skipped += 1
            elif status in ("blocked", "block"):
                m.blocked += 1
            elif status in ("errored", "error"):
                m.errored += 1
            else:
                # Deterministic handling: unknown execution statuses are classified as ERRORED
                m.errored += 1

        # Executed represents tests that actually ran automated assertion passes/fails/errors
        m.executed = m.passed + m.failed + m.errored
        m.duration_ms = total_duration

        # Invariant check: passed + failed + skipped + blocked + errored == total
        computed_sum = m.passed + m.failed + m.skipped + m.blocked + m.errored
        if computed_sum != m.total:
            m.errored += (m.total - computed_sum)

        m.pass_rate = cls.calculate_rate(m.passed, m.total)
        m.fail_rate = cls.calculate_rate(m.failed, m.total)
        m.skip_rate = cls.calculate_rate(m.skipped, m.total)
        m.block_rate = cls.calculate_rate(m.blocked, m.total)
        m.errored_rate = cls.calculate_rate(m.errored, m.total)

        return m

    @classmethod
    def calculate_finding_metrics(
        cls,
        findings: Optional[List[Dict[str, Any]]],
        analysis_failures: int = 0,
        raw_regression_summary: Optional[Dict[str, int]] = None,
    ) -> FindingMetrics:
        """
        Calculate finding summaries, severity breakdowns, and priority breakdowns.
        Guarantees invariants:
        P0 + P1 + P2 + P3 + P4 == total_findings
        critical + high + medium + low + info == total_findings
        """
        m = FindingMetrics(analysis_failures=analysis_failures)
        if not findings:
            return m

        dedup_findings = cls.deduplicate_findings(findings)
        m.total = len(dedup_findings)

        for f in dedup_findings:
            # 1. Severity
            sev = cls.normalize_severity(f.get("severity"))
            m.by_severity[sev] = m.by_severity.get(sev, 0) + 1

            # 2. Priority
            cand = f.get("candidate") or {}
            triage = cand.get("triage") or {}
            raw_pri = f.get("priority") or triage.get("priority") or cand.get("priority")
            pri = cls.normalize_priority(raw_pri)
            m.by_priority[pri] = m.by_priority.get(pri, 0) + 1

            # 3. Classification
            raw_cls = f.get("classification") or triage.get("classification") or cand.get("classification")
            c_cls = cls.normalize_classification(raw_cls)
            m.by_classification[c_cls] = m.by_classification.get(c_cls, 0) + 1

            # 4. Regression Status
            raw_reg = f.get("regression_status") or cand.get("regression_status", "new")
            reg_status = str(raw_reg).strip().lower()
            if reg_status in m.by_regression:
                m.by_regression[reg_status] += 1
            else:
                m.by_regression["new"] += 1

        m.critical_high = m.by_severity.get("critical", 0) + m.by_severity.get("high", 0)

        # Merge explicit regression summary if provided
        if raw_regression_summary:
            for k in cls.REGRESSION_LEVELS:
                if k in raw_regression_summary:
                    m.by_regression[k] = raw_regression_summary[k]

        return m

    @classmethod
    def calculate_crawl_metrics(
        cls,
        crawl_data: Optional[Dict[str, Any]],
        findings: Optional[List[Dict[str, Any]]] = None,
        max_pages: Optional[int] = None,
    ) -> CrawlMetrics:
        """
        Calculate crawler pages and cross-device responsive metrics.
        Clearly distinguishes pages_discovered, pages_crawled, pages_failed, max_pages.
        """
        m = CrawlMetrics()
        if crawl_data:
            m.pages_crawled = crawl_data.get("pages_crawled", 0) or 0
            m.pages_discovered = crawl_data.get("pages_discovered", m.pages_crawled) or 0
            m.pages_failed = crawl_data.get("pages_failed", 0) or 0
            m.max_pages = max_pages if max_pages is not None else (crawl_data.get("max_pages", 0) or 0)
        elif max_pages is not None:
            m.max_pages = max_pages

        if findings:
            for f in findings:
                cand = f.get("candidate") or {}
                ftype = f.get("type") or cand.get("type", "")
                title = (f.get("title") or cand.get("title", "")).lower()

                if ftype == "responsive_issue" or "responsive" in title or "overflow" in title:
                    m.responsive_findings += 1
                    devs = f.get("affected_devices") or cand.get("affected_devices") or []
                    if not devs and (f.get("device") or cand.get("device")):
                        devs = [f.get("device") or cand.get("device")]
                    for dev in devs:
                        d_lower = str(dev).lower()
                        if "desktop" in d_lower:
                            m.device_breakdown["desktop"] += 1
                        elif "iphone" in d_lower:
                            m.device_breakdown["iphone"] += 1
                        elif "ipad" in d_lower:
                            m.device_breakdown["ipad"] += 1

        return m

    @classmethod
    def calculate_interactive_metrics(
        cls,
        interactive_data: Optional[Dict[str, Any]],
    ) -> InteractiveMetrics:
        """Calculate deterministic interactive tester metrics."""
        m = InteractiveMetrics()
        if not interactive_data:
            return m

        summary = interactive_data.get("summary") or {}
        m.elements_discovered = summary.get("elements_discovered", 0) or 0
        m.interactions_attempted = summary.get("interactions_attempted", 0) or 0
        m.passed = summary.get("passed", 0) or 0
        m.failed = summary.get("failed", 0) or 0
        m.manual_review = summary.get("manual_review", 0) or 0

        m.pass_rate = cls.calculate_rate(m.passed, m.interactions_attempted)
        return m

    @classmethod
    def calculate_quality_score(
        cls,
        finding_metrics: FindingMetrics,
        test_case_metrics: TestCaseMetrics,
    ) -> QualityScore:
        """
        Calculate deterministic QA Health Score from 0 to 100 and letter grade.
        
        Formula:
        Score = 100 - (25 * Critical) - (15 * High) - (5 * Medium) - (1 * Low) - (0.3 * FailRate)
        Clamped to [0, 100].
        
        Grade Boundaries:
        - 90 - 100: "A" ("Excellent")
        - 80 - 89:  "B" ("Good")
        - 70 - 79:  "C" ("Fair")
        - 60 - 69:  "D" ("Poor")
        - 0 - 59:   "F" ("Critical Issues Detected")
        """
        score = 100.0

        # Finding severity deductions
        crit_count = finding_metrics.by_severity.get("critical", 0)
        high_count = finding_metrics.by_severity.get("high", 0)
        med_count = finding_metrics.by_severity.get("medium", 0)
        low_count = finding_metrics.by_severity.get("low", 0)

        score -= crit_count * 25.0
        score -= high_count * 15.0
        score -= med_count * 5.0
        score -= low_count * 1.0

        # Test case failure rate deduction
        if test_case_metrics.total > 0:
            score -= (test_case_metrics.fail_rate * 0.3)

        # Strict clamping between 0 and 100
        final_score = int(max(0.0, min(100.0, round(score))))

        if final_score >= 90:
            grade = "A"
            summary = "Excellent"
        elif final_score >= 80:
            grade = "B"
            summary = "Good"
        elif final_score >= 70:
            grade = "C"
            summary = "Fair"
        elif final_score >= 60:
            grade = "D"
            summary = "Poor"
        else:
            grade = "F"
            summary = "Critical Issues Detected"

        return QualityScore(score=final_score, grade=grade, summary=summary)

    @classmethod
    def calculate_canonical_metrics(
        cls,
        raw_data: Dict[str, Any],
        crawl_data: Optional[Dict[str, Any]] = None,
        interactive_data: Optional[Dict[str, Any]] = None,
        test_cases: Optional[List[Dict[str, Any]]] = None,
        test_results: Optional[List[Dict[str, Any]]] = None,
        start_time: Optional[Union[datetime, str, float, int]] = None,
        end_time: Optional[Union[datetime, str, float, int]] = None,
        max_pages: Optional[int] = None,
    ) -> CanonicalQAMetrics:
        """Compute the full authoritative canonical QA metrics model."""
        target = raw_data.get("target") or (crawl_data.get("target") if crawl_data else "Unknown")
        findings = raw_data.get("findings") or []
        
        source_summary = raw_data.get("summary") or {}
        analysis_failures = source_summary.get("analysis_failures", 0) or 0
        raw_regression = source_summary.get("triage_metrics", {}).get("regression_summary") or raw_data.get("triage_metrics", {}).get("regression_summary")

        # 1. Compute duration safely
        duration_seconds = cls.normalize_duration(start_time, end_time)

        # 2. Compute individual components
        finding_metrics = cls.calculate_finding_metrics(
            findings=findings,
            analysis_failures=analysis_failures,
            raw_regression_summary=raw_regression,
        )
        tc_metrics = cls.calculate_test_case_metrics(
            test_cases=test_cases,
            test_results=test_results,
        )
        crawl_metrics = cls.calculate_crawl_metrics(
            crawl_data=crawl_data,
            findings=findings,
            max_pages=max_pages,
        )
        int_metrics = cls.calculate_interactive_metrics(
            interactive_data=interactive_data,
        )
        quality_score = cls.calculate_quality_score(
            finding_metrics=finding_metrics,
            test_case_metrics=tc_metrics,
        )

        return CanonicalQAMetrics(
            target=target,
            duration_seconds=duration_seconds,
            crawl=crawl_metrics,
            test_cases=tc_metrics,
            findings=finding_metrics,
            interactive=int_metrics,
            quality_score=quality_score,
        )
