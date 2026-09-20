from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from api.main import app, supabase

client = TestClient(app)

def _setup_admin_auth():
    mock_user = MagicMock()
    mock_user.user.id = "00000000-0000-0000-0000-000000000099"
    mock_user.user.email = "admin@example.com"
    mock_user.user.role = "admin"
    mock_user.user.user_metadata = {"role": "admin"}
    supabase.auth.get_user = MagicMock(return_value=mock_user)
    return {"Authorization": "Bearer mocked_admin_token"}

def test_admin_metrics_endpoint():
    headers = _setup_admin_auth()
    res = client.get("/api/v1/admin/metrics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "platform_overview" in data
    assert "financial_metrics" in data
    assert "gateway_distribution" in data
    assert "total_scans" in data["platform_overview"]
    assert "mrr_usd" in data["financial_metrics"]

def test_admin_users_endpoint():
    headers = _setup_admin_auth()
    res = client.get("/api/v1/admin/users", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "users" in data
    assert "total" in data

def test_admin_scans_endpoint():
    headers = _setup_admin_auth()
    res = client.get("/api/v1/admin/scans", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "scans" in data
    assert "total" in data

def test_admin_system_endpoint():
    headers = _setup_admin_auth()
    res = client.get("/api/v1/admin/system", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["cluster_health"] == "operational"
    assert "runtime" in data


def _setup_evil_user_auth():
    """Simulate attacker registering admin@evil.com with role='user'."""
    mock_user = MagicMock()
    mock_user.user.id = "00000000-0000-0000-0000-000000000666"
    mock_user.user.email = "admin@evil.com"
    mock_user.user.role = "user"
    mock_user.user.user_metadata = {"role": "user"}
    mock_user.user.app_metadata = {"role": "user"}
    supabase.auth.get_user = MagicMock(return_value=mock_user)
    return {"Authorization": "Bearer mocked_evil_user_token"}


def test_evil_admin_email_pattern_rejected_on_all_admin_routes():
    """
    Verify that an attacker with email admin@evil.com and role 'user'
    is rejected with 403 on every single /admin/* route.
    """
    headers = _setup_evil_user_auth()
    admin_routes = [
        ("GET", "/api/v1/admin/metrics", None),
        ("GET", "/api/v1/admin/users", None),
        ("GET", "/api/v1/admin/scans", None),
        ("GET", "/api/v1/admin/system", None),
        ("GET", "/api/v1/admin/ai-providers", None),
        ("POST", "/api/v1/admin/ai-providers", {"provider": "gemini", "api_key": "k"}),
        ("POST", "/api/v1/admin/ai-providers/test", {"provider": "gemini"}),
        ("GET", "/api/v1/admin/api-keys", None),
        ("POST", "/api/v1/admin/api-keys", {"name": "test"}),
        ("DELETE", "/api/v1/admin/api-keys/key-123", None),
    ]
    for method, path, json_data in admin_routes:
        if method == "GET":
            res = client.get(path, headers=headers)
        elif method == "POST":
            res = client.post(path, headers=headers, json=json_data)
        elif method == "DELETE":
            res = client.delete(path, headers=headers)
        assert res.status_code == 403, f"Expected 403 for {method} {path}, got {res.status_code}"
        assert "Admin access required" in res.json().get("detail", "")


def test_admin_emails_allowlist_exact_match(monkeypatch):
    """Verify that an exact email in ADMIN_EMAILS grants admin access even with role='user'."""
    monkeypatch.setenv("ADMIN_EMAILS", "trusted_admin@corp.com,ops@jasuss.tech")
    mock_user = MagicMock()
    mock_user.user.id = "00000000-0000-0000-0000-000000000777"
    mock_user.user.email = "trusted_admin@corp.com"
    mock_user.user.role = "user"
    mock_user.user.user_metadata = {"role": "user"}
    mock_user.user.app_metadata = {"role": "user"}
    supabase.auth.get_user = MagicMock(return_value=mock_user)
    headers = {"Authorization": "Bearer mocked_trusted_admin_token"}

    res = client.get("/api/v1/admin/metrics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "platform_overview" in data


def test_billing_plans_endpoint():
    res = client.get("/api/v1/billing/plans")
    assert res.status_code == 200
    data = res.json()
    assert len(data["plans"]) == 3
    assert len(data["supported_gateways"]) == 4

def test_billing_checkout_endpoint():
    res = client.post("/api/v1/billing/checkout", json={"plan_id": "pro", "gateway": "stripe"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "checkout_url" in data
