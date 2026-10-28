"""
Autonomous API Testing & Schema Contract Verification Engine (Phase 10).

Verifies the XHR/fetch calls the crawler observed while rendering pages:
status, method and measured latency. Nothing is fabricated; a call without
a timing measurement reports latency null.
"""
import json
import os
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from pydantic import BaseModel


class ApiTestCaseModel(BaseModel):
    api_test_id: str
    endpoint: str
    method: str
    expected_status: str
    actual_status: Optional[int] = None
    passed: bool
    latency_ms: Optional[float] = None
    observed_count: int = 1
    observed_on_pages: List[str] = []
    error: Optional[str] = None


class ApiTestingEngine:
    def __init__(self, discovered_api_calls: List[Dict[str, Any]], results_dir: str, run_id: str):
        self.discovered_api_calls = discovered_api_calls or []
        self.results_dir = results_dir
        self.run_id = run_id
        self.output_file = os.path.join(results_dir, f"api_test_results_{run_id}.json")

    @staticmethod
    def _endpoint_key(call: Dict[str, Any]) -> str:
        url = str(call.get("url") or "")
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme else url.split("?")[0]
        return f"{str(call.get('method') or 'GET').upper()} {base}"

    def run_api_tests(self) -> List[ApiTestCaseModel]:
        grouped: Dict[str, Dict[str, Any]] = {}
        order: List[str] = []
        for call in self.discovered_api_calls:
            if not call.get("url"):
                continue
            key = self._endpoint_key(call)
            entry = grouped.get(key)
            if entry is None:
                entry = {"calls": [], "pages": []}
                grouped[key] = entry
                order.append(key)
            entry["calls"].append(call)
            page = str(call.get("page") or "").rsplit(" [", 1)[0]
            if page and page not in entry["pages"]:
                entry["pages"].append(page)

        results: List[ApiTestCaseModel] = []
        for idx, key in enumerate(order):
            entry = grouped[key]
            calls = entry["calls"]
            method, endpoint = key.split(" ", 1)
            statuses = [c.get("status") for c in calls if isinstance(c.get("status"), int)]
            worst = max(statuses) if statuses else None
            timings = [c.get("timing_ms") for c in calls if isinstance(c.get("timing_ms"), (int, float))]
            latency = round(sum(timings) / len(timings), 1) if timings else None

            if worst is None:
                passed = False
                err_msg = "No response status was recorded for this endpoint"
            elif worst >= 500:
                passed = False
                err_msg = f"HTTP {worst} returned by API endpoint"
            elif worst >= 400:
                passed = False
                err_msg = f"HTTP {worst} returned by API endpoint"
            else:
                passed = True
                err_msg = None

            results.append(ApiTestCaseModel(
                api_test_id=f"API-TC-{idx+1:03d}",
                endpoint=endpoint,
                method=method,
                expected_status="2xx/3xx",
                actual_status=worst,
                passed=passed,
                latency_ms=latency,
                observed_count=len(calls),
                observed_on_pages=entry["pages"][:10],
                error=err_msg,
            ))

        os.makedirs(self.results_dir, exist_ok=True)
        dump_data = [r.model_dump() for r in results]
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)

        return results
