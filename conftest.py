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
