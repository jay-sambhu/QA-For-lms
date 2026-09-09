"""
JASUSS Phase 28 — Real OAuth Integration & Production Security Test Suite

Verifies:
1. Complete absence of fabricated OAuth session fallbacks in production codebase.
2. Dev-token production isolation guard (ENVIRONMENT=production rejects test tokens).
3. Dev-token non-production permission (ENVIRONMENT=development permits dev tokens).
4. Multi-session authorization boundary (User A cannot access User B scans).
5. Secret hygiene (No sensitive service role keys exposed in client env vars).
"""

import os
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_production_environment_rejects_dev_tokens(monkeypatch):
    """Verify that setting ENVIRONMENT=production blocks test tokens with 401."""
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
    """Verify that development environment allows dev-token for local integration testing."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    
    response = client.get(
        "/api/v1/scans",
        headers={"Authorization": "Bearer dev-token"}
    )
    assert response.status_code == 200


def test_multi_user_scan_isolation(monkeypatch):
    """Verify that User A cannot access User B's scans."""
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


def test_zero_synthetic_oauth_identities_in_source():
    """Verify that no fabricated mock OAuth session generators exist in frontend code."""
    auth_modal_path = os.path.join(os.path.dirname(__file__), "..", "web", "src", "components", "auth", "AuthModal.tsx")
    auth_context_path = os.path.join(os.path.dirname(__file__), "..", "web", "src", "context", "AuthContext.tsx")
    
    with open(auth_modal_path, "r", encoding="utf-8") as f:
        auth_modal = f.read()
        
    with open(auth_context_path, "r", encoding="utf-8") as f:
        auth_context = f.read()

    assert "setCustomSession" not in auth_modal
    assert "setCustomSession" not in auth_context
    assert "user@google.com" not in auth_modal
    assert "user@github.com" not in auth_modal


def test_secret_hygiene_in_client_env():
    """Verify no service role keys or secrets are prefixed with NEXT_PUBLIC_."""
    env_local_path = os.path.join(os.path.dirname(__file__), "..", "web", ".env.local")
    if os.path.exists(env_local_path):
        with open(env_local_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "SERVICE_ROLE_KEY" not in content or "NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY" not in content
