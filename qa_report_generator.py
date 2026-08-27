#!/usr/bin/env python3
"""
Final QA Report Generator

Takes the latest Gemini analysis result and produces a professional
QA report in JSON and Markdown formats for human QA testers.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path


class SecretRedactor:
    """Deterministic secret-redaction layer."""
    
    # Common patterns for secrets
    PATTERNS = [
        # Bearer/Authorization tokens
        (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;\"]+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(bearer\s+)[^\s,;\"]+"), r"\1[REDACTED]"),
        # JWT-like tokens (header.payload.signature)
        (re.compile(r"eyJ[a-zA-Z0-9_-]{5,}\.eyJ[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{10,}"), "[REDACTED_JWT]"),
        # API keys, tokens, passwords, secrets in JSON or URLs or Headers.
        # The lookbehind stops short names from matching the tail of an ordinary
        # word: without it `?monkey=1` and `?sortkey=name` were rewritten to
        # `?mon[REDACTED]`, corrupting URLs the reader needs to reproduce the
        # bug. Letters and digits are rejected before the name; `_`, `-` and
        # punctuation are allowed, so `user_session_id=` and `X-API-Key:` still
        # redact. The `["']?` before the separator matches a JSON key's closing
        # quote -- without it `{"token": "secret"}` was never redacted at all.
        (re.compile(r"(?i)(?<![A-Za-z0-9])((?:api[_ -]?key|token|password|passwd|secret|cookie|private[_ -]?key)[\"']?\s*[:=]\s*[\"']?)[^\s,;\"'&]+"), r"\1[REDACTED]"),
    ]

    @classmethod
    def redact(cls, data):
        """Recursively redact secrets from a data structure."""
        if isinstance(data, dict):
            return {k: cls.redact(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.redact(item) for item in data]
        elif isinstance(data, str):
            redacted_str = data
            for pattern, replacement in cls.PATTERNS:
                redacted_str = pattern.sub(replacement, redacted_str)
            return redacted_str
        else:
            return data


class QAReportGenerator:
    """Generates the final QA report."""

    def __init__(self, results_dir="results", base_dir=None):
        self.results_dir = Path(results_dir)
        # Screenshot paths recorded by the crawler are relative to the repo
        # root, so existence checks are resolved against that, not the CWD.
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()

    def _screenshot_exists(self, screenshot):
        """Check whether a recorded screenshot path resolves to a real file."""
        if not screenshot:
            return False

        path = Path(screenshot)
        if path.is_absolute():
            return path.exists()

        return (self.base_dir / path).exists() or path.exists()

    def find_latest_gemini_report(self):
        """Find the latest gemini_qa_report_*.json in the results directory."""
        if not self.results_dir.exists():
            return None
            
        # By mtime, not name: run ids may be UUIDs (from the API) rather than
        # timestamps, so filename order is not chronological order. The name is
        # the tiebreak because mtime granularity is coarse enough that two files
        # written in the same tick would otherwise order arbitrarily.
        reports = sorted(
            self.results_dir.glob("gemini_qa_report_*.json"),
            key=lambda path: (path.stat().st_mtime, path.name),
            reverse=True,
        )
        return reports[0] if reports else None

    def generate_json_report(self, source_path, raw_data):
        """Generate the final JSON report structure."""
        # Clean the raw data of any secrets
        safe_data = SecretRedactor.redact(raw_data)
        
        # We need to know how many pages were crawled. 
        # The gemini report doesn't directly store pages_crawled, 
        # so we will look for crawl_result if possible, or leave it as unknown if we can't easily find it.
        # But wait, we can try to read it from crawl_result if it exists.
        pages_crawled = 0
        crawl_result_path = safe_data.get("source", {}).get("crawl_result")
        if crawl_result_path:
            candidates = [Path(crawl_result_path)]
            if not candidates[0].is_absolute():
                candidates.insert(0, self.base_dir / crawl_result_path)
            for path in candidates:
                if not path.exists():
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        crawl_data = json.load(f)
                        pages_crawled = crawl_data.get("pages_crawled", 0)
                    break
                except (OSError, json.JSONDecodeError):
                    continue
        
        timestamp = datetime.now().isoformat()

        # Stage 3 records how many candidates the model failed to analyse. That
        # number has to reach the reader: without it a scan where every Gemini
        # call failed looks identical to a scan where the model genuinely
        # returned "needs manual review" for everything.
        source_summary = safe_data.get("summary", {}) or {}
        analysis_failures = source_summary.get("analysis_failures", 0) or 0

        report = {
            "report_metadata": {
                "generated_at": timestamp,
                "source_report": str(source_path),
                "target": safe_data.get("target", "Unknown"),
                "pages_crawled": pages_crawled,
                "ai_analysis_failures": analysis_failures,
                "ai_analysis_degraded": bool(analysis_failures),
            },
            "summary": {
                "total_candidates": 0,
                "confirmed_bugs": 0,
                "potential_issues": 0,
                "manual_review": 0,
                "informational": 0,
                "ignored": 0,
                "analysis_failures": analysis_failures
            },
            "severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0
            },
            "findings": []
        }

        for finding in safe_data.get("findings", []):
            classification = finding.get("classification", "")
            
            # Update classification summary
            report["summary"]["total_candidates"] += 1
            if classification == "confirmed_bug":
                report["summary"]["confirmed_bugs"] += 1
            elif classification == "high_confidence_candidate" or classification == "likely_bug":
                report["summary"]["potential_issues"] += 1
            elif classification == "needs_manual_review":
                report["summary"]["manual_review"] += 1
            elif classification in ["expected_behavior", "informational"]:
                report["summary"]["informational"] += 1
            else:
                report["summary"]["ignored"] += 1
                
            # Update severity summary
            severity = finding.get("severity", "info").lower()
            if severity in report["severity"]:
                report["severity"][severity] += 1
            else:
                report["severity"]["info"] += 1
                
            candidate = finding.get("candidate", {})
            
            # Construct final finding
            final_finding = {
                "id": finding.get("id", "UNKNOWN"),
                "classification": classification,
                "severity": severity,
                "confidence": finding.get("confidence", "low"),
                "title": finding.get("title", candidate.get("title", "Untitled")),
                "page": candidate.get("affected_pages", [""])[0] if candidate.get("affected_pages") else "",
                "url": candidate.get("url", ""),
                "description": finding.get("summary", candidate.get("description", "")),
                "evidence": candidate.get("evidence", {}),
                "recommendation": finding.get("recommended_action", ""),
                "manual_verification": finding.get("reasoning", "Needs manual verification."),
                # Page count, not event count. Stage 2 redefined `occurrences`
                # to mean raw events (one page can fail an endpoint 30 times)
                # and moved the page count to `affected_page_count`, so reading
                # `occurrences` here reported "affects 30 pages" for a single
                # page. Both numbers are now carried explicitly.
                "affected_pages_count": candidate.get(
                    "affected_page_count", len(candidate.get("affected_pages", []))
                ),
                "occurrence_count": candidate.get(
                    "occurrences", len(candidate.get("affected_pages", []))
                ),
                "screenshots": candidate.get("screenshots", [])
            }
            
            report["findings"].append(final_finding)
            
        return report

    def generate_markdown_report(self, json_report):
        """Generate the final Markdown report from the JSON report."""
        meta = json_report["report_metadata"]
        summary = json_report["summary"]
        sev = json_report["severity"]
        
        md = [
            "# QA Test Report\n",
        ]

        # A warning banner, not a buried counter: a report built on failed AI
        # analysis must not read like a clean result.
        if meta.get("ai_analysis_degraded"):
            md.append(
                f"> **Warning — AI analysis was incomplete.** "
                f"{meta['ai_analysis_failures']} candidate(s) could not be analysed by "
                f"Gemini, so their classification, severity and recommendation below are "
                f"deterministic fallbacks rather than AI verdicts. Re-run the scan once "
                f"the model is reachable.\n"
            )

        md += [
            "## 1. Executive Summary\n",
            f"- **Target website:** {meta['target']}",
            f"- **Test date/time:** {meta['generated_at']}",
            f"- **Pages crawled:** {meta['pages_crawled']}",
            f"- **Total findings:** {summary['total_candidates']}",
            f"- **High priority issues:** {sev['high'] + sev['critical']}",
            f"- **Medium priority issues:** {sev['medium']}",
            f"- **Low priority issues:** {sev['low']}",
            f"- **Informational findings:** {summary['informational']}",
            f"- **Manual review candidates:** {summary['manual_review']}\n",
            "## 2. Test Coverage\n",
            f"- **Number of pages crawled:** {meta['pages_crawled']}"
        ]
        
        # Calculate other coverage stats from findings
        http_errors = 0
        console_errors = 0
        network_failures = 0
        screenshots = set()
        
        for finding in json_report["findings"]:
            ev = finding.get("evidence", {})
            http_errors += len(ev.get("http_errors", []))
            console_errors += len(ev.get("console_errors", []))
            network_failures += len(ev.get("network_failures", []))
            for s in finding.get("screenshots", []):
                screenshots.add(s)
                
        md.extend([
            f"- **Screenshots referenced in findings:** {len(screenshots)}",
            f"- **HTTP errors collected (in findings):** {http_errors}",
            f"- **Console errors collected (in findings):** {console_errors}",
            f"- **Network failures collected (in findings):** {network_failures}",
            f"- **Root-cause candidates:** {summary['total_candidates']}",
            f"- **Gemini-analyzed candidates:** {summary['total_candidates']}\n"
        ])
        
        md.append("## 3. Findings Summary\n")
        md.append("| ID | Severity | Classification | Confidence | Page | URL |")
        md.append("|----|----------|----------------|------------|------|-----|")

        for f in json_report["findings"]:
            page = self._truncate(f.get("page"))
            url = self._truncate(f.get("url"))
            md.append(
                f"| {f['id']} | {f['severity'].upper()} | {f['classification']} "
                f"| {f['confidence']} | {page} | {url} |"
            )

        md.append("\n## 4. Detailed Findings\n")

        for f in json_report["findings"]:
            md.append(f"### {f['id']} — {f['title']}\n")

            # Bullets rather than bare lines: consecutive plain lines are
            # merged into a single paragraph by every Markdown renderer, which
            # collapsed all of these labels onto one line.
            md.append(f"- **Severity:** {f['severity'].upper()}")
            md.append(f"- **Confidence:** {f['confidence'].title()}")
            md.append(f"- **Classification:** {f['classification']}")
            md.append(f"- **Page:** {f.get('page') or 'N/A'}")

            if f.get('affected_pages_count', 1) > 1:
                md.append(
                    f"- **Also affects:** {f['affected_pages_count'] - 1} other page(s)"
                )

            occurrences = f.get('occurrence_count', 0)
            if occurrences > f.get('affected_pages_count', 0):
                md.append(f"- **Total occurrences:** {occurrences}")

            md.append(f"- **URL:** {f.get('url') or 'N/A'}")
            md.append("")

            md.append(f"**Description:**\n\n{f['description']}\n")

            # Screenshots
            screenshots = f.get("screenshots") or []
            if screenshots:
                md.append("**Screenshot:**\n")
                for s in screenshots:
                    if self._screenshot_exists(s):
                        md.append(f"- [{s}](../{s})")
                    else:
                        md.append(f"- Screenshot: Not available ({s})")
            else:
                md.append("**Screenshot:** Not available")
            md.append("")

            # Evidence
            md.append("**Evidence:**\n")
            ev = f.get("evidence", {}) or {}
            has_evidence = False
            if ev.get("http_errors"):
                md.append("- HTTP Errors:")
                for e in ev["http_errors"][:3]:
                    md.append(f"  - {e.get('status')} {e.get('method')} {e.get('url')}")
                has_evidence = True
            if ev.get("console_errors"):
                md.append("- Console Errors:")
                for e in ev["console_errors"][:3]:
                    md.append(f"  - {e.get('text')}")
                has_evidence = True
            if ev.get("network_failures"):
                md.append("- Network Failures:")
                for e in ev["network_failures"][:3]:
                    md.append(f"  - {e.get('failure')} for {e.get('url')}")
                has_evidence = True

            if not has_evidence:
                md.append("No specific event evidence recorded.")
            md.append("")

            md.append(f"**Recommendation:**\n\n{f['recommendation']}\n")
            md.append(f"**Manual Verification:**\n\n{f['manual_verification']}\n")
            md.append("---\n")

        return "\n".join(md)

    @staticmethod
    def _truncate(value, limit=50):
        """Truncate a table cell value, tolerating None."""
        text = str(value or "")
        if not text:
            return "N/A"
        if len(text) > limit:
            text = f"{text[:limit - 3]}..."
        # A literal pipe would split the Markdown table cell.
        return text.replace("|", "\\|")

    def generate(self, source_path=None, run_id=None):
        """Run the full generator pipeline."""
        if source_path is None:
            source_path = self.find_latest_gemini_report()

        if not source_path:
            print("ERROR: No gemini_qa_report found. Exit gracefully.")
            return None

        print(f"Loading source report: {source_path}")

        with open(source_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        json_report = self.generate_json_report(source_path, raw_data)
        markdown_content = self.generate_markdown_report(json_report)

        # parents=True: results_dir may be nested and not yet created.
        self.results_dir.mkdir(parents=True, exist_ok=True)
        suffix = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        final_json_path = self.results_dir / f"final_qa_report_{suffix}.json"
        final_md_path = self.results_dir / f"final_qa_report_{suffix}.md"

        with open(final_json_path, "w", encoding="utf-8") as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)

        with open(final_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        summary = json_report["summary"]
        sev = json_report["severity"]
        
        print("\n============================================================")
        print("FINAL QA REPORT")
        print("============================================================")
        if json_report["report_metadata"].get("ai_analysis_degraded"):
            print(
                f"\nWARNING: AI analysis incomplete — "
                f"{json_report['report_metadata']['ai_analysis_failures']} candidate(s) "
                f"fell back to deterministic classification.\n"
            )
        print(f"\nSource:\n{source_path}\n")
        print(f"Target:\n{json_report['report_metadata']['target']}\n")
        print(f"Pages:\n{json_report['report_metadata']['pages_crawled']}\n")
        print(f"Findings:\n{summary['total_candidates']}\n")
        print(f"Confirmed bugs:\n{summary['confirmed_bugs']}\n")
        print(f"Potential issues:\n{summary['potential_issues']}\n")
        print(f"Manual review:\n{summary['manual_review']}\n")
        print(f"Informational:\n{summary['informational']}\n")
        print(f"Ignored:\n{summary['ignored']}\n")
        print("Severity:")
        print(f"CRITICAL: {sev['critical']}")
        print(f"HIGH:     {sev['high']}")
        print(f"MEDIUM:   {sev['medium']}")
        print(f"LOW:      {sev['low']}")
        print(f"INFO:     {sev['info']}\n")
        print("Reports:\n")
        print(f"{final_json_path}")
        print(f"{final_md_path}\n")
        
        return {
            # Strings, not Path objects: callers embed these in stdout that the
            # API parses, and in JSON payloads that must be serializable.
            "json_path": str(final_json_path),
            "md_path": str(final_md_path),
            "json_report": json_report
        }

if __name__ == "__main__":
    generator = QAReportGenerator()
    generator.generate()
