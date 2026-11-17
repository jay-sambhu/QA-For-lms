import pytest
from core.schemas.test_case import TestCaseModel, TestCategory, TestPriority, normalize_test_case_dict
from core.schemas.execution_result import TestExecutionResultModel, TestResultStatus


def test_test_case_model_fields():
    tc = TestCaseModel(
        id="TC-001",
        title="Check Form Validation",
        objective="Validate form fields",
        description="Verify boundary values for username input.",
        category=TestCategory.FORM,
        priority=TestPriority.P1,
        issue_level="high",
        expected_behavior="Validation error displayed",
        expected_result="Proper error text rendered when field is empty",
        actual_result="Validation error displayed as expected",
        exact_result="Validation error displayed as expected. HTTP 200 OK.",
        status="passed",
        duration_ms=450,
        source_page="https://example.com/login"
    )
    assert tc.issue_level == "high"
    assert tc.description == "Verify boundary values for username input."
    assert tc.expected_result == "Proper error text rendered when field is empty"
    assert tc.exact_result == "Validation error displayed as expected. HTTP 200 OK."


def test_normalize_test_case_dict_legacy():
    legacy_tc = {
        "id": "TC-NAV-001",
        "title": "Header Navigation",
        "category": "Navigation",
        "priority": "P0",
        "status": "passed",
        "steps": [
            {
                "step_index": 1,
                "action": "navigate",
                "value": "https://example.com/about",
                "expected_result": "Page loaded cleanly."
            }
        ]
    }
    normalized = normalize_test_case_dict(legacy_tc)
    assert normalized["issue_level"] == "critical"
    assert "Header Navigation" in normalized["description"]
    assert normalized["expected_result"] == "Page loaded cleanly."
    assert "successfully" in normalized["exact_result"]


def test_normalize_test_case_dict_levels():
    p1 = normalize_test_case_dict({"id": "TC-1", "priority": "P1", "status": "failed"})
    assert p1["issue_level"] == "high"
    assert "Assertion failed" in p1["exact_result"]

    p2 = normalize_test_case_dict({"id": "TC-2", "priority": "P2", "status": "errored"})
    assert p2["issue_level"] == "medium"
    assert "exception" in p2["exact_result"]

    p3 = normalize_test_case_dict({"id": "TC-3", "priority": "P3", "status": "skipped"})
    assert p3["issue_level"] == "low"
    assert "skipped" in p3["exact_result"]


def test_execution_result_model_fields():
    res = TestExecutionResultModel(
        test_id="TC-001",
        status=TestResultStatus.PASS,
        executed_at="2026-11-17T09:00:00Z",
        duration_ms=120,
        actual_result="Executed cleanly",
        exact_result="All assertions passed without unhandled errors"
    )
    assert res.actual_result == "Executed cleanly"
    assert res.exact_result == "All assertions passed without unhandled errors"
