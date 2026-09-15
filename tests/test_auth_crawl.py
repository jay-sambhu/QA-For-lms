import os
import json
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pydantic import ValidationError

from api.main import ScanRequest, ScanAuthPayload, app
from models import Scan, Base
from db import SessionLocal, engine
from crawler.crawler import WebsiteCrawler
from qa_report_generator import QAReportGenerator


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield


@patch.dict(os.environ, {"ALLOW_LOCAL_TARGETS": "false"})
def test_auth_payload_ssrf_and_secret_redaction():
    # Valid login payload
    valid_req = ScanRequest(
        url="https://example.com",
        auth=ScanAuthPayload(
            login_url="https://example.com/login",
            username="admin@example.com",
            password="SuperSecretPassword123!",
        ),
    )
    assert valid_req.auth is not None
    assert valid_req.auth.login_url == "https://example.com/login"
    assert valid_req.auth.username == "admin@example.com"
    # Password must not expose plaintext in repr or str
    assert "SuperSecretPassword123!" not in str(valid_req.auth)
    assert "SuperSecretPassword123!" not in repr(valid_req.auth)
    assert valid_req.auth.password.get_secret_value() == "SuperSecretPassword123!"

    # SSRF: loopback
    with pytest.raises(ValidationError):
        ScanRequest(
            url="https://example.com",
            auth=ScanAuthPayload(login_url="http://127.0.0.1/login"),
        )

    # SSRF: cloud metadata
    with pytest.raises(ValidationError):
        ScanRequest(
            url="https://example.com",
            auth=ScanAuthPayload(login_url="http://169.254.169.254/latest/meta-data"),
        )

    # SSRF: localhost
    with pytest.raises(ValidationError):
        ScanRequest(
            url="https://example.com",
            auth=ScanAuthPayload(login_url="http://localhost:8000/login"),
        )


