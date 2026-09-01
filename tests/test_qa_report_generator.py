import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qa_report_generator import SecretRedactor, QAReportGenerator


class TestSecretRedactor(unittest.TestCase):
    
    def test_secret_redaction(self):
        # API Keys, Tokens, Passwords
        data = {
            "url": "https://api.example.com/?api_key=SECRET123",
            "headers": {
                "Authorization": "Bearer abcdef12345",
                "Cookie": "session_token=XYZ789"
            },
            "evidence": {
                "console_errors": [
                    {"text": "Failed with password: MySecretPassword!"},
                    {"text": "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"}
                ]
            }
        }
        
        redacted = SecretRedactor.redact(data)
        
        self.assertNotIn("SECRET123", redacted["url"])
        self.assertIn("[REDACTED]", redacted["url"])
        
        self.assertNotIn("abcdef12345", redacted["headers"]["Authorization"])
        self.assertIn("[REDACTED]", redacted["headers"]["Authorization"])
        
        self.assertNotIn("XYZ789", redacted["headers"]["Cookie"])
        self.assertIn("[REDACTED]", redacted["headers"]["Cookie"])
        
        self.assertNotIn("MySecretPassword!", redacted["evidence"]["console_errors"][0]["text"])
        self.assertIn("[REDACTED]", redacted["evidence"]["console_errors"][0]["text"])
        
        jwt_text = redacted["evidence"]["console_errors"][1]["text"]
        self.assertNotIn("eyJhbGci", jwt_text)
        self.assertIn("[REDACTED", jwt_text)


class TestQAReportGenerator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.results_dir = Path(self.temp_dir.name)
        self.generator = QAReportGenerator(results_dir=self.results_dir)
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_latest_report_discovery(self):
        # Create dummy reports
        (self.results_dir / "gemini_qa_report_20260801_100000.json").touch()
        latest = self.results_dir / "gemini_qa_report_20260802_100000.json"
        latest.touch()
        
        found = self.generator.find_latest_gemini_report()
        self.assertEqual(found, latest)

    def test_missing_gemini_report_handling(self):
        found = self.generator.find_latest_gemini_report()
        self.assertIsNone(found)
        result = self.generator.generate()
        self.assertIsNone(result)

    def test_json_report_generation_and_counts(self):
        mock_gemini_data = {
            "target": "https://example.com",
            "findings": [
                {
                    "id": "AI-BUG-001",
                    "classification": "confirmed_bug",
                    "severity": "high",
                    "candidate": {
                        "affected_pages": ["page1", "page2"],
                        "occurrences": 2
                    }
                },
                {
                    "id": "AI-BUG-002",
                    "classification": "needs_manual_review",
                    "severity": "medium",
                    "candidate": {}
                },
                {
                    "id": "AI-BUG-003",
                    "classification": "informational",
                    "severity": "info",
                    "candidate": {}
                }
            ]
        }
        
        json_report = self.generator.generate_json_report(Path("dummy.json"), mock_gemini_data)
        
        self.assertEqual(json_report["summary"]["total_candidates"], 3)
        self.assertEqual(json_report["summary"]["confirmed_bugs"], 1)
        self.assertEqual(json_report["summary"]["manual_review"], 1)
        self.assertEqual(json_report["summary"]["informational"], 1)
        
        self.assertEqual(json_report["severity"]["high"], 1)
        self.assertEqual(json_report["severity"]["medium"], 1)
        self.assertEqual(json_report["severity"]["info"], 1)
        
        # Check root-cause grouping (affected_pages count is preserved)
        self.assertEqual(json_report["findings"][0]["affected_pages_count"], 2)
        self.assertEqual(json_report["findings"][1]["affected_pages_count"], 0)

    def test_screenshot_preservation_and_markdown(self):
        mock_gemini_data = {
            "target": "https://example.com",
            "findings": [
                {
                    "id": "AI-BUG-001",
                    "classification": "needs_manual_review",
                    "severity": "medium",
                    "title": "Auth issue",
                    "summary": "Potential auth issue",
                    "candidate": {
                        "screenshots": ["screenshots/test.png"],
                        "url": "https://api.example.com",
                        "affected_pages": ["https://example.com"]
                    }
                },
                {
                    "id": "AI-BUG-002",
                    "classification": "informational",
                    "severity": "info",
                    "title": "No screenshot",
                    "candidate": {}
                }
            ]
        }
        
        # Create a dummy screenshot file so the existence check passes
        os.makedirs(self.results_dir / "screenshots", exist_ok=True)
        (self.results_dir / "screenshots" / "test.png").touch()
        
        # Mock Path.exists to return true for screenshot, because in actual execution the markdown generator checks Path(s).exists()
        # Wait, the screenshot path is relative, we can mock exists to be safe
        with patch.object(Path, 'exists', return_value=True):
            json_report = self.generator.generate_json_report(Path("dummy.json"), mock_gemini_data)
            md = self.generator.generate_markdown_report(json_report)
        
        self.assertIn("[screenshots/test.png](../screenshots/test.png)", md)
        
        # But if it didn't exist? We can test that.
        with patch.object(Path, 'exists', return_value=False):
            md_no_file = self.generator.generate_markdown_report(json_report)
        self.assertIn("Screenshot: Not available", md_no_file)
        
        # For finding without screenshot
        self.assertIn("**Screenshot:** Not available", md)

    def test_no_secret_exposure(self):
        mock_gemini_data = {
            "target": "https://example.com",
            "findings": [
                {
                    "id": "AI-BUG-001",
                    "classification": "needs_manual_review",
                    "severity": "high",
                    "title": "Auth issue with password=secret123",
                    "candidate": {
                        "evidence": {
                            "console_errors": [
                                {"text": "Authorization: Bearer my_secret_token"}
                            ]
                        }
                    }
                }
            ]
        }
        
        json_report = self.generator.generate_json_report(Path("dummy.json"), mock_gemini_data)
        md = self.generator.generate_markdown_report(json_report)
        
        # Should be redacted
        self.assertNotIn("secret123", json.dumps(json_report))
        self.assertNotIn("my_secret_token", json.dumps(json_report))
        
        self.assertNotIn("secret123", md)
        self.assertNotIn("my_secret_token", md)
        self.assertIn("[REDACTED]", md)
        
    def test_empty_findings(self):
        mock_gemini_data = {
            "target": "https://example.com",
            "findings": []
        }
        json_report = self.generator.generate_json_report(Path("dummy.json"), mock_gemini_data)
        self.assertEqual(json_report["summary"]["total_candidates"], 0)
        
        md = self.generator.generate_markdown_report(json_report)
        self.assertIn("**Total findings:** 0", md)


if __name__ == '__main__':
    unittest.main()
