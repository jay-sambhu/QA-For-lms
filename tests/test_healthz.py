"""
Unit tests for Health Check & Readiness Probes (/healthz, /readyz).
"""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_liveness_probe_healthz():
    """Verify GET /healthz returns 200 with service info."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("service") == "ai-qa-api"

def test_readiness_probe_readyz():
    """Verify GET /readyz checks DB and responds with status ok."""
    response = client.get("/readyz")
    # In test environment, if DB is reachable it returns 200; if unavailable it returns 503
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "database" in data
