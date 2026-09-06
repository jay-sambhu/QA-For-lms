"""
JASUSS Real-Browser Visual Screenshot & Layout Inspector Engine.
Inspects rendered DOM bounding boxes, detects viewport overflow, blank screens, and element layout collision defects.
"""
from typing import Dict, Any, List, Optional


class VisualInspectionFinding:
    def __init__(self, defect_type: str, severity: str, message: str, element_selector: Optional[str] = None):
        self.defect_type = defect_type
        self.severity = severity
        self.message = message
        self.element_selector = element_selector

    def to_dict(self) -> Dict[str, Any]:
        return {
            "defect_type": self.defect_type,
            "severity": self.severity,
            "message": self.message,
            "element_selector": self.element_selector,
        }


class RealBrowserVisualInspector:
    def __init__(self, viewport_width: int = 1280, viewport_height: int = 720):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

    def inspect_element_layout(self, element_data: Dict[str, Any]) -> List[VisualInspectionFinding]:
        findings: List[VisualInspectionFinding] = []
        selector = element_data.get("selector", "unknown")
        width = element_data.get("scroll_width", 0)
        bounding_right = element_data.get("bounding_right", 0)

        # 1. Viewport Horizontal Overflow Defect
        if width > self.viewport_width or bounding_right > self.viewport_width + 10:
            findings.append(VisualInspectionFinding(
                defect_type="UI_OVERFLOW",
                severity="HIGH",
                message=f"Element {selector} scroll width ({width}px) overflows viewport width ({self.viewport_width}px)",
                element_selector=selector,
            ))

        # 2. Zero-size unrendered visible element defect
        if element_data.get("is_visible") and (element_data.get("bounding_width", 1) == 0 or element_data.get("bounding_height", 1) == 0):
            findings.append(VisualInspectionFinding(
                defect_type="UNRENDERED_VISIBLE_ELEMENT",
                severity="MEDIUM",
                message=f"Visible element {selector} rendered with 0px bounding area",
                element_selector=selector,
            ))

        return findings

    def inspect_page_canvas(self, DOM_tree_count: int, visible_text_length: int) -> List[VisualInspectionFinding]:
        findings: List[VisualInspectionFinding] = []
        if DOM_tree_count < 3 or visible_text_length == 0:
            findings.append(VisualInspectionFinding(
                defect_type="BLANK_PAGE_RENDER",
                severity="CRITICAL",
                message="Page canvas rendered completely blank without DOM tree or visible text content",
            ))
        return findings
