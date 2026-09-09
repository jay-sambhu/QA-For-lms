"""
Phase 27 — OAuth Security & Identity Integrity Test Suite

Verifies:
1. Production environment rejects dev test tokens.
2. Unauthenticated requests to protected endpoints return 401.
3. Multi-tenant context isolation (User A vs User B data boundaries).
4. Absence of fabricated OAuth session fallbacks in frontend code.
"""

import os
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_production_environment_rejects_dev_tokens(monkeypatch):
    """Verify that setting ENVIRONMENT=production blocks dev-token access."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    
    response = client.get(
        "/api/v1/scans",
        headers={"Authorization": "Bearer dev-token"}
    )
    
    assert response.status_code == 401
    assert "Development test tokens are rejected in production environment" in response.json()["detail"]


def test_unauthenticated_request_rejected():
    """Verify that unauthenticated requests without bearer tokens return 401."""
    response = client.get("/api/v1/scans")
    assert response.status_code == 401
    assert "Missing or invalid Authorization header" in response.json()["detail"]


def test_non_production_dev_token_allowed(monkeypatch):
    """Verify that development environment allows dev-token for local testing."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    
    response = client.get(
        "/api/v1/scans",
        headers={"Authorization": "Bearer dev-token"}
    )
    assert response.status_code == 200


def test_user_a_and_user_b_isolation(monkeypatch):
    """Verify that User A cannot access User B's scans in non-production dev mode."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    
    # User A creates a scan
    create_res = client.post(
        "/api/v1/scans",
        json={"url": "https://example.com", "max_pages": 1},
        headers={"Authorization": "Bearer dev-token"}
    )
    assert create_res.status_code in (200, 201, 202)
    scan_id = create_res.json().get("scan_id") or create_res.json().get("id")
    assert scan_id is not None

    # User B attempts to access User A's scan
    get_res = client.get(
        f"/api/v1/scans/{scan_id}",
        headers={"Authorization": "Bearer user-b-token"}
    )
    assert get_res.status_code in (403, 404)


def test_no_fabricated_oauth_fallback_in_source():
    """Verify that setCustomSession mock identity generator does not exist in frontend source."""
    auth_modal_path = os.path.join(os.path.dirname(__file__), "..", "web", "src", "components", "auth", "AuthModal.tsx")
    auth_context_path = os.path.join(os.path.dirname(__file__), "..", "web", "src", "context", "AuthContext.tsx")
    
    with open(auth_modal_path, "r", encoding="utf-8") as f:
        auth_modal_content = f.read()
        
    with open(auth_context_path, "r", encoding="utf-8") as f:
        auth_context_content = f.read()

    # Ensure setCustomSession was completely removed
    assert "setCustomSession" not in auth_modal_content
    assert "setCustomSession" not in auth_context_content
    assert "user@google.com" not in auth_modal_content
    assert "user@github.com" not in auth_modal_content
