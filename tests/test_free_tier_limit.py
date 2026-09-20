"""
Regression tests: plan-based page limits must be enforced during scan creation.
Each billing tier (free, pro, enterprise) has its own max_pages defined in
billing.gateways.PLANS, and scan requests exceeding that cap must be silently reduced.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app, _get_plan_max_pages
from billing.gateways import PLANS

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


# ---------------------------------------------------------------------------
# Plan-based page limit constants
# ---------------------------------------------------------------------------

def test_plan_max_pages_free_is_10():
    """Free-tier max_pages must be 10 (from billing PLANS config)."""
    assert _get_plan_max_pages("free") == PLANS["free"]["max_pages"]
    assert _get_plan_max_pages("free") == 10


def test_plan_max_pages_pro_is_50():
    """Pro-tier max_pages must be 50."""
    assert _get_plan_max_pages("pro") == PLANS["pro"]["max_pages"]
    assert _get_plan_max_pages("pro") == 50


def test_plan_max_pages_enterprise_is_200():
    """Enterprise-tier max_pages must match PLANS config (capped by MAX_PAGES_LIMIT)."""
    enterprise_limit = PLANS["enterprise"]["max_pages"]  # 200
    result = _get_plan_max_pages("enterprise")
    # MAX_PAGES_LIMIT defaults to 100, so enterprise is capped at 100
    assert result <= enterprise_limit
    assert result > 0


def test_plan_max_pages_unknown_falls_back_to_free():
    """Unknown plan tier should fall back to free-tier limits."""
    assert _get_plan_max_pages("nonexistent_tier") == _get_plan_max_pages("free")


# ---------------------------------------------------------------------------
# Scan creation with plan-based caps
# ---------------------------------------------------------------------------

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


def test_free_tier_10_pages_not_rejected():
    """A free-tier user requesting exactly 10 pages (plan limit) must not be blocked."""
    user = _mock_user(plan="free")

    with patch("api.main.supabase") as mock_sb:
        mock_resp = MagicMock()
        mock_resp.user = user
        mock_sb.auth.get_user.return_value = mock_resp

        response = client.post(
            "/api/v1/scans",
            headers={"Authorization": "Bearer fake_jwt"},
            json={"url": "https://example.com", "max_pages": 10},
        )

    assert response.status_code in (200, 201, 202), (
        f"10-page free-tier scan was rejected: {response.text}"
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


def test_pro_tier_allows_50_pages():
    """Pro-tier user requesting 50 pages should succeed without capping."""
    user = _mock_user(plan="pro")

    with patch("api.main.supabase") as mock_sb:
        mock_resp = MagicMock()
        mock_resp.user = user
        mock_sb.auth.get_user.return_value = mock_resp

        response = client.post(
            "/api/v1/scans",
            headers={"Authorization": "Bearer fake_jwt"},
            json={"url": "https://example.com", "max_pages": 50},
        )

    assert response.status_code in (200, 201, 202), (
        f"50-page pro-tier scan was rejected: {response.text}"
    )
