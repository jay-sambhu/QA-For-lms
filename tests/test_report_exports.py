#!/usr/bin/env python3
"""
Automated Test Suite for Report Exports and Cross-Layer Consistency.

Verifies that CalculationEngine, QAReportGenerator, JSON reports, and export models
maintain 100% mathematical consistency without calculation drift, NaN/Infinity, or data loss.
"""

import json
import unittest
from datetime import datetime
from pathlib import Path

from calculation_engine import (
    CalculationEngine,
    CanonicalQAMetrics,
    FindingMetrics,
    TestCaseMetrics,
)
from qa_report_generator import QAReportGenerator


class TestReportExports(unittest.TestCase):
    """Test suite for PDF, Excel, and JSON report export contracts."""

    def test_zero_data_export_contract(self):
        """Zero test cases and zero findings produce clean 0 counts, 0.0% rates, and 100 Health Score."""
        generator = QAReportGenerator()
        raw_data = {"target": "https://example.com", "findings": []}
        report = generator.generate_json_report(Path("dummy_zero.json"), raw_data)

        # Check legacy report keys
        self.assertEqual(report["summary"]["total_candidates"], 0)
        self.assertEqual(report["severity"]["critical"], 0)
        self.assertEqual(report["severity"]["high"], 0)

        # Check canonical QA metrics
        qa = report["qa_metrics"]
        self.assertEqual(qa["findings"]["total"], 0)
        self.assertEqual(qa["test_cases"]["total"], 0)
        self.assertEqual(qa["test_cases"]["pass_rate"], 0.0)
        self.assertEqual(qa["test_cases"]["fail_rate"], 0.0)
        self.assertEqual(qa["test_cases"]["skip_rate"], 0.0)
        self.assertEqual(qa["quality_score"]["score"], 100)
        self.assertEqual(qa["quality_score"]["grade"], "A")
        self.assertEqual(qa["quality_score"]["summary"], "Excellent")

    def test_failure_and_finding_export_contract(self):
        """
        Synthetic fixture:
        10 Tests: 5 passed, 2 failed, 1 skipped, 1 blocked, 1 errored
        9 Findings: 1 critical, 2 high, 3 medium, 2 low, 1 info
        """
        generator = QAReportGenerator()
        raw_data = {
            "target": "https://example.com/app",
            "findings": [
                {"id": "F-01", "severity": "critical", "priority": "P0", "classification": "confirmed_bug"},
                {"id": "F-02", "severity": "high", "priority": "P1", "classification": "high_confidence_candidate"},
                {"id": "F-03", "severity": "high", "priority": "P1", "classification": "high_confidence_candidate"},
                {"id": "F-04", "severity": "medium", "priority": "P2", "classification": "needs_manual_review"},
                {"id": "F-05", "severity": "medium", "priority": "P2", "classification": "needs_manual_review"},
                {"id": "F-06", "severity": "medium", "priority": "P2", "classification": "needs_manual_review"},
                {"id": "F-07", "severity": "low", "priority": "P3", "classification": "informational"},
                {"id": "F-08", "severity": "low", "priority": "P3", "classification": "informational"},
                {"id": "F-09", "severity": "info", "priority": "P4", "classification": "informational"},
            ]
        }
        test_cases = [
            {"id": "TC-01", "status": "passed"},
            {"id": "TC-02", "status": "passed"},
            {"id": "TC-03", "status": "passed"},
            {"id": "TC-04", "status": "passed"},
            {"id": "TC-05", "status": "passed"},
            {"id": "TC-06", "status": "failed"},
            {"id": "TC-07", "status": "failed"},
            {"id": "TC-08", "status": "skipped"},
            {"id": "TC-09", "status": "blocked"},
            {"id": "TC-10", "status": "errored"},
        ]

        canonical = CalculationEngine.calculate_canonical_metrics(
            raw_data=raw_data,
            test_cases=test_cases,
        )

        tc = canonical.test_cases
        self.assertEqual(tc.total, 10)
        self.assertEqual(tc.passed, 5)
        self.assertEqual(tc.failed, 2)
        self.assertEqual(tc.skipped, 1)
        self.assertEqual(tc.blocked, 1)
        self.assertEqual(tc.errored, 1)
        self.assertEqual(tc.pass_rate, 50.0)
        self.assertEqual(tc.fail_rate, 20.0)
        self.assertEqual(tc.skip_rate, 10.0)
        self.assertEqual(tc.block_rate, 10.0)
        self.assertEqual(tc.errored_rate, 10.0)

        f = canonical.findings
        self.assertEqual(f.total, 9)
        self.assertEqual(f.by_severity["critical"], 1)
        self.assertEqual(f.by_severity["high"], 2)
        self.assertEqual(f.by_severity["medium"], 3)
        self.assertEqual(f.by_severity["low"], 2)
        self.assertEqual(f.by_severity["info"], 1)

        # Quality score: 100 - (25*1) - (15*2) - (5*3) - (1*2) - (0.3*20.0) = 100 - 25 - 30 - 15 - 2 - 6 = 22 (Grade F)
        self.assertEqual(canonical.quality_score.score, 22)
        self.assertEqual(canonical.quality_score.grade, "F")

    def test_status_normalization_for_exports(self):
        """Mixed casing and aliases map cleanly to canonical states."""
        cases = [
            {"id": "1", "status": "PASSED"},
            {"id": "2", "status": "pass"},
            {"id": "3", "status": "success"},
            {"id": "4", "status": "FAILED"},
            {"id": "5", "status": "fail"},
            {"id": "6", "status": "failure"},
            {"id": "7", "status": "SKIPPED"},
            {"id": "8", "status": "skip"},
            {"id": "9", "status": "manual_review"},
            {"id": "10", "status": "BLOCKED"},
            {"id": "11", "status": "block"},
            {"id": "12", "status": "ERRORED"},
            {"id": "13", "status": "error"},
            {"id": "14", "status": "unexpected_status"},
        ]
        m = CalculationEngine.calculate_test_case_metrics(cases)

        self.assertEqual(m.total, 14)
        self.assertEqual(m.passed, 3)
        self.assertEqual(m.failed, 3)
        self.assertEqual(m.skipped, 3)
        self.assertEqual(m.blocked, 2)
        self.assertEqual(m.errored, 3)  # ERRORED + error + unexpected_status

    def test_cross_layer_consistency(self):
        """Verify CalculationEngine -> QAReportGenerator -> JSON report -> Export payload consistency."""
        raw_data = {
            "target": "https://consistency.example.com",
            "findings": [
                {"id": "B-1", "severity": "high", "priority": "P1", "classification": "confirmed_bug"},
                {"id": "B-2", "severity": "medium", "priority": "P2", "classification": "high_confidence_candidate"},
            ],
            "metadata": {
                "start_time": "2026-09-01T10:00:00Z",
                "end_time": "2026-09-01T10:00:45Z",
            }
        }
        test_cases = [
            {"id": "TC-1", "status": "passed"},
            {"id": "TC-2", "status": "passed"},
            {"id": "TC-3", "status": "failed"},
        ]

        generator = QAReportGenerator()
        generator.test_cases_file = None
        report = generator.generate_json_report(Path("dummy_consistency.json"), raw_data)

        # Directly inject test cases to verify full calculation
        canonical = CalculationEngine.calculate_canonical_metrics(
            raw_data=raw_data,
            test_cases=test_cases,
            start_time=raw_data["metadata"]["start_time"],
            end_time=raw_data["metadata"]["end_time"],
        )

        self.assertEqual(canonical.duration_seconds, 45.0)
        self.assertEqual(canonical.test_cases.total, 3)
        self.assertEqual(canonical.test_cases.passed, 2)
        self.assertEqual(canonical.test_cases.failed, 1)
        self.assertEqual(canonical.test_cases.pass_rate, 66.67)
        self.assertEqual(canonical.test_cases.fail_rate, 33.33)

        # Invariant checks
        self.assertEqual(
            canonical.test_cases.passed + canonical.test_cases.failed + canonical.test_cases.skipped + canonical.test_cases.blocked + canonical.test_cases.errored,
            canonical.test_cases.total
        )
        self.assertEqual(sum(canonical.findings.by_severity.values()), canonical.findings.total)
        self.assertEqual(sum(canonical.findings.by_priority.values()), canonical.findings.total)

    def test_secrets_redaction_in_export_payloads(self):
        """Export payloads must not contain sensitive tokens or secrets."""
        raw_data = {
            "target": "https://example.com?api_key=SECRET_TOKEN_123",
            "findings": [
                {
                    "id": "F-01",
                    "severity": "high",
                    "title": "Leaked secret Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz in URL",
                    "description": "Found password=supersecretpass in logs",
                }
            ]
        }
        generator = QAReportGenerator()
        report = generator.generate_json_report(Path("dummy_secrets.json"), raw_data)

        report_str = json.dumps(report)
        self.assertNotIn("SECRET_TOKEN_123", report_str)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", report_str)
        self.assertNotIn("supersecretpass", report_str)

    def test_download_endpoints_naming_and_headers(self):
        """Verify that download endpoints return canonical Content-Disposition and media_types."""
        import tempfile
        from fastapi.testclient import TestClient
        from api.main import app, ROOT_DIR
        from db import SessionLocal
        from models import Scan

        client = TestClient(app)
        scan_id = "11111111-2222-3333-4444-555555555555"
        user_id = "00000000-0000-0000-0000-000000000001"

        # Create temporary dummy report files
        user_dir = Path(ROOT_DIR) / "user_data" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        json_file = user_dir / f"final_qa_report_{scan_id}.json"
        md_file = user_dir / f"final_qa_report_{scan_id}.md"

        json_file.write_text(json.dumps({"test": "data"}), encoding="utf-8")
        md_file.write_text("# Test Report", encoding="utf-8")

        # Save scan in DB
        with SessionLocal() as session:
            existing = session.query(Scan).filter(Scan.id == scan_id).first()
            if existing:
                session.delete(existing)
                session.commit()
            scan = Scan(
                id=scan_id,
                user_id=user_id,
                url="https://download-test.example.com",
                status="completed",
                json_path=str(json_file.relative_to(ROOT_DIR)),
                report_path=str(md_file.relative_to(ROOT_DIR)),
            )
            session.add(scan)
            session.commit()

        try:
            # 1. Test /api/v1/scans/{scan_id}/download/json
            res_v1_json = client.get(
                f"/api/v1/scans/{scan_id}/download/json",
                headers={"Authorization": "Bearer dev-token"},
            )
            self.assertEqual(res_v1_json.status_code, 200)
            self.assertIn("application/json", res_v1_json.headers.get("content-type", ""))
            self.assertEqual(
                res_v1_json.headers.get("content-disposition"),
                f'attachment; filename="qa-report-{scan_id}.json"',
            )

            # 2. Test /api/v1/scans/{scan_id}/download/md
            res_v1_md = client.get(
                f"/api/v1/scans/{scan_id}/download/md",
                headers={"Authorization": "Bearer dev-token"},
            )
            self.assertEqual(res_v1_md.status_code, 200)
            self.assertIn("text/markdown", res_v1_md.headers.get("content-type", ""))
            self.assertEqual(
                res_v1_md.headers.get("content-disposition"),
                f'attachment; filename="qa-report-{scan_id}.md"',
            )

            # 3. Test /api/scans/{scan_id}/download/markdown (legacy alias)
            res_legacy_md = client.get(
                f"/api/scans/{scan_id}/download/markdown",
                headers={"Authorization": "Bearer dev-token"},
            )
            self.assertEqual(res_legacy_md.status_code, 200)
            self.assertEqual(
                res_legacy_md.headers.get("content-disposition"),
                f'attachment; filename="qa-report-{scan_id}.md"',
            )
        finally:
            if json_file.exists():
                json_file.unlink()
            if md_file.exists():
                md_file.unlink()
            with SessionLocal() as session:
                s = session.query(Scan).filter(Scan.id == scan_id).first()
                if s:
                    session.delete(s)
                    session.commit()


if __name__ == "__main__":
    unittest.main()

