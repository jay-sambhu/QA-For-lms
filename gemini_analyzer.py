#!/usr/bin/env python3
"""Conservative Gemini analysis of deterministic QA root-cause candidates."""

import asyncio
import json
import os
import re
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

MODULE_DIR = Path(__file__).resolve().parent

# Ordered tuples, not sets: iteration order over a set of strings varies with
# PYTHONHASHSEED, which made the JSON key order of the count dictionaries
# change between runs and broke byte-for-byte report comparisons.
CLASSIFICATION_ORDER = (
    "confirmed_bug",
    "high_confidence_candidate",
    "needs_manual_review",
    "expected_behavior",
    "informational",
)
SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
CONFIDENCE_ORDER = ("high", "medium", "low")
REQUIRED_FIELD_ORDER = (
    "classification",
    "severity",
    "confidence",
    "title",
    "summary",
    "reasoning",
    "user_impact",
    "recommended_action",
    "evidence_used",
)

# Kept as sets for fast membership tests, derived from the ordered tuples above
# so the two can never drift apart.
CLASSIFICATIONS = set(CLASSIFICATION_ORDER)
SEVERITIES = set(SEVERITY_ORDER)
CONFIDENCES = set(CONFIDENCE_ORDER)
REQUIRED_FIELDS = set(REQUIRED_FIELD_ORDER)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

# Seconds to wait before the single retry of a failed model call.
RETRY_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 120


