"""
Ground Truth Hidden Defect Registry for JASUSS Challenge Applications.
IMPORTANT: This module is strictly used by the evaluation scoring pipeline.
It is NEVER exposed to the JASUSS agent during scan execution.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class GroundTruthDefect:
    defect_id: str
    app_key: str
    category: str  # functional, ui, security, api, navigation, javascript, validation
    title: str
    target_url_pattern: str
    trigger_condition: str
    expected_status_code: int | None = None
    expected_error_substring: str | None = None
    severity: str = "high"


HIDDEN_DEFECT_REGISTRY: Dict[str, List[GroundTruthDefect]] = {
    "crud": [
        GroundTruthDefect(
            defect_id="CRUD-001",
            app_key="crud",
            category="functional",
            title="Delete on item 999 raises HTTP 500",
            target_url_pattern="/items/999/delete",
            trigger_condition="GET or click link /items/999/delete",
            expected_status_code=500,
            expected_error_substring="Database Constraint Failure",
            severity="high",
        ),
        GroundTruthDefect(
            defect_id="CRUD-002",
            app_key="crud",
            category="ui",
            title="Search page horizontal layout overflow",
            target_url_pattern="/items/search",
            trigger_condition="Navigate to search page",
            severity="medium",
        ),
        GroundTruthDefect(
            defect_id="CRUD-003",
            app_key="crud",
            category="validation",
            title="Item creation allows negative price input -100",
            target_url_pattern="/items/create",
            trigger_condition="POST /items/create with price=-100",
            severity="medium",
        ),
    ],
    "ecommerce": [
        GroundTruthDefect(
            defect_id="ECOM-001",
            app_key="ecommerce",
            category="api",
            title="Checkout with item 404 throws HTTP 500",
            target_url_pattern="/checkout",
            trigger_condition="POST /checkout with item 404 in cart",
            expected_status_code=500,
            severity="high",
        ),
        GroundTruthDefect(
            defect_id="ECOM-002",
            app_key="ecommerce",
            category="javascript",
            title="Cart quantity update uncaught TypeError",
            target_url_pattern="/cart",
            trigger_condition="Click update quantity button",
            expected_error_substring="Cannot read properties of null",
            severity="high",
        ),
        GroundTruthDefect(
            defect_id="ECOM-003",
            app_key="ecommerce",
            category="functional",
            title="Discount coupon OFF50 increases price instead of deducting 50%",
            target_url_pattern="/cart/discount",
            trigger_condition="Apply OFF50 coupon",
            severity="medium",
        ),
    ],
    "lms": [
        GroundTruthDefect(
            defect_id="LMS-001",
            app_key="lms",
            category="security",
            title="Unprotected instructor grade portal access",
            target_url_pattern="/instructor/grades",
            trigger_condition="Navigate to /instructor/grades without auth",
            severity="high",
        ),
        GroundTruthDefect(
            defect_id="LMS-002",
            app_key="lms",
            category="navigation",
            title="Lesson 3 link returns HTTP 404",
            target_url_pattern="/courses/1/lessons/3",
            trigger_condition="Click lesson 3 link",
            expected_status_code=404,
            severity="medium",
        ),
        GroundTruthDefect(
            defect_id="LMS-003",
            app_key="lms",
            category="api",
            title="Quiz submission with empty answer throws HTTP 500",
            target_url_pattern="/quiz/submit",
            trigger_condition="POST /quiz/submit with answer=''",
            expected_status_code=500,
            severity="high",
        ),
    ],
    "dashboard": [
        GroundTruthDefect(
            defect_id="DASH-001",
            app_key="dashboard",
            category="security",
            title="Privilege escalation via query string ?role=superadmin",
            target_url_pattern="/admin/users",
            trigger_condition="GET /admin/users?role=superadmin",
            severity="critical",
        ),
        GroundTruthDefect(
            defect_id="DASH-002",
            app_key="dashboard",
            category="javascript",
            title="Audit modal export button Uncaught ReferenceError",
            target_url_pattern="/admin/audit",
            trigger_condition="Click export modal button",
            expected_error_substring="exportAuditLogsModal is not defined",
            severity="high",
        ),
        GroundTruthDefect(
            defect_id="DASH-003",
            app_key="dashboard",
            category="api",
            title="System logs API with status=ALL_EXCEPT_SYSTEM throws 500",
            target_url_pattern="/api/v1/system-logs",
            trigger_condition="GET /api/v1/system-logs?status=ALL_EXCEPT_SYSTEM",
            expected_status_code=500,
            severity="high",
        ),
    ],
    "spa": [
        GroundTruthDefect(
            defect_id="SPA-001",
            app_key="spa",
            category="api",
            title="Async Feed API page=3 returns HTTP 500",
            target_url_pattern="/api/v1/feed",
            trigger_condition="Fetch /api/v1/feed?page=3",
            expected_status_code=500,
            severity="high",
        ),
        GroundTruthDefect(
            defect_id="SPA-002",
            app_key="spa",
            category="javascript",
            title="Lazy chunk load unhandled promise rejection",
            target_url_pattern="/",
            trigger_condition="Click Load Lazy Chunk button",
            expected_error_substring="ChunkLoadError",
            severity="high",
        ),
        GroundTruthDefect(
            defect_id="SPA-003",
            app_key="spa",
            category="ui",
            title="Settings view horizontal page overflow (+5000px)",
            target_url_pattern="/",
            trigger_condition="Switch to settings tab",
            severity="medium",
        ),
    ],
    "complex_forms": [
        GroundTruthDefect(
            defect_id="FORM-001",
            app_key="complex_forms",
            category="api",
            title="Step 2 submit with boundary age=100 returns HTTP 500",
            target_url_pattern="/submit/step2",
            trigger_condition="POST /submit/step2 with age=100",
            expected_status_code=500,
            severity="high",
        ),
        GroundTruthDefect(
            defect_id="FORM-002",
            app_key="complex_forms",
            category="validation",
            title="Step 1 allows invalid email format without validation",
            target_url_pattern="/",
            trigger_condition="Submit step 1 with text email",
            severity="medium",
        ),
        GroundTruthDefect(
            defect_id="FORM-003",
            app_key="complex_forms",
            category="javascript",
            title="State dropdown change event causes JS TypeError",
            target_url_pattern="/wizard/step2",
            trigger_condition="Change country dropdown",
            expected_error_substring="Cannot read properties of undefined",
            severity="high",
        ),
    ],
}


def get_ground_truth_defects(app_key: str) -> List[GroundTruthDefect]:
    return HIDDEN_DEFECT_REGISTRY.get(app_key, [])
