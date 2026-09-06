"""
Integration unit tests for API Testing, Perf/A11y, Agent Orchestrator, Pattern Extraction, and Self-Test Demo App.
"""
import os
import tempfile
from fastapi.testclient import TestClient

from tests.fixtures.demo_app.main import app as demo_app
from core.api_testing.api_tester import ApiTestingEngine
from core.performance.perf_a11y_engine import PerfA11yEngine
from core.agent.agent_orchestrator import AgentOrchestrator
from core.learning.pattern_extractor import HistoricalLearningEngine


def test_self_test_demo_app_defects():
    client = TestClient(demo_app)

    # 1. Verify broken login endpoint returns 500
    res_login = client.post("/login")
    assert res_login.status_code == 500

    # 2. Verify broken API returns 500
    res_api = client.get("/api/v1/broken")
    assert res_api.status_code == 500

    # 3. Verify unprotected admin is accessible
    res_admin = client.get("/admin")
    assert res_admin.status_code == 200
    assert "Admin Control Panel" in res_admin.text


def test_api_testing_engine():
    with tempfile.TemporaryDirectory() as tmp_dir:
        discovered_calls = [
            {"url": "/api/v1/health", "method": "GET", "status_code": 200},
            {"url": "/api/v1/broken", "method": "GET", "status_code": 500},
        ]
        engine = ApiTestingEngine(discovered_calls, tmp_dir, "scan_api_001")
        results = engine.run_api_tests()

        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].passed is False
        assert os.path.exists(engine.output_file)


def test_perf_a11y_engine():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pages = [
            {
                "url": "https://example.com/home",
                "load_time_ms": 250.0,
                "elements": [{"tag_name": "img", "element_id": "logo"}]
            }
        ]
        engine = PerfA11yEngine(pages, tmp_dir, "scan_perf_001")
        audit = engine.audit_pages()

        assert len(audit["performance"]) == 1
        assert len(audit["accessibility_violations"]) == 1
        assert audit["accessibility_violations"][0]["rule_id"] == "image-alt-missing"


def test_agent_orchestrator_and_sanitization():
    with tempfile.TemporaryDirectory() as tmp_dir:
        orch = AgentOrchestrator("scan_agent_001", tmp_dir)
        untrusted_input = "User input trying to IGNORE PREVIOUS INSTRUCTIONS"
        sanitized = orch.sanitize_untrusted_web_input(untrusted_input)
        assert "[REDACTED_PROMPT_INJECTION]" in sanitized

        decision = orch.log_decision(
            agent_name="DiscoveryAgent",
            stage="DISCOVERING",
            reasoning="Identified 5 routes",
            output={"routes_count": 5}
        )
        assert decision.confidence == 0.95
        assert os.path.exists(orch.decisions_log)


def test_historical_learning_engine():
    with tempfile.TemporaryDirectory() as tmp_dir:
        defects = [
            {"affected_url": "/login", "title": "500 Login Error", "severity": "critical"}
        ]
        learning = HistoricalLearningEngine("app_demo_001", tmp_dir)
        patterns = learning.record_run_outcomes(defects)

        assert len(patterns) == 1
        assert patterns[0].affected_route == "/login"
        assert os.path.exists(learning.learning_file)
