"""
Unit tests for Risk-Based Test Planner.
"""
import os
import tempfile
from core.planning.risk_planner import RiskPlannerEngine
from core.schemas.test_case import TestPriority


def test_risk_planner_engine():
    with tempfile.TemporaryDirectory() as tmp_dir:
        app_model = {
            "target_url": "https://example.com",
            "routes": {
                "/login": {"requires_auth": False, "forms_count": 1},
                "/checkout": {"requires_auth": True, "forms_count": 2},
                "/about": {"requires_auth": False, "forms_count": 0},
            }
        }
        planner = RiskPlannerEngine(app_model, tmp_dir, "scan_plan_001")
        plan = planner.generate_plan()

        assert plan.scan_id == "scan_plan_001"
        assert len(plan.suites) >= 1
        assert os.path.exists(planner.plan_path)

        p0_suite = next((s for s in plan.suites if s.priority == TestPriority.P0), None)
        assert p0_suite is not None
        assert "/checkout" in p0_suite.target_routes or "/login" in p0_suite.target_routes
