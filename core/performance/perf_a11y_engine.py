"""
Autonomous Accessibility & Lightweight Performance Engine (Phase 11).
"""
import json
import os
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class PerformanceMetricsModel(BaseModel):
    url: str
    page_load_ms: float
    dom_content_loaded_ms: float
    total_resources: int
    slow_requests_count: int


class AccessibilityViolationModel(BaseModel):
    rule_id: str
    impact: str  # critical, serious, moderate, minor
    description: str
    help_url: Optional[str] = None
    target_selector: str


class PerfA11yEngine:
    def __init__(self, pages_data: List[Dict[str, Any]], results_dir: str, run_id: str):
        self.pages_data = pages_data
        self.results_dir = results_dir
        self.run_id = run_id
        self.output_file = os.path.join(results_dir, f"perf_a11y_{run_id}.json")

    def audit_pages(self) -> Dict[str, Any]:
        perf_records = []
        a11y_violations = []

        for p in self.pages_data:
            url = p.get("url", "/")
            perf_records.append(
                PerformanceMetricsModel(
                    url=url,
                    page_load_ms=p.get("load_time_ms", 350.0),
                    dom_content_loaded_ms=p.get("dom_loaded_ms", 180.0),
                    total_resources=len(p.get("elements", [])),
                    slow_requests_count=0,
                )
            )

            # Audit images missing alt text
            for el in p.get("elements", []):
                if el.get("tag_name") == "img" and not el.get("attributes", {}).get("alt"):
                    a11y_violations.append(
                        AccessibilityViolationModel(
                            rule_id="image-alt-missing",
                            impact="critical",
                            description="Image element missing required alt attribute for accessibility",
                            target_selector=f"img#{el.get('element_id')}",
                        )
                    )

        result = {
            "scan_id": self.run_id,
            "performance": [pr.model_dump() for pr in perf_records],
            "accessibility_violations": [a.model_dump() for a in a11y_violations],
        }

        os.makedirs(self.results_dir, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        return result
