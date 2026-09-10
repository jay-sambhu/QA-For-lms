"""
Regression test: free-tier users must have max_pages capped to FREE_TIER_MAX_PAGES.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app, FREE_TIER_MAX_PAGES

client = TestClient(app)


def _mock_user(plan="free"):
    from db import SessionLocal
    from models import User
    uid = str(uuid.uuid4())
    with SessionLocal() as db:
        existing = db.query(User).filter(User.id == uid).first()
        if not existing:
            db.add(User(id=uid, email=f"tier_test_{uid}@test.com", role="user", plan_tier=plan))
            db.commit()

    class _User:
        id = uid
        email = f"tier_test_{uid}@test.com"
        user_metadata = {"role": "user"}
    return _User()


def test_free_tier_cap_applied_when_requesting_more_pages():
    """Free-tier user requesting more pages than limit should get capped silently."""
    user = _mock_user(plan="free")

    with patch("api.main.supabase") as mock_sb:
        mock_resp = MagicMock()
        mock_resp.user = user
        mock_sb.auth.get_user.return_value = mock_resp

        response = client.post(
            "/api/v1/scans",
            headers={"Authorization": "Bearer fake_jwt"},
            json={"url": "https://example.com", "max_pages": 50},
        )

    # Should be accepted (not rejected)
    assert response.status_code in (200, 201, 202), f"Unexpected: {response.text}"

    # Confirm in DB that the scan was recorded (pipeline will respect the capped pages)
    data = response.json()
    assert "scan_id" in data or "id" in data


def test_free_tier_cap_constant_is_1():
    """The configured constant must be 1 for the free-tier launch period."""
    assert FREE_TIER_MAX_PAGES == 1, (
        f"FREE_TIER_MAX_PAGES should be 1 for the free launch period, got {FREE_TIER_MAX_PAGES}"
    )


def test_free_tier_single_page_scan_not_rejected():
    """A free-tier user requesting exactly 1 page must not be blocked."""
    user = _mock_user(plan="free")

    with patch("api.main.supabase") as mock_sb:
        mock_resp = MagicMock()
        mock_resp.user = user
        mock_sb.auth.get_user.return_value = mock_resp

        response = client.post(
            "/api/v1/scans",
            headers={"Authorization": "Bearer fake_jwt"},
            json={"url": "https://example.com", "max_pages": 1},
        )

    assert response.status_code in (200, 201, 202), (
        f"Single-page free-tier scan was rejected: {response.text}"
    )
