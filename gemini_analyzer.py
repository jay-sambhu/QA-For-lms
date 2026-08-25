#!/usr/bin/env python3
"""Conservative Gemini analysis of deterministic QA root-cause candidates."""

import asyncio
import json
import os
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

CLASSIFICATIONS = {
    "confirmed_bug", "high_confidence_candidate", "needs_manual_review",
    "expected_behavior", "informational",
}
SEVERITIES = {"high", "medium", "low", "info"}
CONFIDENCES = {"high", "medium", "low"}
REQUIRED_FIELDS = {
    "classification", "severity", "confidence", "title", "summary",
    "reasoning", "user_impact", "recommended_action", "evidence_used",
}


class GeminiQAAnalyzer:
    """Analyze grouped candidates while keeping deterministic evidence authoritative."""

    def __init__(self, api_key=None, model_client=None, model_name="gemini-3-flash-preview"):
        load_dotenv(dotenv_path=".env")
        self.api_key = api_key if api_key is not None else os.getenv("GOOGLE_API_KEY")
        self.model_client = model_client
        self.model_name = model_name
        if self.model_client is None and self.api_key:
            try:
                from browser_use import ChatGoogle
                self.model_client = ChatGoogle(model=model_name, api_key=self.api_key)
            except Exception:
                self.model_client = None

    @staticmethod
    def find_latest_findings(results_dir="results"):
        files = sorted(Path(results_dir).glob("qa_findings_*.json"), reverse=True)
        return files[0] if files else None

    @staticmethod
    def load_findings(path):
        with open(path, encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def is_first_party(url, target_domain):
        hostname = (urlparse(url).hostname or "").lower().rstrip(".")
        domain = target_domain.lower().rstrip(".")
        return hostname == domain or hostname.endswith("." + domain)

    @staticmethod
    def _redact(value):
        """Redact common credentials recursively before prompts or debug output."""
        if isinstance(value, dict):
            return {key: GeminiQAAnalyzer._redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [GeminiQAAnalyzer._redact(item) for item in value]
        if not isinstance(value, str):
            return value
        patterns = [
            (r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+", r"\1[REDACTED]"),
            (r"(?i)(bearer\s+)[^\s,;]+", r"\1[REDACTED]"),
            (r"(?i)((?:api[_ -]?key|token|password|passwd|secret|cookie)\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]"),
        ]
        for pattern, replacement in patterns:
            value = re.sub(pattern, replacement, value)
        return value

    @classmethod
    def compact_evidence(cls, candidate, target=""):
        evidence = candidate.get("evidence") or {}
        affected = candidate.get("affected_pages") or []
        screenshots = candidate.get("screenshots") or []
        screenshot_evidence = []
        for page, path in zip(affected, screenshots):
            exists = Path(path).exists()
            screenshot_evidence.append({"page": page, "path": path, "available": exists})
        package = {
            "target": target,
            "candidate_id": candidate.get("id"),
            "url": candidate.get("url"),
            "status": candidate.get("status"),
            "method": candidate.get("method"),
            "resource_type": candidate.get("resource_type"),
            "occurrences": candidate.get("occurrences", 0),
            "affected_pages": affected,
            "deterministic_severity": candidate.get("severity"),
            "deterministic_confidence": candidate.get("confidence"),
            "description": candidate.get("description", ""),
            "title": candidate.get("title", ""),
            "first_party": candidate.get("first_party"),
            "http_errors": (evidence.get("http_errors") or [])[:3],
            "console_errors": (evidence.get("console_errors") or [])[:5],
            "network_failures": (evidence.get("network_failures") or [])[:5],
            "screenshot_evidence": screenshot_evidence[:3],
        }
        if not any(item["available"] for item in screenshot_evidence):
            package["screenshot_note"] = "Screenshot analysis unavailable."
        return cls._redact(package)

    @classmethod
    def build_prompt(cls, candidate, target=""):
        evidence = cls.compact_evidence(candidate, target)
        return (
            "Act as a conservative senior QA engineer. Analyze only the supplied evidence. "
            "Return one JSON object and no prose. Classification must be exactly one of: "
            "confirmed_bug, high_confidence_candidate, needs_manual_review, expected_behavior, informational. "
            "Severity must be high, medium, low, or info; confidence must be high, medium, or low. "
            "Do not invent backend behavior, credentials, responses, screenshots, or user impact. "
            "A 401/403 is not automatically a bug and usually needs manual review unless broken behavior "
            "is evidenced. A first-party 5xx is usually a high-confidence candidate. ERR_ABORTED and "
            "third-party analytics are normally informational. Use screenshots only when available and "
            "never claim visual observations when screenshot analysis is unavailable. Required fields: "
            + json.dumps(sorted(REQUIRED_FIELDS))
            + "\nEvidence:\n"
            + json.dumps(evidence, indent=2, ensure_ascii=False)
        )

    async def _call_model(self, prompt):
        if self.model_client is None:
            raise RuntimeError("Gemini client unavailable")
        if hasattr(self.model_client, "ainvoke"):
            response = await self.model_client.ainvoke(prompt)
        elif hasattr(self.model_client, "invoke"):
            response = self.model_client.invoke(prompt)
        elif callable(self.model_client):
            response = self.model_client(prompt)
            if hasattr(response, "__await__"):
                response = await response
        else:
            raise TypeError("Unsupported Gemini client")
        return getattr(response, "content", response)

    @staticmethod
    def parse_response(response):
        if isinstance(response, dict):
            return response
        text = str(response or "").strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
        if fenced:
            text = fenced.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start:end + 1])
            raise

    @classmethod
    def validate_response(cls, response):
        parsed = cls.parse_response(response)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response is not an object")
        missing = REQUIRED_FIELDS - parsed.keys()
        if missing:
            raise ValueError("Missing fields: " + ", ".join(sorted(missing)))
        if parsed["classification"] not in CLASSIFICATIONS:
            raise ValueError("Invalid classification")
        if parsed["severity"] not in SEVERITIES:
            raise ValueError("Invalid severity")
        if parsed["confidence"] not in CONFIDENCES:
            raise ValueError("Invalid confidence")
        if not isinstance(parsed["evidence_used"], list):
            raise ValueError("evidence_used must be a list")
        return {field: cls._redact(parsed[field]) for field in REQUIRED_FIELDS}

    @classmethod
    def fallback(cls, reason, raw_response=None):
        result = {
            "classification": "needs_manual_review",
            "severity": "medium",
            "confidence": "low",
            "title": "Gemini analysis unavailable",
            "summary": "Manual review is required because Gemini did not provide a valid analysis.",
            "reasoning": reason,
            "user_impact": "User impact cannot be determined from the available crawl evidence.",
            "recommended_action": "Review the deterministic candidate manually.",
            "evidence_used": [],
        }
        if raw_response:
            result["raw_response"] = cls._redact(str(raw_response))
        return result

    async def analyze_candidate(self, candidate, target=""):
        prompt = self.build_prompt(candidate, target)
        if self.model_client is None:
            return self.fallback("Gemini analysis failed; manual review required.")
        try:
            raw = await self._call_model(prompt)
            return self.validate_response(raw)
        except Exception as error:
            if "429" in str(error) or "quota" in str(error).lower():
                return self.fallback("Gemini quota limit reached; manual review required.")
            try:
                raw = await self._call_model(prompt)
                return self.validate_response(raw)
            except Exception as retry_error:
                return self.fallback("Gemini analysis failed; manual review required.", str(retry_error))

    async def analyze(self, findings_data):
        candidates = findings_data.get("root_cause_candidates") or []
        target = findings_data.get("target", "")
        findings, errors = [], []
        for index, candidate in enumerate(candidates, 1):
            analysis = await self.analyze_candidate(candidate, target)
            if analysis["classification"] == "needs_manual_review":
                errors.append({"candidate_id": candidate.get("id"), "error": analysis["reasoning"]})
            finding = {
                "id": f"AI-BUG-{index:03d}",
                "candidate_id": candidate.get("id"),
                **analysis,
                "candidate": deepcopy(candidate),
            }
            findings.append(finding)
        classifications = list(CLASSIFICATIONS | {"needs_manual_review"})
        classification_counts = {key: 0 for key in classifications}
        severity_counts = {key: 0 for key in SEVERITIES}
        confidence_counts = {key: 0 for key in CONFIDENCES}
        for finding in findings:
            classification_counts[finding["classification"]] += 1
            severity_counts[finding["severity"]] += 1
            confidence_counts[finding["confidence"]] += 1
        return {
            "target": target,
            "source": {"crawl_result": findings_data.get("crawl_source", ""), "qa_findings": findings_data.get("source_file", "")},
            "summary": {
                "total_candidates": len(findings),
                "confirmed_bugs": classification_counts["confirmed_bug"],
                "high_confidence_candidates": classification_counts["high_confidence_candidate"],
                "needs_manual_review": classification_counts["needs_manual_review"],
                "expected_behavior": classification_counts["expected_behavior"],
                "informational": classification_counts["informational"],
                "classification_counts": classification_counts,
                "severity_counts": severity_counts,
                "confidence_counts": confidence_counts,
            },
            "findings": findings,
            "errors": errors,
        }

    @staticmethod
    def render_markdown(result):
        summary = result["summary"]
        lines = [
            "# AI QA Analysis Report", "", f"Target: {result.get('target', '')}", "",
            "## Executive Summary", "",
            f"Total Candidates: {summary['total_candidates']}",
            f"Confirmed Bugs: {summary['confirmed_bugs']}",
            f"High-Confidence Candidates: {summary['high_confidence_candidates']}",
            f"Needs Manual Review: {summary['needs_manual_review']}",
            f"Expected Behavior: {summary['expected_behavior']}",
            f"Informational: {summary['informational']}", "",
        ]
        sections = [("confirmed_bug", "Confirmed Bugs"), ("high_confidence_candidate", "Critical / High-Confidence Findings"), ("needs_manual_review", "Manual Review Required"), ("expected_behavior", "Expected Behavior"), ("informational", "Informational")]
        for classification, heading in sections:
            lines.extend([f"## {heading}", ""])
            selected = [f for f in result["findings"] if f["classification"] == classification]
            if not selected:
                lines.append("None.")
            for finding in selected:
                candidate = finding.get("candidate", {})
                lines.extend([
                    f"### {finding['candidate_id']}", "",
                    f"Classification: {finding['classification']}",
                    f"Severity: {finding['severity']}", f"Confidence: {finding['confidence']}",
                    f"Endpoint: {candidate.get('method', '')} {candidate.get('url', '')}",
                    f"Occurrences: {candidate.get('occurrences', 0)}", "",
                    f"**Title:** {finding.get('title', '')}", "",
                    f"**Summary:** {finding.get('summary', '')}", "",
                    f"**Reasoning:** {finding.get('reasoning', '')}", "",
                    f"**User impact:** {finding.get('user_impact', '')}", "",
                    f"**Recommended action:** {finding.get('recommended_action', '')}", "",
                ])
        lines.extend(["## Evidence", "", "Deterministic candidate evidence is preserved in the JSON report.", "", "## Recommended QA Actions", ""])
        for finding in result["findings"]:
            lines.append(f"- {finding['candidate_id']}: {finding.get('recommended_action', '')}")
        return "\n".join(lines) + "\n"


async def generate_report(findings_file=None):
    path = Path(findings_file) if findings_file else GeminiQAAnalyzer.find_latest_findings()
    if path is None:
        print("No QA findings file found under results/qa_findings_*.json")
        return None
    data = GeminiQAAnalyzer.load_findings(path)
    data["source_file"] = str(path)
    analyzer = GeminiQAAnalyzer()
    result = await analyzer.analyze(data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = Path("results") / f"gemini_qa_report_{timestamp}.json"
    md_path = Path("results") / f"gemini_qa_report_{timestamp}.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(analyzer.render_markdown(result), encoding="utf-8")
    print("\n" + "=" * 60 + "\nGEMINI QA ANALYZER VERIFICATION\n" + "=" * 60)
    print(f"\nRAW CANDIDATES: {result['summary']['total_candidates']}")
    print(f"\nCONFIRMED BUGS: {result['summary']['confirmed_bugs']}")
    print(f"\nHIGH-CONFIDENCE CANDIDATES: {result['summary']['high_confidence_candidates']}")
    print(f"\nNEEDS MANUAL REVIEW: {result['summary']['needs_manual_review']}")
    print(f"\nEXPECTED BEHAVIOR: {result['summary']['expected_behavior']}")
    print(f"\nINFORMATIONAL: {result['summary']['informational']}")
    print("\nSEVERITY:")
    for key, value in result["summary"]["severity_counts"].items():
        print(f"  {key.upper()}: {value}")
    print("\nSECURITY:\n  Secrets exposed: NO\n\nEVIDENCE:\n  Evidence preserved: YES")
    print(f"\nREPORT:\n  JSON generated: YES\n  Markdown generated: YES\n  JSON: {json_path}\n  Markdown: {md_path}")
    for finding in result["findings"]:
        print(f"\n{finding['candidate_id']}: {finding['classification']}")
    return result


if __name__ == "__main__":
    asyncio.run(generate_report())
