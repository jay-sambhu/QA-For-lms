"""
Strongly typed Pydantic models for Test Cases and Test Execution.
"""
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class TestPriority(str, Enum):
    __test__ = False
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TestCategory(str, Enum):
    __test__ = False
    FUNCTIONAL = "functional"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    FORM = "form"
    NAVIGATION = "navigation"
    API = "api"
    UI = "ui"
    RELIABILITY = "reliability"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"


class TestStepModel(BaseModel):
    step_index: int
    action: str  # click, fill, navigate, wait, assert, etc.
    target_selector: Optional[str] = None
    fallback_selectors: List[str] = Field(default_factory=list)
    value: Optional[str] = None
    expected_result: str


class TestCaseModel(BaseModel):
    __test__ = False
    id: str
    title: str
    objective: str
    description: Optional[str] = None
    category: TestCategory = TestCategory.FUNCTIONAL
    priority: TestPriority = TestPriority.P2
    issue_level: str = "medium"  # critical, high, medium, low
    risk_score: float = 0.5
    preconditions: List[str] = Field(default_factory=list)
    steps: List[TestStepModel] = Field(default_factory=list)
    expected_behavior: str
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    exact_result: Optional[str] = None
    status: Optional[str] = None
    duration_ms: Optional[int] = 0
    source_page: Optional[str] = None
    evidence_requirements: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    cleanup_steps: List[str] = Field(default_factory=list)


def normalize_test_case_dict(tc: dict) -> dict:
    """
    Normalizes a test case dictionary to ensure it has valid issue_level,
    description, expected_result, actual_result, and exact_result fields.
    """
    if not isinstance(tc, dict):
        return tc

    # Priority & Issue level mapping
    issue_level = tc.get("issue_level")
    priority = str(tc.get("priority") or "P2").upper()
    if not issue_level:
        if priority in ("P0", "CRITICAL"):
            issue_level = "critical"
        elif priority in ("P1", "HIGH"):
            issue_level = "high"
        elif priority in ("P2", "MEDIUM"):
            issue_level = "medium"
        elif priority in ("P3", "LOW"):
            issue_level = "low"
        else:
            issue_level = "medium"
    else:
        issue_level = str(issue_level).lower()
        if issue_level not in ("critical", "high", "medium", "low"):
            issue_level = "medium"

    # Description
    description = tc.get("description") or tc.get("objective")
    title = tc.get("title") or "Automated Test Case"
    if not description:
        category = tc.get("category", "Functionality")
        description = f"Validate {str(category).lower()} scenario for '{title}' to verify interface stability and error boundaries."

    # Expected result
    expected_result = tc.get("expected_result") or tc.get("expected_behavior")
    if not expected_result:
        steps = tc.get("steps") or []
        for step in steps:
            if isinstance(step, dict) and step.get("expected_result"):
                expected_result = step.get("expected_result")
                break
    if not expected_result:
        expected_result = f"Expected '{title}' to complete successfully without errors or unexpected state."

    # Status
    status = (tc.get("status") or "skipped").lower()

    # Exact / Actual result
    exact_result = tc.get("exact_result") or tc.get("actual_result")
    if not exact_result:
        if status == "passed":
            exact_result = "Test executed successfully. All assertions passed, HTTP status valid, and no unhandled errors detected."
        elif status == "failed":
            exact_result = "Assertion failed or unexpected behavior encountered during test execution."
        elif status == "errored":
            exact_result = "Test execution terminated due to an uncaught exception or runtime failure."
        elif status == "blocked":
            exact_result = "Test execution blocked due to prerequisite failure (e.g. authentication failed)."
        else:
            exact_result = "Test case skipped or queued for automated execution."

    tc["issue_level"] = issue_level
    tc["description"] = description
    tc["expected_result"] = expected_result
    tc["actual_result"] = exact_result
    tc["exact_result"] = exact_result
    return tc

