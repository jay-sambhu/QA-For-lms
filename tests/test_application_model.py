"""
Unit tests for Persistent Application Knowledge Model Manager.
"""
import os
import tempfile
from core.application_model.manager import ApplicationKnowledgeManager


def test_application_knowledge_manager_initialization():
    with tempfile.TemporaryDirectory() as tmp_dir:
        mgr = ApplicationKnowledgeManager("https://example.com", tmp_dir)
        assert mgr.model.target_url == "https://example.com"
        assert os.path.exists(mgr.model_path)


def test_update_from_discovery():
    with tempfile.TemporaryDirectory() as tmp_dir:
        mgr = ApplicationKnowledgeManager("https://example.com", tmp_dir)
        discovery_data = {
            "pages": [
                {
                    "route": "/login",
                    "url": "https://example.com/login",
                    "title": "Login Page",
                    "forms": [{"form_id": "login_form"}],
                    "elements": [{"element_id": "btn_submit"}],
                    "api_calls": [{"method": "POST", "url": "/api/v1/auth/login"}],
                },
                {
                    "route": "/dashboard",
                    "url": "https://example.com/dashboard",
                    "title": "User Dashboard",
                    "forms": [],
                    "elements": [],
                    "api_calls": [],
                },
            ]
        }
        updated_model = mgr.update_from_discovery(discovery_data)
        assert "/login" in updated_model.routes
        assert "/dashboard" in updated_model.routes
        assert updated_model.routes["/dashboard"]["requires_auth"] is True
        assert len(updated_model.workflows) >= 1
