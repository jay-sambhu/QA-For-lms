"""
Autonomous Risk-Based Test Planner for JASUSS.
Evaluates application knowledge graph and discovery findings to prioritize high-risk test execution.
"""
import json
import os
import time
from typing import Dict, List, Any
from pydantic import BaseModel, Field

from core.schemas.test_case import TestPriority, TestCategory


class PlannedTestSuiteModel(BaseModel):
    priority: TestPriority
    title: str
    target_routes: List[str]
    categories: List[TestCategory]
    risk_weight: float


class TestPlanModel(BaseModel):
    scan_id: str
    target_url: str
    generated_at: str
    suites: List[PlannedTestSuiteModel] = Field(default_factory=list)
    total_estimated_tests: int = 0


class RiskPlannerEngine:
    def __init__(self, application_model: Dict[str, Any], results_dir: str, run_id: str):
        self.app_model = application_model
        self.results_dir = results_dir
        self.run_id = run_id
        self.plan_path = os.path.join(results_dir, f"test_plan_{run_id}.json")

    def calculate_route_risk(self, route: str, route_info: Dict[str, Any]) -> float:
        """Calculates risk score (0.0 to 1.0) for a given route."""
        risk = 0.3  # baseline

        route_lower = route.lower()
        if any(term in route_lower for term in ["auth", "login", "pay", "checkout", "billing"]):
            risk += 0.5
        elif any(term in route_lower for term in ["admin", "settings", "user", "profile"]):
            risk += 0.3

        if route_info.get("requires_auth", False):
            risk += 0.1

        if route_info.get("forms_count", 0) > 0:
            risk += 0.1

        return min(1.0, risk)

    def generate_plan(self) -> TestPlanModel:
        routes = self.app_model.get("routes", {})
        p0_routes = []
        p1_routes = []
        p2_routes = []
        p3_routes = []

        for route, info in routes.items():
            score = self.calculate_route_risk(route, info)
            if score >= 0.8:
                p0_routes.append(route)
            elif score >= 0.5:
                p1_routes.append(route)
            elif score >= 0.3:
                p2_routes.append(route)
            else:
                p3_routes.append(route)

        suites = []
        if p0_routes:
            suites.append(
                PlannedTestSuiteModel(
                    priority=TestPriority.P0,
                    title="P0: Critical Authentication & Financial Workflows",
                    target_routes=p0_routes,
                    categories=[TestCategory.AUTHENTICATION, TestCategory.SECURITY, TestCategory.FUNCTIONAL],
                    risk_weight=0.9,
                )
            )

        if p1_routes:
            suites.append(
                PlannedTestSuiteModel(
                    priority=TestPriority.P1,
                    title="P1: Core Business Workflows & Data Mutation",
                    target_routes=p1_routes,
                    categories=[TestCategory.FUNCTIONAL, TestCategory.FORM, TestCategory.API],
                    risk_weight=0.7,
                )
            )

        if p2_routes or not suites:
            suites.append(
                PlannedTestSuiteModel(
                    priority=TestPriority.P2,
                    title="P2: Standard Navigation & UI Controls",
                    target_routes=p2_routes or list(routes.keys())[:5],
                    categories=[TestCategory.NAVIGATION, TestCategory.UI],
                    risk_weight=0.4,
                )
            )

        plan = TestPlanModel(
            scan_id=self.run_id,
            target_url=self.app_model.get("target_url", ""),
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            suites=suites,
            total_estimated_tests=len(suites) * 5,
        )

        os.makedirs(self.results_dir, exist_ok=True)
        with open(self.plan_path, "w", encoding="utf-8") as f:
            json.dump(plan.model_dump(), f, indent=2)

        return plan