def test_create_scan_authenticated_persists_is_authenticated_flag_no_password_stored():
    from fastapi.testclient import TestClient
    from api.main import supabase
    client = TestClient(app)

    mock_user = MagicMock()
    mock_user.user.id = "00000000-0000-0000-0000-000000000001"
    mock_user.user.email = "tester@example.com"
    mock_user.user.role = "user"
    mock_user.user.user_metadata = {"role": "user"}
    supabase.auth.get_user = MagicMock(return_value=mock_user)

    with patch("api.main.process_query_task.apply_async") as mock_celery:
        response = client.post(
            "/api/v1/scans",
            json={
                "url": "https://example.com",
                "max_pages": 5,
                "auth": {
                    "login_url": "https://example.com/login",
                    "username": "tester@example.com",
                    "password": "PasswordSecret999",
                },
            },
            headers={"Authorization": "Bearer mocked_user_token"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        scan_id = data["scan_id"]
        assert data["is_authenticated"] is True
        assert "password" not in response.text
        assert "PasswordSecret999" not in response.text

        # Verify in SQLite database
        with SessionLocal() as db:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            assert scan is not None
            assert scan.is_authenticated is True
            # Database model contains no password column
            assert not hasattr(scan, "password")

        # Verify Celery task received the transient arguments
        mock_celery.assert_called_once()
        kwargs = mock_celery.call_args[1]
        args = kwargs.get("args", mock_celery.call_args[0])
        assert args[0] == scan_id  # scan_id
        assert args[2] == "https://example.com"  # url
        assert args[5] == "https://example.com/login"  # login_url
        assert args[6] == "tester@example.com"  # username
        assert args[7] == "PasswordSecret999"  # password_raw transiently passed to worker


def test_crawler_perform_login_success():
    async def _test():
        crawler = WebsiteCrawler(
            "https://example.com",
            login_url="https://example.com/login",
            username="user@example.com",
            password="MySecretPassword",
        )

        mock_page = MagicMock()
        mock_page.url = "https://example.com/dashboard"
        mock_res = MagicMock()
        mock_res.status = 200
        mock_page.goto = AsyncMock(return_value=mock_res)
        mock_page.wait_for_timeout = AsyncMock()

        mock_username_input = MagicMock()
        mock_username_input.is_visible = AsyncMock(return_value=True)
        mock_username_input.fill = AsyncMock()

        mock_password_input = MagicMock()
        mock_password_input.is_visible = AsyncMock(return_value=True)
        mock_password_input.fill = AsyncMock()

        mock_submit_btn = MagicMock()
        mock_submit_btn.is_visible = AsyncMock(return_value=True)
        mock_submit_btn.click = AsyncMock()

        async def fake_query_selector(selector):
            if "class*='error'" in selector or "alert" in selector or "Invalid" in selector:
                return None
            if "type='email'" in selector or "name='username'" in selector:
                return mock_username_input
            if "type='password'" in selector:
                return mock_password_input
            if "type='submit'" in selector or "Sign In" in selector:
                return mock_submit_btn
            return None

        mock_page.query_selector = AsyncMock(side_effect=fake_query_selector)

        res = await crawler.perform_login(mock_page, "desktop")
        assert res["success"] is True
        assert res["status"] == "passed"
        mock_username_input.fill.assert_called_once_with("user@example.com")
        mock_password_input.fill.assert_called_once_with("MySecretPassword")
        mock_submit_btn.click.assert_called_once()

    asyncio.run(_test())


def test_crawler_perform_login_failure():
    async def _test():
        crawler = WebsiteCrawler(
            "https://example.com",
            login_url="https://example.com/login",
            username="wronguser@example.com",
            password="WrongPassword",
        )

        mock_page = MagicMock()
        mock_page.url = "https://example.com/login"
        mock_res = MagicMock()
        mock_res.status = 401
        mock_page.goto = AsyncMock(return_value=mock_res)
        mock_page.wait_for_timeout = AsyncMock()

        mock_err_el = MagicMock()
        mock_err_el.is_visible = AsyncMock(return_value=True)

        async def fake_query_selector(selector):
            if "class*='error'" in selector or "alert" in selector or "Invalid" in selector:
                return mock_err_el
            return None

        mock_page.query_selector = AsyncMock(side_effect=fake_query_selector)

        res = await crawler.perform_login(mock_page, "desktop")
        assert res["success"] is False
        assert res["status"] == "errored"

    asyncio.run(_test())


def test_report_generator_handles_auth_errored_and_blocks_downstream(tmp_path):
    # Simulated crawl file with auth error
    crawl_data = {
        "target": "https://example.com",
        "run_id": "test_auth_run",
        "pages_crawled": 1,
        "pages_attempted": 1,
        "pages": [{"url": "https://example.com/login", "status": 401}],
        "http_errors": [],
        "network_failures": [],
        "console_errors": [],
        "auth_test_cases": [
            {
                "id": "TC-AUTH-001",
                "title": "Website Authentication & Session Initialization",
                "category": "Authentication",
                "priority": "P0",
                "status": "errored",
                "duration_ms": 1200,
                "source_page": "https://example.com/login",
                "expected_result": "User authenticated successfully.",
                "actual_result": "Invalid credentials or login rejected by server",
            }
        ],
        "auth_findings": [
            {
                "id": "AUTH-FAIL-001",
                "severity": "high",
                "priority": "P1",
                "classification": "confirmed_bug",
                "title": "Authentication Failed on Login Page",
                "page": "https://example.com/login",
                "description": "Automated login failed with provided credentials.",
            }
        ],
    }
    crawl_file = tmp_path / "crawl_test_auth_run.json"
    with open(crawl_file, "w", encoding="utf-8") as f:
        json.dump(crawl_data, f)

    # Simulated downstream test cases
    test_cases_file = tmp_path / "test_cases.json"
    with open(test_cases_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test_cases": [
                    {
                        "id": "TC-DASH-001",
                        "title": "Access Protected Dashboard",
                        "category": "Dashboard",
                        "status": "unexecuted",
                    }
                ]
            },
            f,
        )

    raw_data = {
        "metadata": {"target_url": "https://example.com", "run_id": "test_auth_run"},
        "source": {"crawl_result": str(crawl_file)},
        "findings": [],
    }

    generator = QAReportGenerator(results_dir=str(tmp_path), base_dir=str(tmp_path))
    generator.test_cases_file = str(test_cases_file)
    final_report = generator.generate_json_report(str(crawl_file), raw_data)

    metrics = final_report["qa_metrics"]
    assert metrics["test_cases"]["total"] == 2
    assert metrics["test_cases"]["errored"] == 1  # TC-AUTH-001
    assert metrics["test_cases"]["blocked"] == 1  # TC-DASH-001 downstream
    assert metrics["test_cases"]["passed"] == 0

    findings = final_report["findings"]
    assert len(findings) == 1
    assert findings[0]["title"] == "Authentication Failed on Login Page"


