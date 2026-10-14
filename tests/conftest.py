"""
Shared fixtures for tests/.

- Scan creation without a reachable Celery worker falls back to running the
  real pipeline (Chromium + network) inside the API process. No test wants
  that, so the local launcher is stubbed for every test.
- Scan creation requires the user to have an AI provider key (BYOK). Tests
  that exercise unrelated behaviour (rate limiting, plan caps, isolation)
  use ``seed_ai_key`` to give their user one.
"""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _no_real_local_pipeline():
    try:
        import api.main  # noqa: F401
    except Exception:
        yield None
        return
    with patch("api.main._submit_local_scan", MagicMock(name="_submit_local_scan")) as stub:
        yield stub


@pytest.fixture
def seed_ai_key():
    def _seed(user_id: str, email: str, plan_tier: str = "free"):
        from db import SessionLocal
        from models import User

        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                user = User(id=user_id, email=email, role="user", plan_tier=plan_tier)
                db.add(user)
            user.gemini_api_key = "AIzaSy_TEST_KEY_FOR_FIXTURE_000"
            db.commit()

    return _seed
