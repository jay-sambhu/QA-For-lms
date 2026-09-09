"""
Unit tests for Phase 20 Deep Stateful Exploration, Application State Model, and Console Error Filtering.
"""
from core.schemas.application_model import ApplicationStateModel
from core.bug_detector import QAFindingClassifier


def test_application_state_schema():
    state = ApplicationStateModel(
        state_id="state_001",
        url="http://127.0.0.1:8101/items",
        route="/items",
        page_title="Inventory Items",
        authentication_state="anonymous",
        visible_elements=15,
        forms_count=1,
        interactive_buttons=["#btn-add", "#del-999"],
    )
    assert state.state_id == "state_001"
    assert state.forms_count == 1
    assert len(state.interactive_buttons) == 2


def test_console_error_noise_filter():
    classifier = QAFindingClassifier(
        target_domain="127.0.0.1",
        crawl_result={
            "console_errors": [
                # 1. Non-critical sub-resource 404 -> MUST BE IGNORED (NO FP)
                {
                    "page": "http://127.0.0.1:8101/items/1/edit",
                    "text": "Failed to load resource: the server responded with a status of 404 (Not Found)",
                },
                # 2. Critical JS TypeError -> MUST BE ELEVATED (TRUE POSITIVE)
                {
                    "page": "http://127.0.0.1:8102/cart",
                    "text": "Uncaught TypeError: Cannot read properties of null (reading 'quantity')",
                },
            ]
        },
    )
    classifier.classify_console_errors()

    # Only the JS TypeError should be retained as a finding; sub-resource 404 must be filtered out!
    assert len(classifier.findings) == 1
    assert classifier.findings[0]["error_category"] == "javascript_exception"
