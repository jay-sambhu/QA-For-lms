"""
Unit tests for JASUSS Pydantic Schemas.
"""
from core.schemas.discovery import DiscoveryResultModel, PageModel, ElementModel
from core.schemas.application_model import ApplicationKnowledgeModel, WorkflowModel
from core.schemas.test_case import TestCaseModel, TestCategory, TestPriority
from core.schemas.execution_result import TestExecutionResultModel, TestResultStatus
from core.schemas.defect import DefectModel, DefectSeverity
from core.schemas.quality import QualityGateResultModel, OverallQualityStatus


def test_discovery_schemas():
    elem = ElementModel(element_id="el_1", tag_name="button", text="Submit")
    page = PageModel(page_id="p_1", url="https://example.com/login", route="/login", elements=[elem])
    res = DiscoveryResultModel(scan_id="s_1", target_url="https://example.com", start_time="2026-09-06T10:00:00Z", pages=[page])
    assert res.pages[0].elements[0].text == "Submit"


def test_test_case_schemas():
    tc = TestCaseModel(
        id="TC-001",
        title="Valid Login Test",
        objective="Verify login with valid credentials",
        category=TestCategory.AUTHENTICATION,
        priority=TestPriority.P0,
        expected_behavior="User redirected to dashboard"
    )
    assert tc.category == TestCategory.AUTHENTICATION
    assert tc.priority == TestPriority.P0


def test_quality_gate_schemas():
    qg = QualityGateResultModel(
        overall_status=OverallQualityStatus.PASS,
        health_score=95,
        grade="A",
        is_deployable=True
    )
    assert qg.is_deployable is True
