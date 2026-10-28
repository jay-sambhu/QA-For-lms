"""
Autonomous Accessibility & Lightweight Performance Engine (Phase 11).

Numbers come from the crawler's Navigation Timing capture and DOM checks;
when a page has no measurement the value is null, never a default.
"""
import json
import os
from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class PerformanceMetricsModel(BaseModel):
    url: str
    page_load_ms: Optional[float] = None
    dom_content_loaded_ms: Optional[float] = None
    ttfb_ms: Optional[float] = None
    transfer_size_bytes: Optional[int] = None
    total_resources: Optional[int] = None
    slow_requests_count: Optional[int] = None
    measured: bool = False


class AccessibilityViolationModel(BaseModel):
    rule_id: str
    impact: str  # critical, serious, moderate, minor
    description: str
    help_url: Optional[str] = None
    target_selector: str
    page_url: Optional[str] = None
    count: int = 1


# (check key, rule id, impact, description, selector, help)
_COUNT_RULES = (
    ("images_missing_alt", "image-alt", "critical",
     "Images without an alt attribute are announced as unlabeled by screen readers.",
     "img:not([alt])", "https://dequeuniversity.com/rules/axe/4.8/image-alt"),
    ("inputs_without_label", "label", "critical",
     "Form fields without an associated label cannot be identified by assistive technology.",
     "input, select, textarea", "https://dequeuniversity.com/rules/axe/4.8/label"),
    ("controls_without_name", "button-name", "serious",
     "Buttons and links without an accessible name cannot be understood out of context.",
     "button, [role=button], a[href]", "https://dequeuniversity.com/rules/axe/4.8/button-name"),
)

_FLAG_RULES = (
    ("has_lang", "html-has-lang", "serious",
     "The <html> element has no lang attribute, so screen readers may use the wrong pronunciation rules.",
     "html", "https://dequeuniversity.com/rules/axe/4.8/html-has-lang"),
    ("has_title", "document-title", "serious",
     "The page has no <title>, so it cannot be identified in tabs, history or by screen readers.",
     "head > title", "https://dequeuniversity.com/rules/axe/4.8/document-title"),
    ("has_main_landmark", "landmark-one-main", "moderate",
     "The page has no main landmark, which makes skipping to the content harder.",
     "main, [role=main]", "https://dequeuniversity.com/rules/axe/4.8/landmark-one-main"),
)


class PerfA11yEngine:
    def __init__(self, pages_data: List[Dict[str, Any]], results_dir: str, run_id: str):
        self.pages_data = pages_data
        self.results_dir = results_dir
        self.run_id = run_id
        self.output_file = os.path.join(results_dir, f"perf_a11y_{run_id}.json")

    @staticmethod
    def _perf_record(page: Dict[str, Any]) -> PerformanceMetricsModel:
        url = page.get("url", "/")
        timings = page.get("timings") or {}
        api_calls = page.get("api_calls") or []
        measured = bool(timings)
        slow_api = sum(1 for c in api_calls if isinstance(c.get("timing_ms"), (int, float)) and c["timing_ms"] > 1000)
        slow_resources = timings.get("slow_resources")
        slow = None
        if measured:
            slow = int(slow_resources or 0) + slow_api
        return PerformanceMetricsModel(
            url=url,
            page_load_ms=timings.get("load_event_ms") if measured else None,
            dom_content_loaded_ms=timings.get("dom_content_loaded_ms") if measured else None,
            ttfb_ms=timings.get("ttfb_ms") if measured else None,
            transfer_size_bytes=timings.get("transfer_size") if measured else None,
            total_resources=timings.get("resource_count") if measured else None,
            slow_requests_count=slow,
            measured=measured,
        )

    @staticmethod
    def _a11y_violations(page: Dict[str, Any]) -> List[AccessibilityViolationModel]:
        url = page.get("url", "/")
        checks = page.get("a11y_checks") or {}
        violations: List[AccessibilityViolationModel] = []
        if not checks:
            # Legacy path: elements captured as ElementModels.
            for el in page.get("elements", []):
                if el.get("tag_name") == "img" and not el.get("attributes", {}).get("alt"):
                    violations.append(AccessibilityViolationModel(
                        rule_id="image-alt",
                        impact="critical",
                        description="Image element missing required alt attribute for accessibility",
                        target_selector=f"img#{el.get('element_id')}",
                        page_url=url,
                    ))
            return violations

        for key, rule_id, impact, description, selector, help_url in _COUNT_RULES:
            count = checks.get(key) or 0
            if isinstance(count, int) and count > 0:
                violations.append(AccessibilityViolationModel(
                    rule_id=rule_id,
                    impact=impact,
                    description=f"{count} element(s): {description}",
                    help_url=help_url,
                    target_selector=selector,
                    page_url=url,
                    count=count,
                ))
        for key, rule_id, impact, description, selector, help_url in _FLAG_RULES:
            if key in checks and not checks.get(key):
                violations.append(AccessibilityViolationModel(
                    rule_id=rule_id,
                    impact=impact,
                    description=description,
                    help_url=help_url,
                    target_selector=selector,
                    page_url=url,
                ))
        return violations

    def audit_pages(self) -> Dict[str, Any]:
        perf_records = []
        a11y_violations = []

        for p in self.pages_data:
            if p.get("error") or p.get("auth_wall"):
                continue
            perf_records.append(self._perf_record(p))
            a11y_violations.extend(self._a11y_violations(p))

        measured = [r for r in perf_records if r.measured and r.page_load_ms]
        summary = {
            "pages_measured": len(measured),
            "pages_unmeasured": len(perf_records) - len(measured),
            "median_load_ms": (sorted(r.page_load_ms for r in measured)[len(measured) // 2] if measured else None),
            "slowest_page": (max(measured, key=lambda r: r.page_load_ms).url if measured else None),
            "a11y_violations": len(a11y_violations),
            "a11y_pages_affected": len({v.page_url for v in a11y_violations}),
        }

        result = {
            "scan_id": self.run_id,
            "summary": summary,
            "performance": [pr.model_dump() for pr in perf_records],
            "accessibility_violations": [a.model_dump() for a in a11y_violations],
        }

        os.makedirs(self.results_dir, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        return result
