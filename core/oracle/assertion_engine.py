"""
Autonomous Multi-Source Assertion Engine and Oracle Layer for JASUSS.
"""
from typing import Any, Dict, List, Optional
from core.schemas.execution_result import AssertionResultModel, TestResultStatus


class AssertionEngine:
    """Evaluates multi-source observable assertions against DOM, Network, and API states."""

    @staticmethod
    def assert_url(expected_url: str, actual_url: str) -> AssertionResultModel:
        passed = expected_url in actual_url or actual_url in expected_url
        return AssertionResultModel(
            assertion_type="url_match",
            expected=expected_url,
            actual=actual_url,
            passed=passed,
            message=f"URL match check: expected '{expected_url}', got '{actual_url}'",
        )

    @staticmethod
    def assert_status_code(expected_status: int, actual_status: int) -> AssertionResultModel:
        passed = (expected_status == actual_status)
        return AssertionResultModel(
            assertion_type="http_status",
            expected=expected_status,
            actual=actual_status,
            passed=passed,
            message=f"HTTP status code check: expected {expected_status}, got {actual_status}",
        )

    @staticmethod
    def assert_no_console_errors(console_logs: List[str]) -> AssertionResultModel:
        errors = [msg for msg in console_logs if "error" in msg.lower() or "exception" in msg.lower()]
        passed = len(errors) == 0
        return AssertionResultModel(
            assertion_type="no_console_errors",
            expected=0,
            actual=len(errors),
            passed=passed,
            message=f"Console error check: found {len(errors)} error(s)",
        )

    @staticmethod
    def determine_final_status(assertions: List[AssertionResultModel], has_healing_review: bool = False) -> TestResultStatus:
        if not assertions:
            return TestResultStatus.INCONCLUSIVE

        if any(not a.passed for a in assertions):
            return TestResultStatus.FAIL

        if has_healing_review:
            return TestResultStatus.NEEDS_REVIEW

        return TestResultStatus.PASS
