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
    assert "crawler_workers" in data

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
