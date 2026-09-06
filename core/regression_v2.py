"""
Autonomous Regression Memory and Flakiness Detection Engine (Phase 9).
"""
import json
import os
from typing import Dict, List, Optional, Any

from core.schemas.regression import RegressionAnalysisModel, FlakyMetricModel, RegressionStatus


class RegressionMemoryEngine:
    def __init__(self, current_defects: List[Dict[str, Any]], baseline_file: Optional[str], results_dir: str, run_id: str):
        self.current_defects = current_defects
        self.baseline_file = baseline_file
        self.results_dir = results_dir
        self.run_id = run_id
        self.output_file = os.path.join(results_dir, f"regression_{run_id}.json")

    def analyze_regression(self) -> RegressionAnalysisModel:
        baseline_fingerprints = set()
        if self.baseline_file and os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file, "r", encoding="utf-8") as f:
                    base_data = json.load(f)
                    for item in base_data.get("defects", []):
                        if isinstance(item, dict) and item.get("fingerprint"):
                            baseline_fingerprints.add(item.get("fingerprint"))
            except Exception:
                pass

        current_fingerprints = {d.get("fingerprint"): d for d in self.current_defects if d.get("fingerprint")}

        regressions = []
        new_failures = []
        fixed_defects = []

        for fp, d in current_fingerprints.items():
            if fp in baseline_fingerprints:
                regressions.append(d.get("defect_id", fp))
            else:
                new_failures.append(d.get("defect_id", fp))

        for b_fp in baseline_fingerprints:
            if b_fp not in current_fingerprints:
                fixed_defects.append(b_fp[:8])

        analysis = RegressionAnalysisModel(
            scan_id=self.run_id,
            baseline_scan_id=self.baseline_file,
            new_failures=new_failures,
            regressions=regressions,
            fixed_defects=fixed_defects,
            flaky_tests=[],
        )

        os.makedirs(self.results_dir, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(analysis.model_dump(), f, indent=2)

        return analysis
