import os
import sys

# Ensure repository root and core package are in sys.path for test discovery and modular imports
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

CORE_DIR = os.path.join(ROOT_DIR, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

# Ensure test session default DATABASE_URL is isolated to prevent modifying or colliding with live qa_agent.db
if not os.environ.get("DATABASE_URL"):
    _test_db_path = os.path.join(ROOT_DIR, "test_qa_agent.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"

import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="session", autouse=True)
def cleanup_isolated_test_database():
    """Clean up the isolated test SQLite database after the test session."""
    yield
    test_db = os.path.join(ROOT_DIR, "test_qa_agent.db")
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def mock_supabase_jwt(request):
    """
    Auto-mock Supabase JWT validation so tests never make a real network call to Supabase.
    Can be bypassed for tests marked with @pytest.mark.live_auth.
    """
    if "live_auth" in request.keywords:
        yield
        return

    mock_user_obj = MagicMock()
    mock_user_obj.id = "00000000-0000-0000-0000-000000000001"
    mock_user_obj.email = "tester@example.com"
    mock_user_obj.role = "authenticated"
    mock_user_obj.user_metadata = {"role": "user"}

    mock_resp = MagicMock()
    mock_resp.user = mock_user_obj

    try:
        import api.main
    except Exception:
        yield
        return

    if api.main.supabase is not None:
        with patch.object(api.main.supabase.auth, "get_user", return_value=mock_resp):
            yield
    else:
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_resp
        orig_client = api.main.supabase
        api.main.supabase = mock_client
        try:
            yield
        finally:
            api.main.supabase = orig_client
