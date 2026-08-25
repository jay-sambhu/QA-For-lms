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
        # API keys, tokens, passwords, secrets in JSON or URLs or Headers
        (re.compile(r"(?i)((?:api[_ -]?key|token|password|passwd|secret|cookie|private[_ -]?key)\s*[:=]\s*[\"']?)[^\s,;\"'&]+"), r"\1[REDACTED]"),
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

    def __init__(self, results_dir="results"):
        self.results_dir = Path(results_dir)

    def find_latest_gemini_report(self):
        """Find the latest gemini_qa_report_*.json in the results directory."""
        if not self.results_dir.exists():
            return None
            
        reports = sorted(self.results_dir.glob("gemini_qa_report_*.json"), reverse=True)
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
        if crawl_result_path and Path(crawl_result_path).exists():
            try:
                with open(crawl_result_path, "r", encoding="utf-8") as f:
                    crawl_data = json.load(f)
                    pages_crawled = crawl_data.get("pages_crawled", 0)
            except Exception:
                pass
        
        timestamp = datetime.now().isoformat()
        
        report = {
            "report_metadata": {
                "generated_at": timestamp,
                "source_report": str(source_path),
                "target": safe_data.get("target", "Unknown"),
                "pages_crawled": pages_crawled
            },
            "summary": {
                "total_candidates": 0,
                "confirmed_bugs": 0,
                "potential_issues": 0,
                "manual_review": 0,
                "informational": 0,
                "ignored": 0
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
                "affected_pages_count": candidate.get("occurrences", len(candidate.get("affected_pages", []))),
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
            page = f['page'] if len(f['page']) <= 50 else f"{f['page'][:47]}..."
            url = f['url'] if len(f['url']) <= 50 else f"{f['url'][:47]}..."
            md.append(f"| {f['id']} | {f['severity'].upper()} | {f['classification']} | {f['confidence']} | {page} | {url} |")
            
        md.append("\n## 4. Detailed Findings\n")
        
        for f in json_report["findings"]:
            md.append(f"### {f['id']} — {f['title']}\n")
            md.append(f"**Severity:** {f['severity'].upper()}")
            md.append(f"**Confidence:** {f['confidence'].title()}")
            md.append(f"**Classification:** {f['classification']}\n")
            
            md.append(f"**Page:** {f['page']}")
            if f.get('affected_pages_count', 1) > 1:
                md.append(f"*(and {f['affected_pages_count'] - 1} other affected pages)*")
            md.append(f"**URL:** {f['url']}\n")
            
            md.append(f"**Description:**\n{f['description']}\n")
            
            # Screenshots
            if f.get("screenshots"):
                md.append("**Screenshot:**")
                for s in f["screenshots"]:
                    # Check if screenshot actually exists
                    if Path(s).exists():
                        md.append(f"[{s}](../{s})")
                    else:
                        md.append("Screenshot: Not available")
            else:
                md.append("**Screenshot:** Not available")
            md.append("")
                
            # Evidence
            md.append("**Evidence:**")
            ev = f.get("evidence", {})
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
                
            md.append(f"**Recommendation:**\n{f['recommendation']}\n")
            md.append(f"**Manual Verification:**\n{f['manual_verification']}\n")
            md.append("---\n")
            
        return "\n".join(md)

    def generate(self, source_path=None):
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
        
        self.results_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        final_json_path = self.results_dir / f"final_qa_report_{timestamp}.json"
        final_md_path = self.results_dir / f"final_qa_report_{timestamp}.md"
        
        with open(final_json_path, "w", encoding="utf-8") as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)
            
        with open(final_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        summary = json_report["summary"]
        sev = json_report["severity"]
        
        print("\n============================================================")
        print("FINAL QA REPORT")
        print("============================================================")
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
            "json_path": final_json_path,
            "md_path": final_md_path,
            "json_report": json_report
        }

if __name__ == "__main__":
    generator = QAReportGenerator()
    generator.generate()