class GeminiQAAnalyzer:
    """Analyze grouped candidates while keeping deterministic evidence authoritative."""

    def __init__(self, api_key=None, model_client=None, model_name="gemini-3-flash-preview"):
        # Load the .env sitting next to this module rather than one relative to
        # the current working directory, so the key is found no matter where
        # the pipeline is invoked from.
        load_dotenv(dotenv_path=MODULE_DIR / ".env")
        self.api_key = api_key if api_key is not None else os.getenv("GOOGLE_API_KEY")
        self.model_client = model_client
        self.model_name = model_name

    @staticmethod
    def find_latest_findings(results_dir="results"):
        results_path = Path(results_dir)
        if not results_path.exists():
            return None
        # By mtime, not name: run ids may be UUIDs (from the API) rather than
        # timestamps, so filename order is not chronological order. The name is
        # the tiebreak because mtime granularity is coarse enough that two files
        # written in the same tick would otherwise order arbitrarily.
        files = sorted(
            results_path.glob("qa_findings_*.json"),
            key=lambda path: (path.stat().st_mtime, path.name),
            reverse=True,
        )
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

        for pattern, replacement in GeminiQAAnalyzer.REDACTION_PATTERNS:
            value = pattern.sub(replacement, value)
        return value

    # Compiled once at class creation rather than rebuilt on every call.
    REDACTION_PATTERNS = [
        (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;\"']+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(bearer\s+)[^\s,;\"']+"), r"\1[REDACTED]"),
        # JWTs, which often appear in console errors and request URLs.
        (
            re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{10,}"),
            "[REDACTED_JWT]",
        ),
        # Named credentials in JSON, headers, or query strings. `key` and
        # `apikey` are included because Google-style URLs use a bare `?key=`,
        # which the previous pattern list did not match at all.
        #
        # The lookbehind is load-bearing: without it, short names matched the
        # tail of ordinary words, so `?monkey=1`, `?sortkey=name` and
        # `?hotkey=x` were rewritten to `?mon[REDACTED]` and friends -- silently
        # corrupting the URLs a QA reader needs in order to reproduce the bug.
        # It rejects a preceding letter or digit but allows `_`, `-` and
        # punctuation, so `user_session_id=` and `X-API-Key:` still redact.
        #
        # The `["']?` *before* the separator matches a JSON key's closing quote.
        # Without it `{"access_token": "secret"}` did not match at all, so
        # credentials inside JSON request bodies and console errors -- the most
        # likely place for them to appear -- were passed to the model verbatim.
        (
            re.compile(
                r"(?i)(?<![A-Za-z0-9])"
                r"((?:api[_ -]?key|apikey|access[_ -]?token|refresh[_ -]?token"
                r"|id[_ -]?token|client[_ -]?secret|session[_ -]?id|token|key"
                r"|password|passwd|pwd|secret|cookie|auth)"
                r"[\"']?\s*[:=]\s*[\"']?)[^\s,;\"'&]+"
            ),
            r"\1[REDACTED]",
        ),
    ]

    @classmethod
    def compact_evidence(cls, candidate, target=""):
        evidence = candidate.get("evidence") or {}
        affected = candidate.get("affected_pages") or []
        screenshots = candidate.get("screenshots") or []

        # Prefer the explicit page->screenshot pairing produced by the bug
        # detector. Zipping two separately de-duplicated lists silently paired
        # the wrong screenshot with the wrong page whenever a page had none.
        pairs = candidate.get("page_screenshots")
        if pairs:
            paired = [
                (item.get("page", ""), item.get("screenshot", ""))
                for item in pairs
            ]
        else:
            paired = list(zip(affected, screenshots))

        screenshot_evidence = []
        for page, path in paired:
            exists = bool(path) and Path(path).exists()
            screenshot_evidence.append({"page": page, "path": path, "available": exists})

        package = {
            "target": target,
            "candidate_id": candidate.get("id"),
            "type": candidate.get("type"),
            "url": candidate.get("url"),
            "status": candidate.get("status"),
            "method": candidate.get("method"),
            "resource_type": candidate.get("resource_type"),
            "occurrences": candidate.get("occurrences", 0),
            "affected_pages": affected,
            "affected_page_count": candidate.get("affected_page_count", len(affected)),
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
            + ", ".join(CLASSIFICATION_ORDER)
            + ". Severity must be one of: "
            + ", ".join(SEVERITY_ORDER)
            + "; confidence must be one of: "
            + ", ".join(CONFIDENCE_ORDER)
            + ". Do not invent backend behavior, credentials, responses, screenshots, or user impact. "
            "A 401/403 is not automatically a bug and usually needs manual review unless broken behavior "
            "is evidenced. A first-party 5xx is usually a high-confidence candidate. ERR_ABORTED and "
            "third-party analytics are normally informational. Use screenshots only when available and "
            "never claim visual observations when screenshot analysis is unavailable. Required fields: "
            + json.dumps(list(REQUIRED_FIELD_ORDER))
            + ". Make sure 'evidence_used' is a JSON array of strings."
            + "\nEvidence:\n"
            + json.dumps(evidence, indent=2, ensure_ascii=False)
        )

    async def _call_model(self, prompt):
        if self.model_client is not None:
            if hasattr(self.model_client, "ainvoke"):
                response = await self.model_client.ainvoke(prompt)
            elif hasattr(self.model_client, "invoke"):
                response = self.model_client.invoke(prompt)
            elif callable(self.model_client):
                response = self.model_client(prompt)
                if hasattr(response, "__await__"):
                    response = await response
            else:
                raise TypeError("Unsupported Gemini mock client")
            return getattr(response, "content", response)

        if not self.api_key:
            raise RuntimeError("Gemini API key unavailable")

        url = f"{GEMINI_ENDPOINT}/{self.model_name}:generateContent"

        # The key goes in a header, not the query string. A key in the URL is
        # echoed into exception messages, proxy logs, and stack traces.
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0},
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        def fetch():
            try:
                with urllib.request.urlopen(
                    request, timeout=REQUEST_TIMEOUT_SECONDS
                ) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                # Surface the status code so the caller can detect 429/quota.
                detail = ""
                try:
                    detail = error.read().decode("utf-8", "replace")[:500]
                except Exception:
                    pass
                raise RuntimeError(
                    f"Gemini API returned HTTP {error.code}: {detail}"
                ) from None

        try:
            response_data = await asyncio.to_thread(fetch)
        except Exception as error:
            # Redact before re-raising: the message ends up in the report.
            raise RuntimeError(
                f"Gemini API request failed: {self._redact(str(error))}"
            ) from None

        try:
            candidates = response_data["candidates"]
            if not candidates:
                # An empty candidate list usually means the prompt was blocked.
                feedback = response_data.get("promptFeedback", {})
                raise RuntimeError(f"Gemini returned no candidates: {feedback}")
            parts = candidates[0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(
                f"Unexpected Gemini response shape: {error}"
            ) from None

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
            raise ValueError(f"Invalid classification: {parsed['classification']!r}")
        if parsed["severity"] not in SEVERITIES:
            raise ValueError(f"Invalid severity: {parsed['severity']!r}")
        if parsed["confidence"] not in CONFIDENCES:
            raise ValueError(f"Invalid confidence: {parsed['confidence']!r}")
        if not isinstance(parsed.get("evidence_used"), list):
            parsed["evidence_used"] = (
                [str(parsed.get("evidence_used", ""))] if parsed.get("evidence_used") else []
            )
        # Fixed field order so the emitted JSON is byte-stable across runs.
        return {field: cls._redact(parsed[field]) for field in REQUIRED_FIELD_ORDER}

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
            # Distinguishes "the model deliberately asked for manual review"
            # from "the model call failed", which the summary previously
            # conflated into a single error list.
            "analysis_failed": True,
        }
        if raw_response:
            result["raw_response"] = cls._redact(str(raw_response))
        return result

    async def analyze_candidate(self, candidate, target=""):
        prompt = self.build_prompt(candidate, target)
        if self.model_client is None and not self.api_key:
            return self.fallback("Gemini API key unavailable; manual review required.")
        try:
            raw = await self._call_model(prompt)
            return self.validate_response(raw)
        except Exception as error:
            message = str(error)
            # Quota errors will not succeed on an immediate retry.
            if "429" in message or "quota" in message.lower():
                return self.fallback("Gemini quota limit reached; manual review required.")

            # Back off briefly before the single retry so a transient rate
            # limit or network blip has time to clear.
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            try:
                raw = await self._call_model(prompt)
                return self.validate_response(raw)
            except Exception as retry_error:
                return self.fallback(
                    "Gemini analysis failed; manual review required.", str(retry_error)
                )

    async def analyze(self, findings_data):
        candidates = findings_data.get("root_cause_candidates") or []
        target = findings_data.get("target", "")
        findings, errors = [], []
        for index, candidate in enumerate(candidates, 1):
            analysis = await self.analyze_candidate(candidate, target)

            # Only genuine failures belong in `errors`. A model that returns a
            # well-formed `needs_manual_review` verdict is working correctly.
            if analysis.pop("analysis_failed", False):
                errors.append(
                    {"candidate_id": candidate.get("id"), "error": analysis["reasoning"]}
                )

            finding = {
                "id": f"AI-BUG-{index:03d}",
                "candidate_id": candidate.get("id"),
                **analysis,
                "candidate": deepcopy(candidate),
            }
            findings.append(finding)

        classification_counts = {key: 0 for key in CLASSIFICATION_ORDER}
        severity_counts = {key: 0 for key in SEVERITY_ORDER}
        confidence_counts = {key: 0 for key in CONFIDENCE_ORDER}
        for finding in findings:
            # `.get` guards against a future classification/severity being
            # added to the prompt but not to the ordered tuples.
            if finding["classification"] in classification_counts:
                classification_counts[finding["classification"]] += 1
            if finding["severity"] in severity_counts:
                severity_counts[finding["severity"]] += 1
            if finding["confidence"] in confidence_counts:
                confidence_counts[finding["confidence"]] += 1
        return {
            "target": target,
            "source": {
                "crawl_result": findings_data.get("crawl_source", ""),
                "qa_findings": findings_data.get("source_file", ""),
            },
            "summary": {
                "total_candidates": len(findings),
                "confirmed_bugs": classification_counts["confirmed_bug"],
                "high_confidence_candidates": classification_counts["high_confidence_candidate"],
                "needs_manual_review": classification_counts["needs_manual_review"],
                "expected_behavior": classification_counts["expected_behavior"],
                "informational": classification_counts["informational"],
                "analysis_failures": len(errors),
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


async def generate_report(findings_file=None, results_dir="results", run_id=None):
    """
    Run the Gemini analysis stage.

    Args:
        findings_file: Explicit path to a qa_findings_*.json file. When omitted
            the newest file in `results_dir` is used, which is only safe for
            single-run/CLI usage.
        results_dir: Directory to read from and write to.
        run_id: Suffix for output filenames. Defaults to a timestamp.
    """
    path = (
        Path(findings_file)
        if findings_file
        else GeminiQAAnalyzer.find_latest_findings(results_dir)
    )
    if path is None:
        print(f"No QA findings file found under {results_dir}/qa_findings_*.json")
        return None

    data = GeminiQAAnalyzer.load_findings(path)
    data["source_file"] = str(path)
    analyzer = GeminiQAAnalyzer()
    result = await analyzer.analyze(data)

    results_path = Path(results_dir)
    results_path.mkdir(parents=True, exist_ok=True)

    suffix = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = results_path / f"gemini_qa_report_{suffix}.json"
    md_path = results_path / f"gemini_qa_report_{suffix}.md"

    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(analyzer.render_markdown(result), encoding="utf-8")

    summary = result["summary"]
    print("\n" + "=" * 60 + "\nGEMINI QA ANALYZER VERIFICATION\n" + "=" * 60)
    print(f"\nRAW CANDIDATES: {summary['total_candidates']}")
    print(f"\nCONFIRMED BUGS: {summary['confirmed_bugs']}")
    print(f"\nHIGH-CONFIDENCE CANDIDATES: {summary['high_confidence_candidates']}")
    print(f"\nNEEDS MANUAL REVIEW: {summary['needs_manual_review']}")
    print(f"\nEXPECTED BEHAVIOR: {summary['expected_behavior']}")
    print(f"\nINFORMATIONAL: {summary['informational']}")
    print(f"\nANALYSIS FAILURES: {summary['analysis_failures']}")
    print("\nSEVERITY:")
    for key, value in summary["severity_counts"].items():
        print(f"  {key.upper()}: {value}")
    print("\nSECURITY:\n  Secrets redacted: YES\n\nEVIDENCE:\n  Evidence preserved: YES")
    print(
        f"\nREPORT:\n  JSON generated: YES\n  Markdown generated: YES"
        f"\n  JSON: {json_path}\n  Markdown: {md_path}"
    )
    for finding in result["findings"]:
        print(f"\n{finding['candidate_id']}: {finding['classification']}")

    # Surface the paths so callers do not have to re-glob the directory.
    result["json_path"] = str(json_path)
    result["md_path"] = str(md_path)

    return result


if __name__ == "__main__":
    asyncio.run(generate_report())
