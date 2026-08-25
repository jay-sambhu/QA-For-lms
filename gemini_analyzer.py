#!/usr/bin/env python3
"""Gemini-powered validation of deterministic QA root-cause candidates."""

import asyncio
import json
import os
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


CLASSIFICATIONS = {
    "likely_bug",
    "possible_bug",
    "expected_behavior",
    "false_positive",
    "needs_manual_review",
}
SEVERITIES = {"critical", "high", "medium", "low", "info"}
CONFIDENCES = {"high", "medium", "low"}
RESPONSE_FIELDS = (
    "classification",
    "severity",
    "confidence",
    "title",
    "reasoning",
    "user_impact",
    "recommendation",
    "evidence_used",
)


class GeminiQAAnalyzer:
    """Analyze root-cause candidates without changing deterministic evidence."""

    def __init__(self, api_key=None, model_client=None, model_name="gemini-3-flash-preview"):
        load_dotenv(dotenv_path=".env")
        self.api_key = api_key if api_key is not None else os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name
        self.model_client = model_client
        self._client_error = None

        if self.model_client is None and self.api_key:
            try:
                from browser_use import ChatGoogle
                self.model_client = ChatGoogle(
                    model=self.model_name,
                    api_key=self.api_key,
                )
            except Exception as error:
                self._client_error = str(error)

    @staticmethod
    def find_latest_findings(results_dir="results"):
        """Return the newest deterministic QA findings file."""
        files = sorted(Path(results_dir).glob("qa_findings_*.json"), reverse=True)
        return files[0] if files else None

    @staticmethod
    def load_findings(path):
        """Load a deterministic findings JSON document."""
        with open(path, encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _compact_evidence(candidate):
        """Build a bounded evidence package while retaining representative detail."""
        evidence = candidate.get("evidence") or {}
        package = {
            "candidate_id": candidate.get("id"),
            "root_cause_key": candidate.get("root_cause_key"),
            "url": candidate.get("url"),
            "status": candidate.get("status"),
            "method": candidate.get("method"),
            "resource_type": candidate.get("resource_type"),
            "occurrences": candidate.get("occurrences", 0),
            "affected_pages": candidate.get("affected_pages", []),
            "deterministic_title": candidate.get("title", ""),
            "deterministic_description": candidate.get("description", ""),
            "first_party": candidate.get("first_party"),
            "http_evidence": (evidence.get("http_errors") or [])[:3],
            "console_evidence": (evidence.get("console_errors") or [])[:5],
            "network_evidence": (evidence.get("network_failures") or [])[:5],
            "screenshots": [
                {"page": page, "path": screenshot}
                for page, screenshot in zip(
                    candidate.get("affected_pages", []),
                    candidate.get("screenshots", []),
                )
                if Path(screenshot).exists()
            ],
            "screenshot_analysis_note": "Screenshot analysis unavailable through the text model interface.",
        }
        return package

    @classmethod
    def build_prompt(cls, candidate):
        """Create the focused senior-QA prompt for one candidate."""
        evidence = cls._compact_evidence(candidate)
        return (
            "You are a senior QA engineer validating one deterministic root-cause candidate.\n"
            "Return ONLY valid JSON, with exactly these fields:\n"
            f"{json.dumps(RESPONSE_FIELDS)}\n"
            "Classification must be one of: likely_bug, possible_bug, expected_behavior, "
            "false_positive, needs_manual_review. Severity must be one of: critical, high, "
            "medium, low, info. Confidence must be high, medium, or low.\n"
            "Reason only from the supplied evidence. Do not invent HTTP responses, screenshots, "
            "or user impact. A 401 alone is not a bug: explicitly consider whether this is an "
            "authentication/session/cart/user endpoint used by anonymous users. A first-party "
            "500/502/503/504 is a strong candidate, but inspect the evidence. Treat a first-party "
            "404 as likely_bug only when evidence indicates a broken internal link or user-facing "
            "resource. If screenshots are listed, use their page association; otherwise state that "
            "screenshot analysis is unavailable.\n\n"
            "Candidate evidence:\n"
            + json.dumps(evidence, indent=2, ensure_ascii=False)
        )

    async def _call_model(self, prompt):
        """Call the configured ChatGoogle client, supporting test doubles and async clients."""
        if self.model_client is None:
            raise RuntimeError("GOOGLE_API_KEY is missing or Gemini client is unavailable")
        if hasattr(self.model_client, "ainvoke"):
            response = await self.model_client.ainvoke(prompt)
        elif hasattr(self.model_client, "invoke"):
            response = self.model_client.invoke(prompt)
        elif callable(self.model_client):
            response = self.model_client(prompt)
            if hasattr(response, "__await__"):
                response = await response
        else:
            raise TypeError("Unsupported Gemini client interface")
        return getattr(response, "content", response)

    @staticmethod
    def _parse_response(response):
        """Parse JSON or fenced JSON returned by Gemini."""
        if isinstance(response, dict):
            parsed = response
        else:
            text = str(response).strip()
            fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
            if fenced:
                text = fenced.group(1).strip()
            parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response must be a JSON object")
        return parsed

    @staticmethod
    def _validated_response(response):
        """Keep only the documented response fields and validate enum values."""
        parsed = GeminiQAAnalyzer._parse_response(response)
        classification = parsed.get("classification")
        severity = parsed.get("severity")
        confidence = parsed.get("confidence")
        if classification not in CLASSIFICATIONS:
            raise ValueError("Invalid classification")
        if severity not in SEVERITIES:
            raise ValueError("Invalid severity")
        if confidence not in CONFIDENCES:
            raise ValueError("Invalid confidence")
        evidence_used = parsed.get("evidence_used", [])
        if not isinstance(evidence_used, list) or not all(isinstance(item, str) for item in evidence_used):
            raise ValueError("evidence_used must be a list of strings")
        return {
            "classification": classification,
            "severity": severity,
            "confidence": confidence,
            "title": str(parsed.get("title", "")),
            "reasoning": str(parsed.get("reasoning", "")),
            "user_impact": str(parsed.get("user_impact", "")),
            "recommendation": str(parsed.get("recommendation", "")),
            "evidence_used": evidence_used,
        }

    @staticmethod
    def _failure_response(reason):
        return {
            "classification": "needs_manual_review",
            "severity": "medium",
            "confidence": "low",
            "title": "Gemini analysis unavailable",
            "reasoning": reason,
            "user_impact": "Not determined without candidate validation.",
            "recommendation": "Review the deterministic candidate and its screenshots manually.",
            "evidence_used": [],
        }

    async def analyze_candidate(self, candidate):
        """Analyze one candidate, with at most one controlled retry."""
        prompt = self.build_prompt(candidate)
        if self.model_client is None:
            return self._failure_response("Gemini analysis failed; manual review required.")

        try:
            raw_response = await self._call_model(prompt)
            return self._validated_response(raw_response)
        except Exception as error:
            if "429" in str(error) or "quota" in str(error).lower():
                return self._failure_response("Gemini quota limit reached; manual review required.")
            try:
                raw_response = await self._call_model(prompt)
                return self._validated_response(raw_response)
            except Exception:
                return self._failure_response("Gemini analysis failed; manual review required.")

    async def analyze(self, findings_data):
        """Analyze every candidate independently and preserve source candidates verbatim."""
        candidates = findings_data.get("root_cause_candidates", [])
        findings = []
        for index, candidate in enumerate(candidates, start=1):
            analysis = await self.analyze_candidate(candidate)
            finding = {
                "id": f"AI-BUG-{index:03d}",
                "candidate_id": candidate.get("id"),
                **analysis,
                "candidate": deepcopy(candidate),
                "evidence_used": analysis.get("evidence_used", []),
            }
            findings.append(finding)

        counts = {classification: 0 for classification in CLASSIFICATIONS}
        for finding in findings:
            counts[finding["classification"]] += 1
        return {
            "target": findings_data.get("target"),
            "source_file": findings_data.get("source_file", ""),
            "summary": {
                "candidates_analyzed": len(findings),
                "likely_bugs": counts["likely_bug"],
                "possible_bugs": counts["possible_bug"],
                "expected_behavior": counts["expected_behavior"],
                "false_positives": counts["false_positive"],
                "needs_manual_review": counts["needs_manual_review"],
            },
            "findings": findings,
        }


async def generate_ai_findings(findings_file=None):
    """Load the latest deterministic findings and write AI validation results."""
    path = Path(findings_file) if findings_file else GeminiQAAnalyzer.find_latest_findings()
    if path is None:
        print("No deterministic QA findings found")
        return None
    data = GeminiQAAnalyzer().load_findings(path)
    analyzer = GeminiQAAnalyzer()
    result = await analyzer.analyze(data)
    result["source_file"] = str(path)
    output_file = Path("results") / f"ai_qa_findings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("AI QA ANALYSIS")
    print("=" * 60)
    print(f"\nSource:\n{path}")
    print(f"\nCandidates:\n{result['summary']['candidates_analyzed']}")
    for finding in result["findings"]:
        print(f"\nAnalyzing {finding['candidate_id']}...")
        print(f"Classification: {finding['classification']}")
        print(f"Severity: {finding['severity']}")
        print(f"Confidence: {finding['confidence']}")
    summary = result["summary"]
    print("\n" + "=" * 60)
    print("AI QA SUMMARY")
    print("=" * 60)
    print(f"\nLikely bugs: {summary['likely_bugs']}")
    print(f"\nPossible bugs: {summary['possible_bugs']}")
    print(f"\nExpected behavior: {summary['expected_behavior']}")
    print(f"\nFalse positives: {summary['false_positives']}")
    print(f"\nManual review: {summary['needs_manual_review']}")
    print(f"\nResults saved to:\n{output_file}\n")
    return result


if __name__ == "__main__":
    asyncio.run(generate_ai_findings())
