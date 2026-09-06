"""
Unit tests for Autonomous Test Generator, Assertion Engine, and Self-Healing Executor.
"""
import asyncio
import json
import os
import tempfile
from core.test_generator_v2 import AutonomousTestGenerator
from core.oracle.assertion_engine import AssertionEngine
from core.executor_v2 import SelfHealingExecutor
from core.schemas.execution_result import TestResultStatus


def test_autonomous_test_generator():
    with tempfile.TemporaryDirectory() as tmp_dir:
        app_model = {
            "target_url": "https://example.com",
            "routes": {
                "/login": {"requires_auth": False, "forms_count": 1},
                "/dashboard": {"requires_auth": True, "forms_count": 0},
            }
        }
        test_plan = {"suites": []}
        gen = AutonomousTestGenerator(app_model, test_plan, tmp_dir, "scan_gen_001")
        test_cases = gen.generate_test_cases()

        assert len(test_cases) >= 3
        assert os.path.exists(gen.output_file)


def test_assertion_engine():
    url_res = AssertionEngine.assert_url("https://example.com/dashboard", "https://example.com/dashboard")
    assert url_res.passed is True

    status_res = AssertionEngine.assert_status_code(200, 500)
    assert status_res.passed is False

    final_status = AssertionEngine.determine_final_status([url_res, status_res])
    assert final_status == TestResultStatus.FAIL


def test_self_healing_executor():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tc_path = os.path.join(tmp_dir, "test_cases.json")
        sample_cases = [
            {
                "id": "TC-001",
                "title": "Sample Navigation",
                "objective": "Verify nav",
                "category": "navigation",
                "priority": "P2",
                "risk_score": 0.5,
                "preconditions": [],
                "steps": [
                    {
                        "step_index": 1,
                        "action": "navigate",
                        "target_selector": None,
                        "value": "https://example.com",
                        "expected_result": "Page loads"
                    }
                ],
                "expected_behavior": "Pass",
                "evidence_requirements": [],
                "confidence": 1.0,
                "cleanup_steps": []
            }
        ]
        with open(tc_path, "w", encoding="utf-8") as f:
            json.dump(sample_cases, f)

        executor = SelfHealingExecutor(tc_path, tmp_dir, "scan_exec_001")
        results = asyncio.run(executor.execute_suite())

        assert len(results) == 1
        assert results[0].status == TestResultStatus.PASS
        assert os.path.exists(executor.output_file)