class _StubAuthServerHandler:
    """Ephemeral HTTP handler simulating an authentication flow for Playwright crawler."""
    @staticmethod
    def create_handler():
        import urllib.parse
        from http.server import BaseHTTPRequestHandler

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress server logging during tests

            def do_GET(self):
                if self.path == "/login":
                    html = """<!DOCTYPE html>
<html>
<head><title>Login Page</title></head>
<body>
    <h2>Sign In</h2>
    <form method="POST" action="/login">
        <input type="email" name="email" id="email" placeholder="Email address" />
        <input type="password" name="password" id="password" placeholder="Password" />
        <button type="submit" id="submit-btn">Sign In</button>
    </form>
</body>
</html>"""
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))
                elif self.path == "/dashboard":
                    html = """<!DOCTYPE html>
<html>
<head><title>Dashboard</title></head>
<body>
    <h1>Protected Dashboard</h1>
    <p>Session initialized successfully</p>
</body>
</html>"""
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == "/login":
                    content_len = int(self.headers.get("Content-Length", 0))
                    post_body = self.rfile.read(content_len).decode("utf-8")
                    params = urllib.parse.parse_qs(post_body)
                    email = params.get("email", [""])[0]
                    password = params.get("password", [""])[0]

                    if email == "crawler_user@example.com" and password == "SecretPass123!":
                        self.send_response(302)
                        self.send_header("Location", "/dashboard")
                        self.end_headers()
                    else:
                        html = """<!DOCTYPE html>
<html>
<head><title>Login Failed</title></head>
<body>
    <div class="alert error" role="alert">Invalid credentials</div>
    <form method="POST" action="/login">
        <input type="email" name="email" id="email" />
        <input type="password" name="password" id="password" />
        <button type="submit">Sign In</button>
    </form>
</body>
</html>"""
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html")
                        self.end_headers()
                        self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

        return Handler


def test_playwright_crawler_hits_local_stub_login_success():
    """Verify Playwright crawler against a real local HTTP auth server with valid credentials."""
    import threading
    from http.server import HTTPServer
    from playwright.async_api import async_playwright

    server = HTTPServer(("127.0.0.1", 0), _StubAuthServerHandler.create_handler())
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def _run():
        login_url = f"http://127.0.0.1:{port}/login"
        crawler = WebsiteCrawler(
            f"http://127.0.0.1:{port}",
            login_url=login_url,
            username="crawler_user@example.com",
            password="SecretPass123!",
        )
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            try:
                res = await crawler.perform_login(page, "desktop")
                assert res["success"] is True
                assert res["status"] == "passed"
                assert "/dashboard" in page.url
            finally:
                await context.close()
                await browser.close()

    try:
        asyncio.run(_run())
    finally:
        server.shutdown()
        server.server_close()


def test_playwright_crawler_hits_local_stub_login_failure():
    """Verify Playwright crawler against a real local HTTP auth server with invalid credentials."""
    import threading
    from http.server import HTTPServer
    from playwright.async_api import async_playwright

    server = HTTPServer(("127.0.0.1", 0), _StubAuthServerHandler.create_handler())
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def _run():
        login_url = f"http://127.0.0.1:{port}/login"
        crawler = WebsiteCrawler(
            f"http://127.0.0.1:{port}",
            login_url=login_url,
            username="wrong_user@example.com",
            password="InvalidPassword123!",
        )
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            try:
                res = await crawler.perform_login(page, "desktop")
                assert res["success"] is False
                assert res["status"] == "errored"
                assert "Invalid credentials" in res.get("error", "")
            finally:
                await context.close()
                await browser.close()

    try:
        asyncio.run(_run())
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.live_auth
def test_live_supabase_auth_connection():
    """
    Legitimate live Supabase test requiring real network authentication credentials.
    Excluded from default CI/test runs via -m 'not live_auth'.
    """
    import os
    from supabase import create_client
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        pytest.skip("Live Supabase credentials not configured in environment")
    sb = create_client(url, key)
    assert sb is not None
