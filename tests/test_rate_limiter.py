"""
Tests for rate limiting on scan creation endpoints.
"""
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app, supabase
import api.rate_limiter as rl

client = TestClient(app)

def test_rate_limiter_triggers_429_on_rapid_requests():
    """Verify that rapid requests to /api/v1/scans trigger HTTP 429."""
    mock_user = MagicMock()
    mock_user.user.id = "test-rate-limit-user-id"
    mock_user.user.email = "rl-test@example.com"
    mock_user.user.role = "student"
    supabase.auth.get_user = MagicMock(return_value=mock_user)

    # Temporarily set standard limit to 2 for test
    orig_limit = rl.STANDARD_LIMIT
    rl.STANDARD_LIMIT = 2
    rl._memory_store.clear()
    if rl.redis_client:
        rl.redis_client.delete("rl:token:valid_token_rl")

    try:
        with patch("worker.tasks.process_query_task.apply_async"):
            # Request 1: OK
            r1 = client.post(
                "/api/v1/scans",
                headers={"Authorization": "Bearer valid_token_rl"},
                json={"url": "https://example.com"}
            )
            assert r1.status_code == 200

            # Request 2: OK
            r2 = client.post(
                "/api/v1/scans",
                headers={"Authorization": "Bearer valid_token_rl"},
                json={"url": "https://example.com"}
            )
            assert r2.status_code == 200

            # Request 3: Exceeds limit (2) -> must return 429
            r3 = client.post(
                "/api/v1/scans",
                headers={"Authorization": "Bearer valid_token_rl"},
                json={"url": "https://example.com"}
            )
            assert r3.status_code == 429
            assert r3.json()["detail"] == "Rate limit exceeded. Please try again later."
    finally:
        rl.STANDARD_LIMIT = orig_limit
        rl._memory_store.clear()
        if rl.redis_client:
            rl.redis_client.delete("rl:token:valid_token_rl")
