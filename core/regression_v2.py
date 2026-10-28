"""
Autonomous Regression Memory and Flakiness Detection Engine (Phase 9).

The baseline defaults to the user's most recent final report for the same
target host, so every scan after the first can say which findings are new,
which are unchanged and which were fixed.
"""
import glob
import json
import os
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from core.schemas.regression import RegressionAnalysisModel


def _comparable_host(url: str) -> str:
    host = (urlparse(url or "").hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


class RegressionMemoryEngine:
    def __init__(self, current_defects: List[Dict[str, Any]], baseline_file: Optional[str], results_dir: str, run_id: str,
                 target: Optional[str] = None):
        self.current_defects = current_defects
        self.baseline_file = baseline_file
        self.results_dir = results_dir
        self.run_id = run_id
        self.target = target or ""
        self.output_file = os.path.join(results_dir, f"regression_{run_id}.json")
        self.status_by_fingerprint: Dict[str, str] = {}
        self.baseline_fingerprints = set()

    def find_default_baseline(self) -> Optional[str]:
        """Newest earlier final_qa_report for the same host, if any."""
        if not self.target:
            return None
        host = _comparable_host(self.target)
        candidates = []
        for path in glob.glob(os.path.join(self.results_dir, "final_qa_report_*.json")):
            if path.endswith(f"final_qa_report_{self.run_id}.json"):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            report_target = (data.get("report_metadata") or {}).get("target") or data.get("target") or ""
            if _comparable_host(report_target) != host:
                continue
            candidates.append((os.path.getmtime(path), path))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    @staticmethod
    def _baseline_fingerprints(path: str) -> set:
        fingerprints = set()
        try:
            with open(path, "r", encoding="utf-8") as f:
                base_data = json.load(f)
        except Exception:
            return fingerprints
        if isinstance(base_data, list):
            items = base_data
        else:
            items = list(base_data.get("defects", []) or []) + list(base_data.get("findings", []) or [])
        for item in items:
            if not isinstance(item, dict):
                continue
            fp = item.get("fingerprint") or (item.get("candidate") or {}).get("fingerprint")
            if fp:
                fingerprints.add(fp)
        return fingerprints

    def analyze_regression(self) -> RegressionAnalysisModel:
        baseline = self.baseline_file
        if not baseline or not os.path.exists(baseline):
            baseline = self.find_default_baseline()
        baseline_fingerprints = self._baseline_fingerprints(baseline) if baseline else set()
        self.baseline_fingerprints = baseline_fingerprints

        current_fingerprints = {d.get("fingerprint"): d for d in self.current_defects if d.get("fingerprint")}

        regressions = []
        new_failures = []
        fixed_defects = []

        for fp, d in current_fingerprints.items():
            if fp in baseline_fingerprints:
                regressions.append(d.get("defect_id", fp))
                self.status_by_fingerprint[fp] = "unchanged"
            else:
                new_failures.append(d.get("defect_id", fp))
                self.status_by_fingerprint[fp] = "new"

        for b_fp in baseline_fingerprints:
            if b_fp not in current_fingerprints:
                fixed_defects.append(b_fp[:8])

        analysis = RegressionAnalysisModel(
            scan_id=self.run_id,
            baseline_scan_id=baseline,
            new_failures=new_failures,
            regressions=regressions,
            fixed_defects=fixed_defects,
            flaky_tests=[],
        )

        os.makedirs(self.results_dir, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(analysis.model_dump(), f, indent=2)

        return analysis
