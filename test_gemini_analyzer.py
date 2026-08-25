#!/usr/bin/env python3
"""Unit tests for the Gemini QA candidate analyzer."""

import asyncio
import copy
import json
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
        self.candidate_401 = {
            "id": "CANDIDATE-001",
            "type": "http_error",
            "severity": "medium",
            "confidence": "medium",
            "root_cause_key": "https://api.example.com/api/auth/me|401|GET",
            "url": "https://api.example.com/api/auth/me",
            "status": 401,
            "method": "GET",
            "resource_type": "xhr",
            "title": "Repeated HTTP 401 response",
            "description": "Potential authentication issue",
            "occurrences": 2,
            "affected_pages": ["https://example.com/", "https://example.com/login"],
            "screenshots": ["missing-home.png", "missing-login.png"],
            "evidence": {
                "http_errors": [{"status": 401, "url": "https://api.example.com/api/auth/me"}],
                "console_errors": [{"text": "Failed to load resource: status of 401"}],
                "network_failures": [],
            },
        }
        self.candidate_500 = copy.deepcopy(self.candidate_401)
        self.candidate_500.update({
            "id": "CANDIDATE-002",
            "status": 500,
            "url": "https://api.example.com/api/broken",
        })
        self.data = {
            "target": "https://example.com/",
            "source_file": "results/qa_findings_test.json",
            "root_cause_candidates": [self.candidate_401],
        }

    def response(self, classification="expected_behavior", severity="medium", confidence="high"):
        return json.dumps({
            "classification": classification,
            "severity": severity,
            "confidence": confidence,
            "title": "Validated candidate",
            "reasoning": "The supplied evidence supports this assessment.",
            "user_impact": "No visible impact established.",
            "recommendation": "Review the endpoint behavior in an authenticated flow.",
            "evidence_used": ["HTTP status and affected pages"],
        })

    def test_candidate_json_loads_correctly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "findings.json"
            path.write_text(json.dumps(self.data), encoding="utf-8")
            loaded = GeminiQAAnalyzer.load_findings(path)
        self.assertEqual(loaded["root_cause_candidates"][0]["id"], "CANDIDATE-001")

    def test_missing_api_key_is_handled_gracefully(self):
        result = asyncio.run(GeminiQAAnalyzer(api_key="").analyze(self.data))
        finding = result["findings"][0]
        self.assertEqual(finding["classification"], "needs_manual_review")
        self.assertEqual(finding["confidence"], "low")
        self.assertEqual(result["summary"]["needs_manual_review"], 1)

    def test_missing_screenshot_is_handled_gracefully(self):
        package = GeminiQAAnalyzer._compact_evidence(self.candidate_401)
        self.assertEqual(package["screenshots"], [])
        self.assertIn("unavailable", package["screenshot_analysis_note"])

    def test_malformed_gemini_json_is_handled(self):
        client = FakeClient(responses=["not json", "still not json"])
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(self.data))
        self.assertEqual(result["findings"][0]["classification"], "needs_manual_review")
        self.assertEqual(result["findings"][0]["confidence"], "low")

    def test_401_can_be_expected_behavior(self):
        client = FakeClient(responses=[self.response()])
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(self.data))
        self.assertEqual(result["findings"][0]["classification"], "expected_behavior")
        self.assertIn("authentication", client.prompts[0].lower())

    def test_500_can_be_likely_bug(self):
        data = copy.deepcopy(self.data)
        data["root_cause_candidates"] = [self.candidate_500]
        client = FakeClient(responses=[self.response("likely_bug", "high")])
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(data))
        self.assertEqual(result["findings"][0]["classification"], "likely_bug")
        self.assertEqual(result["findings"][0]["severity"], "high")

    def test_quota_error_returns_manual_review_without_retry(self):
        client = FakeClient(error=RuntimeError("429 quota exceeded"))
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(self.data))
        self.assertEqual(result["findings"][0]["classification"], "needs_manual_review")
        self.assertEqual(len(client.prompts), 1)

    def test_original_evidence_is_not_overwritten(self):
        original = copy.deepcopy(self.data["root_cause_candidates"][0])
        client = FakeClient(responses=[self.response()])
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(self.data))
        self.assertEqual(result["findings"][0]["candidate"], original)
        self.assertEqual(self.data["root_cause_candidates"][0], original)

    def test_unique_ai_finding_ids(self):
        data = copy.deepcopy(self.data)
        data["root_cause_candidates"] = [self.candidate_401, self.candidate_500]
        client = FakeClient(responses=[self.response(), self.response()])
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(data))
        self.assertEqual([f["id"] for f in result["findings"]], ["AI-BUG-001", "AI-BUG-002"])

    def test_multiple_candidates_are_processed_independently(self):
        data = copy.deepcopy(self.data)
        data["root_cause_candidates"] = [self.candidate_401, self.candidate_500]
        client = FakeClient(responses=[self.response(), self.response("likely_bug", "high")])
        result = asyncio.run(GeminiQAAnalyzer(model_client=client).analyze(data))
        self.assertEqual(result["summary"]["candidates_analyzed"], 2)
        self.assertEqual(len(client.prompts), 2)
        self.assertEqual(result["findings"][1]["classification"], "likely_bug")


if __name__ == "__main__":
    unittest.main()
