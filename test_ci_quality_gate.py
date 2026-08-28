import unittest
import os
import json
import tempfile
import ci_quality_gate

class TestCIQualityGate(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.report_path = os.path.join(self.test_dir.name, "report.json")

        # Save old environment variables
        self.old_env = {}
        for k in ["CI_FAIL_ON_NEW_CRITICAL", "CI_FAIL_ON_NEW_HIGH", "CI_FAIL_ON_NEW_MEDIUM", "GITHUB_STEP_SUMMARY"]:
            self.old_env[k] = os.environ.get(k)
        
        # Reset variables for tests
        os.environ["CI_FAIL_ON_NEW_CRITICAL"] = "true"
        os.environ["CI_FAIL_ON_NEW_HIGH"] = "true"
        os.environ["CI_FAIL_ON_NEW_MEDIUM"] = "false"

    def tearDown(self):
        for k, v in self.old_env.items():
            if v is None:
                if k in os.environ:
                    del os.environ[k]
            else:
                os.environ[k] = v
        self.test_dir.cleanup()

    def _write_report(self, findings, fixed=0):
        report = {
            "report_metadata": {"target": "test", "pages_crawled": 1},
            "summary": {"regression_summary": {"fixed": fixed}},
            "findings": findings
        }
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(report, f)

    def test_no_findings(self):
        self._write_report([])
        exit_code = ci_quality_gate.evaluate_quality_gate(self.report_path)
        self.assertEqual(exit_code, 0)

    def test_new_critical_fails(self):
        self._write_report([
            {"regression_status": "NEW", "severity": "critical"}
        ])
        exit_code = ci_quality_gate.evaluate_quality_gate(self.report_path)
        self.assertEqual(exit_code, 1)

    def test_new_high_fails(self):
        self._write_report([
            {"regression_status": "NEW", "severity": "high"}
        ])
        exit_code = ci_quality_gate.evaluate_quality_gate(self.report_path)
        self.assertEqual(exit_code, 1)

    def test_new_medium_configurable(self):
        self._write_report([
            {"regression_status": "NEW", "severity": "medium"}
        ])
        # Default config: MEDIUM doesn't fail
        exit_code = ci_quality_gate.evaluate_quality_gate(self.report_path)
        self.assertEqual(exit_code, 0)

        # Reconfigure: MEDIUM fails
        os.environ["CI_FAIL_ON_NEW_MEDIUM"] = "true"
        exit_code = ci_quality_gate.evaluate_quality_gate(self.report_path)
        self.assertEqual(exit_code, 1)

    def test_new_info_passes(self):
        self._write_report([
            {"regression_status": "NEW", "severity": "info"}
        ])
        exit_code = ci_quality_gate.evaluate_quality_gate(self.report_path)
        self.assertEqual(exit_code, 0)

    def test_persisting_critical_passes(self):
        self._write_report([
            {"regression_status": "UNCHANGED", "severity": "critical"}
        ])
        exit_code = ci_quality_gate.evaluate_quality_gate(self.report_path)
        self.assertEqual(exit_code, 0)

    def test_worsened_critical_fails(self):
        self._write_report([
            {"regression_status": "WORSENED", "severity": "critical"}
        ])
        exit_code = ci_quality_gate.evaluate_quality_gate(self.report_path)
        self.assertEqual(exit_code, 1)

    def test_improved_critical_passes(self):
        self._write_report([
            {"regression_status": "IMPROVED", "severity": "critical"}
        ])
        exit_code = ci_quality_gate.evaluate_quality_gate(self.report_path)
        self.assertEqual(exit_code, 0)

if __name__ == "__main__":
    unittest.main()
