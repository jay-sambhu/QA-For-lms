"""
Autonomous Multi-Category Test Case Generator (V2 Engine).
Generates detailed, observable test cases across Functional, Auth, Authorization, Form, Navigation, API, UI, Reliability, and Security categories.
"""
import json
import os
import time
from typing import Dict, List, Any

from core.schemas.test_case import TestCaseModel, TestCategory, TestPriority, TestStepModel


class AutonomousTestGenerator:
    __test__ = False

    def __init__(self, application_model: Dict[str, Any], test_plan: Dict[str, Any], results_dir: str, run_id: str):
        self.app_model = application_model
        self.test_plan = test_plan
        self.results_dir = results_dir
        self.run_id = run_id
        self.output_file = os.path.join(results_dir, f"test_cases_{run_id}.json")

    def generate_test_cases(self) -> List[TestCaseModel]:
        test_cases: List[TestCaseModel] = []
        routes = self.app_model.get("routes", {})
        counter = 1

        for route, info in routes.items():
            url = info.get("url", f"{self.app_model.get('target_url', '')}{route}")

            # 1. Functional Navigation Test
            tc_nav = TestCaseModel(
                id=f"TC-{counter:03d}",
                title=f"Verify Route Accessibility: {route}",
                objective=f"Ensure user can navigate to {route} and page loads correctly",
                category=TestCategory.NAVIGATION,
                priority=TestPriority.P1 if info.get("requires_auth") else TestPriority.P2,
                risk_score=0.6 if info.get("requires_auth") else 0.3,
                preconditions=["Browser initialized"],
                steps=[
                    TestStepModel(
                        step_index=1,
                        action="navigate",
                        value=url,
                        expected_result=f"Page loads with status 200 at {route}",
                    )
                ],
                expected_behavior=f"Route {route} loads without uncaught JavaScript exceptions",
                evidence_requirements=["screenshot", "console_logs", "network_har"],
                confidence=1.0,
            )
            test_cases.append(tc_nav)
            counter += 1

            # 2. Form Validation & Security Test (if form exists)
            if info.get("forms_count", 0) > 0:
                tc_form = TestCaseModel(
                    id=f"TC-{counter:03d}",
                    title=f"Form Validation & Special Character Test: {route}",
                    objective=f"Verify form handles invalid input and special characters safely on {route}",
                    category=TestCategory.FORM,
                    priority=TestPriority.P1,
                    risk_score=0.7,
                    preconditions=[f"Navigated to {route}"],
                    steps=[
                        TestStepModel(
                            step_index=1,
                            action="fill",
                            target_selector="input[type='text'], input[type='email']",
                            value="<script>alert('xss')</script>' OR '1'='1",
                            expected_result="Input accepted without script execution",
                        ),
                        TestStepModel(
                            step_index=2,
                            action="click",
                            target_selector="button[type='submit'], input[type='submit']",
                            expected_result="Form validates or displays user-friendly error message",
                        )
                    ],
                    expected_behavior="Form rejects malicious payloads cleanly with HTTP 400 or client-side validation error",
                    evidence_requirements=["screenshot", "console_logs"],
                    confidence=0.9,
                )
                test_cases.append(tc_form)
                counter += 1

            # 3. Authentication & Session Boundary Test
            if info.get("requires_auth"):
                tc_auth = TestCaseModel(
                    id=f"TC-{counter:03d}",
                    title=f"Unauthenticated Access Isolation: {route}",
                    objective=f"Ensure unauthenticated requests to protected route {route} are redirected to login",
                    category=TestCategory.AUTHORIZATION,
                    priority=TestPriority.P0,
                    risk_score=0.9,
                    preconditions=["Anonymous session state (no auth token)"],
                    steps=[
                        TestStepModel(
                            step_index=1,
                            action="navigate",
                            value=url,
                            expected_result="Redirected to /login or HTTP 401/403 returned",
                        )
                    ],
                    expected_behavior="Protected resource denies access to unauthenticated user",
                    evidence_requirements=["screenshot", "response_headers"],
                    confidence=1.0,
                )
                test_cases.append(tc_auth)
                counter += 1

        os.makedirs(self.results_dir, exist_ok=True)
        dump_data = [tc.model_dump() for tc in test_cases]
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)

        return test_cases
