import os
import pytest
from fastapi import HTTPException
from unittest.mock import patch

from api.main import require_user, missing_supabase_vars, _startup_diag
import api.main


def test_supabase_env_vars_loaded_at_startup():
    """Verify that NEXT_PUBLIC_SUPABASE_URL is loaded into os.environ at import time."""
    assert "NEXT_PUBLIC_SUPABASE_URL" in os.environ
    assert len(os.environ["NEXT_PUBLIC_SUPABASE_URL"].strip()) > 0
    assert _startup_diag.startswith("[SUPABASE AUTH] Environment check:")


def test_require_user_fails_with_specific_missing_vars_when_supabase_is_none():
    """Verify require_user raises 503 detailing the exact missing variables when supabase is None."""
    with patch.object(api.main, "supabase", None):
        with patch.object(api.main, "missing_supabase_vars", ["NEXT_PUBLIC_SUPABASE_URL"]):
            with pytest.raises(HTTPException) as exc_info:
                require_user("Bearer test_token_123")

            assert exc_info.value.status_code == 503
            assert "missing environment variable(s) NEXT_PUBLIC_SUPABASE_URL" in exc_info.value.detail
