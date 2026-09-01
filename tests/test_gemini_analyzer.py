import asyncio
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from gemini_analyzer import GeminiQAAnalyzer


class FakeClient:
    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.prompts = []

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.responses.pop(0)


class TestGeminiQAAnalyzer(unittest.TestCase):
    def setUp(self):
        self.candidate = {
            "id": "CANDIDATE-001", "url": "https://api.dplms.com/api/auth/me",
            "status": 401, "method": "GET", "resource_type": "xhr",
            "severity": "medium", "confidence": "medium",
            "title": "Authentication check", "description": "401 response",
            "occurrences": 2, "affected_pages": ["https://dplms.com/", "https://dplms.com/login"],
            "screenshots": ["missing.png", "missing2.png"], "first_party": True,
            "evidence": {
                "http_errors": [{"status": 401, "url": "https://api.dplms.com/api/auth/me"}],
                "console_errors": [{"text": "status of 401"}], "network_failures": [],
            },
        }
        self.data = {
            "target": "https://dplms.com/", "crawl_source": "results/crawl.json",
            "root_cause_candidates": [self.candidate],
        }

    def response(self, classification="needs_manual_review", severity="medium", confidence="medium"):
        return json.dumps({
            "classification": classification, "severity": severity, "confidence": confidence,
            "title": "QA assessment", "summary": "Evidence-based assessment",
            "expected_result": "Expected behavior.", "actual_result": "Actual behavior.",
            "reasoning": "Only supplied evidence was considered.",
            "user_impact": "User impact cannot be determined from the available crawl evidence.",
            "recommended_action": "Verify behavior with an authenticated session.",
            "evidence_used": ["HTTP status", "affected pages"],
        })

    def analyze_with(self, response, data=None):
        return asyncio.run(GeminiQAAnalyzer(model_client=FakeClient([response])).analyze(data or self.data))

    def test_latest_findings_file_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "qa_findings_20260824_000000.json"
            new = root / "qa_findings_20260825_000000.json"
            old.write_text("{}")
            new.write_text("{}")
            self.assertEqual(GeminiQAAnalyzer.find_latest_findings(root), new)

    def test_latest_findings_prefers_newest_not_highest_name(self):
        """A UUID run id must not lose to a lexicographically larger name.

        The API names each run after its scan UUID, so filename order carries no
        chronological meaning. Selecting by name picked whichever id happened to
        sort highest, which meant a concurrent scan could analyse another scan's
        crawl output.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # 'z...' sorts after 'a...', but is written first and back-dated.
            stale = root / "qa_findings_zzzzzzzz-0000-0000-0000-000000000000.json"
            fresh = root / "qa_findings_aaaaaaaa-0000-0000-0000-000000000000.json"
            stale.write_text("{}")
            fresh.write_text("{}")
            os.utime(stale, (1_000_000, 1_000_000))

            self.assertEqual(GeminiQAAnalyzer.find_latest_findings(root), fresh)

    def test_no_findings_file_handling(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(GeminiQAAnalyzer.find_latest_findings(directory))

    def test_root_cause_candidate_extraction(self):
        result = self.analyze_with(self.response())
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["candidate_id"], "CANDIDATE-001")

    def test_candidate_evidence_preservation(self):
        original = copy.deepcopy(self.candidate)
        result = self.analyze_with(self.response())
        self.assertEqual(result["findings"][0]["candidate"], original)
        self.assertEqual(self.data["root_cause_candidates"][0], original)

    def test_401_needs_manual_review(self):
        result = self.analyze_with(self.response())
        self.assertEqual(result["findings"][0]["classification"], "needs_manual_review")

    def test_403_needs_manual_review(self):
        data = copy.deepcopy(self.data)
        data["root_cause_candidates"][0]["status"] = 403
        result = self.analyze_with(self.response(), data)
        self.assertEqual(result["findings"][0]["classification"], "needs_manual_review")

    def test_404_high_confidence_candidate(self):
        result = self.analyze_with(self.response("high_confidence_candidate", "high", "high"))
        self.assertEqual(result["findings"][0]["classification"], "high_confidence_candidate")
        self.assertEqual(result["findings"][0]["severity"], "high")

    def test_500_high_confidence_candidate(self):
        data = copy.deepcopy(self.data)
        data["root_cause_candidates"][0]["status"] = 500
        result = self.analyze_with(self.response("high_confidence_candidate", "high", "high"), data)
        self.assertEqual(result["findings"][0]["severity"], "high")

    def test_runtime_exception_high_confidence_candidate(self):
        data = copy.deepcopy(self.data)
        data["root_cause_candidates"][0]["evidence"]["console_errors"] = [{"text": "TypeError: failed"}]
        result = self.analyze_with(self.response("high_confidence_candidate", "high", "high"), data)
        self.assertEqual(result["findings"][0]["classification"], "high_confidence_candidate")

    def test_err_aborted_informational(self):
        result = self.analyze_with(self.response("informational", "info", "high"))
        self.assertEqual(result["findings"][0]["classification"], "informational")

    def test_google_analytics_informational(self):
        result = self.analyze_with(self.response("informational", "info", "low"))
        self.assertEqual(result["findings"][0]["classification"], "informational")

    def test_hostname_boundary_first_party_detection(self):
        for url in ["https://dplms.com", "https://www.dplms.com", "https://api.dplms.com", "https://sub.api.dplms.com"]:
            self.assertTrue(GeminiQAAnalyzer.is_first_party(url, "dplms.com"))
        for url in ["https://evil-dplms.com", "https://dplms.com.evil.com"]:
            self.assertFalse(GeminiQAAnalyzer.is_first_party(url, "dplms.com"))

    def test_repeated_candidate_is_one_input(self):
        data = copy.deepcopy(self.data)
        data["root_cause_candidates"] = [self.candidate]
        client = FakeClient([self.response()])
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(data))
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn('"occurrences": 2', client.prompts[0])

    def test_malformed_json_safe_fallback_and_raw_response_redacted(self):
        client = FakeClient(["not json", "Authorization: Bearer abc"])
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(self.data))
        finding = result["findings"][0]
        self.assertEqual(finding["classification"], "needs_manual_review")
        self.assertNotIn("abc", json.dumps(result))

    def test_markdown_wrapped_json(self):
        result = self.analyze_with("```json\n" + self.response("expected_behavior", "info", "high") + "\n```")
        self.assertEqual(result["findings"][0]["classification"], "expected_behavior")

    def test_invalid_classification_safe_fallback(self):
        result = self.analyze_with(self.response("bug_magic"))
        self.assertEqual(result["findings"][0]["classification"], "needs_manual_review")

    def test_api_failure_safe_fallback(self):
        client = FakeClient(error=RuntimeError("network failure"))
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(self.data))
        self.assertEqual(result["summary"]["needs_manual_review"], 1)

    def test_missing_api_key_safe_fallback(self):
        result = asyncio.run(GeminiQAAnalyzer(api_key="").analyze(self.data))
        self.assertEqual(result["findings"][0]["classification"], "needs_manual_review")

    def test_missing_screenshot_safe(self):
        package = GeminiQAAnalyzer.compact_evidence(self.candidate, self.data["target"])
        self.assertFalse(package["screenshot_evidence"][0]["available"])
        self.assertIn("unavailable", package["screenshot_note"])

    def test_unique_finding_ids_and_no_duplicates(self):
        data = copy.deepcopy(self.data)
        second = copy.deepcopy(self.candidate)
        second["id"] = "CANDIDATE-002"
        data["root_cause_candidates"] = [self.candidate, second]
        client = FakeClient([self.response(), self.response()])
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(data))
        self.assertEqual([f["id"] for f in result["findings"]], ["AI-BUG-001", "AI-BUG-002"])

    def test_summary_severity_confidence_and_classification_counts(self):
        data = copy.deepcopy(self.data)
        second = copy.deepcopy(self.candidate)
        second["id"] = "CANDIDATE-002"
        data["root_cause_candidates"] = [self.candidate, second]
        client = FakeClient([self.response(), self.response("expected_behavior", "info", "high")])
        summary = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(data))["summary"]
        self.assertEqual(summary["total_candidates"], 2)
        self.assertEqual(summary["severity_counts"]["medium"], 1)
        self.assertEqual(summary["confidence_counts"]["high"], 1)
        self.assertEqual(summary["classification_counts"]["expected_behavior"], 1)

    def test_markdown_report_generation(self):
        result = self.analyze_with(self.response())
        markdown = GeminiQAAnalyzer.render_markdown(result)
        self.assertIn("# AI QA Analysis Report", markdown)
        self.assertIn("## Manual Review Required", markdown)
        self.assertIn("CANDIDATE-001", markdown)


if __name__ == "__main__":
    unittest.main()
