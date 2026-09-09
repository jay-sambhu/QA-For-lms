"""
Unit tests for JASUSS MultiSessionManager.
"""
from core.multi_session_manager import MultiSessionManager


def test_session_creation_and_isolation():
    mgr = MultiSessionManager()
    sess_a = mgr.create_session("sess_a", "USER", "user_101", "token_101")
    sess_b = mgr.create_session("sess_b", "USER", "user_102", "token_102")
    sess_admin = mgr.create_session("sess_c", "ADMIN", "admin_001", "token_admin")

    assert sess_a.user_id == "user_101"
    assert sess_b.user_id == "user_102"
    assert sess_a.auth_token != sess_b.auth_token

    # Validate authorization checks
    assert mgr.validate_authorization("sess_a", "USER", "user_101") is True
    assert mgr.validate_authorization("sess_b", "USER", "user_101") is False
    assert mgr.validate_authorization("sess_a", "ADMIN") is False
    assert mgr.validate_authorization("sess_c", "ADMIN") is True

    # Invalidate session A
    mgr.invalidate_session("sess_a")
    assert mgr.get_session("sess_a") is None
    assert mgr.validate_authorization("sess_a", "USER", "user_101") is False
    assert mgr.get_session("sess_b") is not None
