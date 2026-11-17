"""
Evidence-based Test Case Executor (V2 Engine).

Navigation and authorization test cases are verified against what the
crawler actually observed for the target URL (HTTP status of the final
response, redirects to a login page, uncaught JavaScript exceptions raised
while the page loaded). Steps that need a live interactive browser session
(fill, click, submit) are reported as SKIPPED, never as passed.
"""
import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from core.oracle.assertion_engine import AssertionEngine
from core.schemas.execution_result import TestExecutionResultModel, AssertionResultModel, TestResultStatus
from core.schemas.test_case import TestCaseModel, TestCategory

NOT_EXECUTED_REASON = "Not executed: interactive steps (fill/click/submit) require a live browser session."
NO_EVIDENCE_REASON = "Not executed: the crawler recorded no render of this URL."


def _normalize(url: str) -> str:
    """Comparable form of a URL: lowercase host, no fragment, no trailing slash."""
    if not url:
        return ""
    parsed = urlparse(str(url).strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "/").rstrip("/") or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{host}{path}{query}"


class SelfHealingExecutor:
    __test__ = False

    def __init__(self, test_cases_file: str, results_dir: str, run_id: str, crawl_file: Optional[str] = None,
                 crawl_result: Optional[Dict[str, Any]] = None):
        self.test_cases_file = test_cases_file
        self.results_dir = results_dir
        self.run_id = run_id
        self.output_file = os.path.join(results_dir, f"execution_results_{run_id}.json")
        self.crawl_file = crawl_file
        self.crawl_result = crawl_result
        self._pages_by_url: Dict[str, List[Dict[str, Any]]] = {}
        self._page_errors_by_url: Dict[str, List[str]] = {}
        self._credentials_supplied = False

    def _load_crawl(self) -> None:
        data = self.crawl_result
        if data is None and self.crawl_file and os.path.exists(self.crawl_file):
            try:
                with open(self.crawl_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = None
        data = data or {}
        self._credentials_supplied = bool(data.get("auth_credentials_supplied"))

        for page in data.get("pages", []) or []:
            if page.get("error"):
                continue
            url = page.get("actual_url") or str(page.get("url", "")).rsplit(" [", 1)[0]
            self._pages_by_url.setdefault(_normalize(url), []).append(page)

        for err in data.get("console_errors", []) or []:
            if err.get("source") != "pageerror":
                continue
            page_id = str(err.get("page", "")).rsplit(" [", 1)[0]
            key = _normalize(page_id)
            text = str(err.get("text") or "")
            bucket = self._page_errors_by_url.setdefault(key, [])
            if text not in bucket:
                bucket.append(text)

    def _record_for(self, url: str) -> Optional[Dict[str, Any]]:
        """The desktop render of `url` if there is one, else any render."""
        records = self._pages_by_url.get(_normalize(url)) or []
        for rec in records:
            if "desktop" in str(rec.get("device", "")).lower():
                return rec
        return records[0] if records else None

    def _navigation_assertions(self, url: str, category: TestCategory) -> tuple[List[AssertionResultModel], List[Dict[str, Any]], Optional[str]]:
        rec = self._record_for(url)
        if rec is None:
            return [], [{"step": "navigate", "url": url, "result": "skipped", "reason": NO_EVIDENCE_REASON}], NO_EVIDENCE_REASON

        status = rec.get("status")
        auth_wall = bool(rec.get("auth_wall"))
        final_url = rec.get("final_url") or url
        page_errors = self._page_errors_by_url.get(_normalize(url), [])
        step_result = {
            "step": "navigate",
            "url": url,
            "device": rec.get("device"),
            "observed_status": status,
            "final_url": final_url,
            "redirected": bool(rec.get("redirected")),
            "auth_wall": auth_wall,
            "uncaught_exceptions": page_errors[:5],
            "screenshot": rec.get("screenshot"),
        }

        if category == TestCategory.AUTHORIZATION:
            denied = auth_wall or (isinstance(status, int) and status in (401, 403))
            if denied:
                assertion = AssertionResultModel(
                    assertion_type="access_denied",
                    expected="redirect to login or HTTP 401/403",
                    actual=f"HTTP {status}, redirected to {final_url}" if auth_wall else f"HTTP {status}",
                    passed=True,
                    message="Unauthenticated access was denied as expected.",
                )
                step_result["result"] = "passed"
                return [assertion], [step_result], None
            reason = (
                "Inconclusive: the page rendered without a login redirect. The crawl session may have been "
                "authenticated, so unauthenticated access cannot be judged from crawl evidence."
            )
            step_result["result"] = "needs_review"
            step_result["reason"] = reason
            return [], [step_result], reason

        if auth_wall and not self._credentials_supplied:
            reason = (
                "Not executed: the page requires authentication (redirected to a login page) and no "
                "credentials were supplied for this scan."
            )
            step_result["result"] = "skipped"
            step_result["reason"] = reason
            return [], [step_result], reason

        assertions: List[AssertionResultModel] = []
        if isinstance(status, int):
            assertions.append(AssertionResultModel(
                assertion_type="http_status",
                expected="< 400",
                actual=status,
                passed=status < 400,
                message=f"Page responded with HTTP {status}",
            ))
        else:
            assertions.append(AssertionResultModel(
                assertion_type="http_status",
                expected="< 400",
                actual=None,
                passed=False,
                message="No HTTP response was recorded for the page",
            ))

        if auth_wall:
            assertions.append(AssertionResultModel(
                assertion_type="no_auth_redirect",
                expected=url,
                actual=final_url,
                passed=False,
                message="Page redirected to a login or external page instead of rendering",
            ))

        assertions.append(AssertionEngine.assert_no_console_errors(page_errors))
        assertions[-1].message = (
            f"Uncaught JavaScript exceptions during load: {len(page_errors)}"
            + (f" ({page_errors[0][:120]})" if page_errors else "")
        )

        step_result["result"] = "passed" if all(a.passed for a in assertions) else "failed"
        return assertions, [step_result], None

    async def execute_suite(self) -> List[TestExecutionResultModel]:
        if not os.path.exists(self.test_cases_file):
            return []

        with open(self.test_cases_file, "r", encoding="utf-8") as f:
            raw_cases = json.load(f)

        self._load_crawl()

        results: List[TestExecutionResultModel] = []
        for raw in raw_cases:
            tc = TestCaseModel(**raw)
            start_time = time.time()
            executed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            assertions: List[AssertionResultModel] = []
            step_results: List[Dict[str, Any]] = []
            skip_reason: Optional[str] = None
            screenshots: List[str] = []

            for step in tc.steps:
                action = (step.action or "").lower()
                if action == "navigate" and step.value:
                    nav_assertions, nav_steps, reason = self._navigation_assertions(step.value, tc.category)
                    assertions.extend(nav_assertions)
                    step_results.extend(nav_steps)
                    for s in nav_steps:
                        if s.get("screenshot"):
                            screenshots.append(s["screenshot"])
                    if reason and not skip_reason:
                        skip_reason = reason
                else:
                    step_results.append({
                        "step": action or "unknown",
                        "selector": step.target_selector,
                        "result": "skipped",
                        "reason": NOT_EXECUTED_REASON,
                    })
                    if not skip_reason:
                        skip_reason = NOT_EXECUTED_REASON

            if skip_reason:
                # A test with any unexecuted step was not verified; its
                # executed navigation evidence is kept for the reader.
                final_status = TestResultStatus.SKIPPED
            else:
                final_status = AssertionEngine.determine_final_status(assertions)
                if final_status == TestResultStatus.INCONCLUSIVE:
                    final_status = TestResultStatus.SKIPPED
                    skip_reason = "Not executed: the test case has no verifiable steps."

            duration_ms = int((time.time() - start_time) * 1000)

            if final_status == TestResultStatus.PASS:
                passed_details = [a.message for a in assertions if a.message]
                exact_result = f"Passed: {'; '.join(passed_details)}" if passed_details else "Observed expected behavior: all assertions satisfied."
            elif final_status == TestResultStatus.FAIL:
                failed_details = [a.message for a in assertions if not a.passed]
                exact_result = f"Failed: {'; '.join(failed_details)}" if failed_details else "Assertion failure observed during test execution."
            elif final_status == TestResultStatus.BLOCKED:
                exact_result = "Test execution blocked due to upstream authentication failure."
            else:
                exact_result = skip_reason or NOT_EXECUTED_REASON

            res = TestExecutionResultModel(
                test_id=tc.id,
                status=final_status,
                duration_ms=duration_ms,
                executed_at=executed_at,
                error_message=skip_reason or (
                    "; ".join(a.message for a in assertions if not a.passed) or None
                ),
                actual_result=exact_result,
                exact_result=exact_result,
                step_results=step_results,
                assertions=assertions,
                healing_events=[],
                screenshots=screenshots,
            )
            results.append(res)

        os.makedirs(self.results_dir, exist_ok=True)
        dump_data = [r.model_dump() for r in results]
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)

        return results
