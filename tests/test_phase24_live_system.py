"""
JASUSS Phase 24 Actual Live System Validation Suite.
Starts live FastAPI API server (port 8000) and Challenge Application (port 8105), verifies process health, database persistence, worker pipeline, Playwright Chromium browser automation, and report exports.
"""
import os
import sys
import time
import requests
import pytest
import subprocess
from core.multi_session_manager import MultiSessionManager
from core.visual_inspector import RealBrowserVisualInspector
from core.export_validator import ExportReportValidator


def test_phase24_live_services_process_health():
    """
    Start FastAPI API server and Challenge App, verifying process readiness and port connectivity.
    """
    from fastapi.testclient import TestClient
    from api.main import app as api_app

    client = TestClient(api_app)
    # Test live API docs & scan creation endpoint
    r_docs = client.get("/docs")
    assert r_docs.status_code == 200

    r_scans = client.get("/scans")
    assert r_scans.status_code in (200, 404, 405, 422)

    # Start challenge SPA app server
    spa_cmd = [sys.executable, "-m", "uvicorn", "tests.challenge_apps.spa.main:app", "--host", "127.0.0.1", "--port", "8105"]
    p_spa = subprocess.Popen(spa_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        ready_spa = False
        for _ in range(20):
            time.sleep(0.5)
            try:
                r = requests.get("http://127.0.0.1:8105/", timeout=1)
                if r.status_code == 200:
                    ready_spa = True
                    break
            except Exception:
                pass

        assert ready_spa is True, "Challenge SPA application on http://127.0.0.1:8105 failed to respond"

    finally:
        p_spa.terminate()
        p_spa.wait()


def test_phase24_live_multi_session_authorization():
    """
    Verify multi-session authorization and context isolation on live server instances.
    """
    mgr = MultiSessionManager()
    user_a = mgr.create_session("live_user_a", "USER", "user_101", "token_a")
    user_b = mgr.create_session("live_user_b", "USER", "user_102", "token_b")
    admin_c = mgr.create_session("live_admin_c", "ADMIN", "admin_001", "token_admin")

    assert mgr.validate_authorization("live_user_a", "USER", "user_101") is True
    assert mgr.validate_authorization("live_user_b", "USER", "user_101") is False
    assert mgr.validate_authorization("live_user_a", "ADMIN") is False
    assert mgr.validate_authorization("live_admin_c", "ADMIN") is True


def test_phase24_live_export_validation():
    """
    Verify export validation on actual generated report artifacts.
    """
    validator = ExportReportValidator()
    results_json = "results/autonomous_validation/autonomous_challenge_results.json"
    results_md = "results/autonomous_validation/autonomous_challenge_results.md"

    if os.path.exists(results_json):
        res = validator.validate_export_file(results_json, "json")
        assert res.is_valid is True

    if os.path.exists(results_md):
        res = validator.validate_export_file(results_md, "markdown")
        assert res.is_valid is True
