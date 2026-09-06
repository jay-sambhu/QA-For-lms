"""
Unit tests for Defect Verification Loop, Fingerprint Deduplication, and Regression Memory Engine.
"""
import json
import os
import tempfile
from core.defect_verification import DefectVerificationEngine
from core.regression_v2 import RegressionMemoryEngine
from core.schemas.defect import DefectSeverity


def test_defect_verification_deduplication():
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_findings = [
            {"page": "https://example.com/login", "title": "500 Internal Error", "description": "Server crashed during auth", "severity": "critical"},
            {"page": "https://example.com/login", "title": "500 Internal Error", "description": "Server crashed during auth", "severity": "critical"},
            {"page": "https://example.com/login", "title": "500 Internal Error", "description": "Server crashed during auth", "severity": "critical"},
            {"page": "https://example.com/dashboard", "title": "Button Overflow", "description": "UI element clips screen", "severity": "low"},
        ]

        engine = DefectVerificationEngine(raw_findings, tmp_dir, "scan_def_001")
        defects = engine.process_and_deduplicate()

        assert len(defects) == 2  # Deduplicated 3 identical + 1 distinct
        assert os.path.exists(engine.output_file)

        login_defect = next(d for d in defects if d.affected_url == "https://example.com/login")
        assert login_defect.occurrence_count == 3
        assert login_defect.severity == DefectSeverity.CRITICAL


def test_regression_memory_engine():
    with tempfile.TemporaryDirectory() as tmp_dir:
        baseline_file = os.path.join(tmp_dir, "baseline.json")
        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump({
                "defects": [
                    {"fingerprint": "fp_old_bug_001"},
                    {"fingerprint": "fp_fixed_bug_002"}
                ]
            }, f)

        current_defects = [
            {"defect_id": "DEF-001", "fingerprint": "fp_old_bug_001"},
            {"defect_id": "DEF-002", "fingerprint": "fp_new_bug_003"},
        ]

        reg_engine = RegressionMemoryEngine(current_defects, baseline_file, tmp_dir, "scan_reg_001")
        analysis = reg_engine.analyze_regression()

        assert "DEF-001" in analysis.regressions
        assert "DEF-002" in analysis.new_failures
        assert len(analysis.fixed_defects) == 1
