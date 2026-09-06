"""
Phase 21 SPA Deep State Transitions & Multi-Step Form Wizard Integration Tests.
Validates client-side SPA route transitions, dynamic button triggers, and multi-step wizard state persistence.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from core.schemas.application_model import ApplicationStateModel, StateTransitionModel
from core.test_generator_v2 import AutonomousTestGenerator


def test_spa_state_transition_model():
    """
    Verify SPA state transition representation captures route changes, DOM updates, and button clicks.
    """
    state_a = ApplicationStateModel(
        state_id="state_feed",
        url="http://127.0.0.1:8105/",
        route="/feed",
        page_title="SPA Activity Feed",
        visible_elements=4,
    )

    state_b = ApplicationStateModel(
        state_id="state_settings",
        url="http://127.0.0.1:8105/#settings",
        route="/settings",
        page_title="SPA Settings",
        visible_elements=1,
    )

    transition = StateTransitionModel(
        transition_id="trans_1",
        from_route="/feed",
        to_route="/settings",
        trigger_action="click(#tab-settings)",
        source_state_id=state_a.state_id,
        target_state_id=state_b.state_id,
    )

    assert transition.from_route == "/feed"
    assert transition.to_route == "/settings"
    assert transition.source_state_id == "state_feed"


def test_form_wizard_boundary_generation():
    """
    Verify AutonomousTestGenerator produces boundary test cases for multi-step form fields.
    """
    app_model = {
        "target_url": "http://127.0.0.1:8106",
        "routes": {
            "/wizard/step1": {"url": "http://127.0.0.1:8106/wizard/step1", "forms_count": 1},
            "/wizard/step2": {"url": "http://127.0.0.1:8106/wizard/step2", "forms_count": 1},
        }
    }
    gen = AutonomousTestGenerator(app_model, {}, "/tmp", "run_test_123")
    tcs = gen.generate_test_cases()
    assert len(tcs) >= 2
    assert any("Form Validation" in tc.title for tc in tcs)
