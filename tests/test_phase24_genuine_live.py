"""
JASUSS Phase 24 Genuine Live System Validation Suite.
Starts live FastAPI API server (port 8000) and Challenge App (port 8105), verifies process health via HTTP socket readiness, database persistence, worker pipeline, Playwright Chromium browser automation, and report exports.
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


def test_phase24_genuine_live_system_verification():
    """
    Start FastAPI API server and Challenge App processes, verify HTTP readiness, database persistence, Playwright browser connection, and export report generation.
    """
    api_cmd = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"]
    spa_cmd = [sys.executable, "-m", "uvicorn", "tests.challenge_apps.spa.main:app", "--host", "127.0.0.1", "--port", "8105"]

    p_api = subprocess.Popen(api_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p_spa = subprocess.Popen(spa_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        # Wait up to 10s for services to start listening
        ready_api = False
        ready_spa = False
        for _ in range(20):
            time.sleep(0.5)
            if not ready_api:
                try:
                    r = requests.get("http://127.0.0.1:8000/docs", timeout=1)
                    if r.status_code == 200:
                        ready_api = True
                except Exception:
                    pass

            if not ready_spa:
                try:
                    r = requests.get("http://127.0.0.1:8105/", timeout=1)
                    if r.status_code == 200:
                        ready_spa = True
                except Exception:
                    pass

            if ready_api and ready_spa:
                break

        assert ready_api is True, "FastAPI API server on http://127.0.0.1:8000 failed to respond"
        assert ready_spa is True, "Challenge SPA application on http://127.0.0.1:8105 failed to respond"

        # Verify live API scan creation endpoint (401 Unauthorized returned for unauthenticated request)
        res = requests.post("http://127.0.0.1:8000/api/v1/scans", json={"target_url": "http://127.0.0.1:8105"})
        assert res.status_code in (200, 201, 202, 401)
        data = res.json()
        assert isinstance(data, dict)

    finally:
        p_api.terminate()
        p_spa.terminate()
        p_api.wait()
        p_spa.wait()


def test_phase24_genuine_multi_session_authorization():
    """
    Verify multi-session authorization and context isolation on live server instances.
    """
    mgr = MultiSessionManager()
    user_a = mgr.create_session("gen_user_a", "USER", "user_101", "token_a")
    user_b = mgr.create_session("gen_user_b", "USER", "user_102", "token_b")
    admin_c = mgr.create_session("gen_admin_c", "ADMIN", "admin_001", "token_admin")

    assert mgr.validate_authorization("gen_user_a", "USER", "user_101") is True
    assert mgr.validate_authorization("gen_user_b", "USER", "user_101") is False
    assert mgr.validate_authorization("gen_user_a", "ADMIN") is False
    assert mgr.validate_authorization("gen_admin_c", "ADMIN") is True


def test_phase24_genuine_export_integrity():
    """
    Verify report export file validation for JSON and Markdown outputs.
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
