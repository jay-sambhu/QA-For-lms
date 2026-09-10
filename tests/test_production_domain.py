import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_cors_jasuss_tech_origin_allowed(client):
    """Verify that requests with Origin: https://jasuss.tech receive CORS approval."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://jasuss.tech",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://jasuss.tech"
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_www_jasuss_tech_origin_allowed(client):
    """Verify that requests with Origin: https://www.jasuss.tech receive CORS approval."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://www.jasuss.tech",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://www.jasuss.tech"
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_untrusted_origin_disallowed(client):
    """Verify that untrusted origins do not receive an allow header."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://malicious-site.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI CORS middleware returns 400 or omits access-control-allow-origin for unauthorized origins
    assert response.headers.get("access-control-allow-origin") is None

def test_cors_vercel_origin_allowed(client):
    """Verify that requests from deployed Vercel apps receive CORS approval."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://web-two-flame-39.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://web-two-flame-39.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"
