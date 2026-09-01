import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_admin_metrics_endpoint():
    res = client.get("/api/v1/admin/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "platform_overview" in data
    assert "financial_metrics" in data
    assert "gateway_distribution" in data
    assert "total_scans" in data["platform_overview"]
    assert "mrr_usd" in data["financial_metrics"]

def test_admin_users_endpoint():
    res = client.get("/api/v1/admin/users")
    assert res.status_code == 200
    data = res.json()
    assert "users" in data
    assert "total" in data

def test_admin_scans_endpoint():
    res = client.get("/api/v1/admin/scans")
    assert res.status_code == 200
    data = res.json()
    assert "scans" in data
    assert "total" in data

def test_admin_system_endpoint():
    res = client.get("/api/v1/admin/system")
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
