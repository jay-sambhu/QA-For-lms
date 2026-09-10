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

def test_cors_vercel_preview_pattern_allowed(client):
    """Verify that dynamic preview deployments matching web-*.vercel.app receive CORS approval."""
    preview_origin = "https://web-preview-feature-jay-sambhus-projects.vercel.app"
    response = client.options(
        "/api/health",
        headers={
            "Origin": preview_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == preview_origin
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_untrusted_vercel_origin_rejected(client):
    """Verify that unrelated Vercel origins not belonging to this project are rejected."""
    untrusted_origin = "https://some-other-persons-app.vercel.app"
    response = client.options(
        "/api/health",
        headers={
            "Origin": untrusted_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") is None
