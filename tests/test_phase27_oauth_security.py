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


def test_production_environment_rejects_dev_tokens():
    """Verify that arbitrary unverified dev-tokens are rejected with 401."""
    from api.main import supabase
    from unittest.mock import MagicMock
    supabase.auth.get_user = MagicMock(side_effect=Exception("Invalid token"))

    response = client.get(
        "/api/v1/scans",
        headers={"Authorization": "Bearer dev-token"}
    )
    assert response.status_code == 401


def test_unauthenticated_request_rejected():
    """Verify that unauthenticated requests without bearer tokens return 401."""
    response = client.get("/api/v1/scans")
    assert response.status_code == 401
    assert "Missing or invalid Authorization header" in response.json()["detail"]


def test_non_production_dev_token_allowed():
    """Verify that authenticated requests with valid Supabase user are allowed."""
    from api.main import supabase
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.user.id = "00000000-0000-0000-0000-000000000001"
    mock_user.user.email = "dev@example.com"
    mock_user.user.role = "user"
    mock_user.user.user_metadata = {"role": "user"}
    supabase.auth.get_user = MagicMock(return_value=mock_user)

    response = client.get(
        "/api/v1/scans",
        headers={"Authorization": "Bearer valid_supabase_jwt"}
    )
    assert response.status_code == 200


def test_user_a_and_user_b_isolation():
    """Verify that User A cannot access User B's scans."""
    from api.main import supabase
    from unittest.mock import MagicMock, patch

    user_a = MagicMock()
    user_a.user.id = "00000000-0000-0000-0000-000000000001"
    user_a.user.email = "user_a@example.com"
    user_a.user.role = "user"
    user_a.user.user_metadata = {"role": "user"}

    user_b = MagicMock()
    user_b.user.id = "00000000-0000-0000-0000-000000000002"
    user_b.user.email = "user_b@example.com"
    user_b.user.role = "user"
    user_b.user.user_metadata = {"role": "user"}

    # User A creates a scan
    supabase.auth.get_user = MagicMock(return_value=user_a)
    with patch("worker.tasks.process_query_task.delay"):
        create_res = client.post(
            "/api/v1/scans",
            json={"url": "https://example.com", "max_pages": 1},
            headers={"Authorization": "Bearer token_user_a"}
        )
    assert create_res.status_code in (200, 201, 202)
    scan_id = create_res.json().get("scan_id") or create_res.json().get("id")
    assert scan_id is not None

    # User B attempts to access User A's scan
    supabase.auth.get_user = MagicMock(return_value=user_b)
    get_res = client.get(
        f"/api/v1/scans/{scan_id}",
        headers={"Authorization": "Bearer token_user_b"}
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
