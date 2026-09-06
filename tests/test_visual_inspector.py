"""
Unit tests for JASUSS RealBrowserVisualInspector.
"""
import pytest
from core.visual_inspector import RealBrowserVisualInspector


def test_visual_overflow_detection():
    inspector = RealBrowserVisualInspector(viewport_width=1280, viewport_height=720)

    # Element exceeding viewport width (App E SPA Overflow bug)
    overflow_elem = {
        "selector": "#spa-overflow",
        "scroll_width": 5000,
        "bounding_right": 5000,
        "is_visible": True,
        "bounding_width": 5000,
        "bounding_height": 40
    }
    findings = inspector.inspect_element_layout(overflow_elem)
    assert len(findings) == 1
    assert findings[0].defect_type == "UI_OVERFLOW"
    assert findings[0].severity == "HIGH"


def test_blank_page_detection():
    inspector = RealBrowserVisualInspector(viewport_width=1280, viewport_height=720)
    findings = inspector.inspect_page_canvas(DOM_tree_count=1, visible_text_length=0)
    assert len(findings) == 1
    assert findings[0].defect_type == "BLANK_PAGE_RENDER"
    assert findings[0].severity == "CRITICAL"
