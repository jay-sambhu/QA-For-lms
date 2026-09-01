#!/usr/bin/env python3
"""
Final QA Report Generator

Takes the latest Gemini analysis result and produces a professional
QA report in JSON and Markdown formats for human QA testers.
"""

import json
import os
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path


from security.redactor import SecretRedactor  # noqa: F401 — re-exported for backward compat


from calculation_engine import CalculationEngine


class QAReportGenerator:
    """Generates the final QA report."""

    def __init__(self, results_dir="results", base_dir=None):
        self.results_dir = Path(results_dir)
        # Screenshot paths recorded by the crawler are relative to the repo
        # root, so existence checks are resolved against that, not the CWD.
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.test_cases_file = None
        self.test_results_file = None

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
        """Generate the final JSON report structure using CalculationEngine."""
        # Clean the raw data of any secrets
        safe_data = SecretRedactor.redact(raw_data)
        
        # Crawl results lookup
        crawl_data = None
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
                    break
                except (OSError, json.JSONDecodeError):
                    continue
                    
        # Extract interactive metrics
        interactive_data = None
        interactive_path = safe_data.get("source", {}).get("interactive_result")
        if not interactive_path:
            # Fallback to looking in results_dir by timestamp matching or finding the newest
            interactions = sorted(self.results_dir.glob("interactive_qa_*.json"), key=os.path.getmtime, reverse=True)
            if interactions:
                interactive_path = interactions[0]
                
        if interactive_path:
            candidates = [Path(interactive_path)]
            if not candidates[0].is_absolute():
                candidates.insert(0, self.base_dir / interactive_path)
            for path in candidates:
                if not path.exists():
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        interactive_data = json.load(f)
                    break
                except (OSError, json.JSONDecodeError):
                    continue

        # Load test cases if provided
        test_cases = []
        if hasattr(self, "test_cases_file") and self.test_cases_file and os.path.exists(self.test_cases_file):
            try:
                with open(self.test_cases_file, "r") as f:
                    tc_data = json.load(f)
                    test_cases = tc_data.get("test_cases", [])
            except Exception:
                pass

        # Load test results if provided
        test_results = []
        if hasattr(self, "test_results_file") and self.test_results_file and os.path.exists(self.test_results_file):
            try:
                with open(self.test_results_file, "r") as f:
                    tr_data = json.load(f)
                    test_results = tr_data.get("results", [])
                    for tc in test_cases:
                        for res in test_results:
                            if tc.get("id") == res.get("test_id"):
                                tc["status"] = res.get("status")
                                tc["actual_result"] = res.get("actual_result")
                                tc["evidence"] = res.get("evidence")
                                tc["duration_ms"] = res.get("duration_ms", 0)
            except Exception:
                pass

        # Integrate authentication test cases and findings from crawl data if present
        if crawl_data:
            auth_tc = crawl_data.get("auth_test_cases", [])
            if auth_tc:
                test_cases = list(auth_tc) + test_cases
            auth_findings = crawl_data.get("auth_findings", [])
            if auth_findings:
                existing_findings = safe_data.get("findings", [])
                safe_data["findings"] = list(auth_findings) + existing_findings

            # If authentication errored, downstream unexecuted test cases must be BLOCKED
            auth_failed = any(tc.get("status") == "errored" for tc in auth_tc)
            if auth_failed:
                for tc in test_cases:
                    if tc.get("id") != "TC-AUTH-001" and tc.get("status") not in ("passed", "failed", "errored"):
                        tc["status"] = "blocked"
                        tc["actual_result"] = "Blocked due to authentication failure."

        # Run Authoritative Calculation Engine
        start_t = safe_data.get("metadata", {}).get("start_time") or safe_data.get("start_time")
        end_t = safe_data.get("metadata", {}).get("end_time") or safe_data.get("end_time")
        canonical = CalculationEngine.calculate_canonical_metrics(
            raw_data=safe_data,
            crawl_data=crawl_data,
            interactive_data=interactive_data,
            test_cases=test_cases if test_cases else None,
            test_results=test_results if test_results else None,
            start_time=start_t,
            end_time=end_t,
        )

        timestamp = datetime.now().isoformat()
        source_summary = safe_data.get("summary", {}) or {}
        analysis_failures = source_summary.get("analysis_failures", 0) or 0

        # Construct findings list
        findings_list = []
        for finding in safe_data.get("findings", []):
            classification = finding.get("classification", "")
            candidate = finding.get("candidate", {})
            triage = candidate.get("triage", {})
            
            final_finding = {
                "id": finding.get("id", "UNKNOWN"),
                "classification": classification,
                "severity": CalculationEngine.normalize_severity(finding.get("severity")),
                "confidence": finding.get("confidence", "low"),
                "priority": triage.get("priority") or finding.get("priority") or "P3",
                "user_impact": finding.get("user_impact", triage.get("user_impact", "unknown")),
                "root_cause": triage.get("root_cause", {}),
                "regression_status": candidate.get("regression_status", "NEW"),
                "fingerprint": candidate.get("fingerprint", ""),
                "title": finding.get("title", candidate.get("title", "Untitled")),
                "page": candidate.get("affected_pages", [""])[0] if candidate.get("affected_pages") else "",
                "url": candidate.get("url", ""),
                "description": finding.get("summary", candidate.get("description", "")),
                "expected_result": finding.get("expected_result", "Not specified."),
                "actual_result": finding.get("actual_result", "Not specified."),
                "evidence": finding.get("evidence", candidate.get("evidence", {})),
                "evidence_structured": candidate.get("evidence_structured", {}),
                "reproduction": finding.get("reproduction", candidate.get("reproduction", {})),
                "recommendation": finding.get("recommended_action", ""),
                "manual_verification": finding.get("reasoning", "Needs manual verification."),
                "occurrences": candidate.get("occurrences", 1),
                "affected_pages_count": candidate.get(
                    "affected_page_count", len(candidate.get("affected_pages", []))
                ),
                "occurrence_count": candidate.get(
                    "occurrences", len(candidate.get("affected_pages", []))
                ),
                "screenshots": candidate.get("screenshots", [])
            }
            findings_list.append(final_finding)

        # Build comprehensive report maintaining backward-compatibility
        f_metrics = canonical.findings
        tc_metrics = canonical.test_cases
        c_metrics = canonical.crawl
        int_metrics = canonical.interactive

        # Construct legacy summary mapping
        potential_issues = (
            f_metrics.by_classification.get("high_confidence_candidate", 0)
            + f_metrics.by_classification.get("likely_bug", 0)
        )
        report = {
            "report_metadata": {
                "generated_at": timestamp,
                "source_report": str(source_path),
                "target": canonical.target,
                "pages_crawled": c_metrics.pages_crawled,
                "ai_analysis_failures": analysis_failures,
                "ai_analysis_degraded": bool(analysis_failures),
                "interactive_metrics": asdict(int_metrics) if interactive_data else None,
                "cross_device_metrics": asdict(c_metrics),
                "quality_score": asdict(canonical.quality_score),
            },
            "summary": {
                "total_candidates": f_metrics.total,
                "confirmed_bugs": f_metrics.by_classification.get("confirmed_bug", 0),
                "potential_issues": potential_issues,
                "manual_review": f_metrics.by_classification.get("needs_manual_review", 0),
                "informational": (
                    f_metrics.by_classification.get("informational", 0)
                    + f_metrics.by_classification.get("expected_behavior", 0)
                ),
                "ignored": f_metrics.by_classification.get("ignored", 0),
                "analysis_failures": analysis_failures,
                "regression_summary": f_metrics.by_regression,
            },
            "severity": f_metrics.by_severity,
            "findings": findings_list,
            "triage_metrics": {
                "confirmed_bug": f_metrics.by_classification.get("confirmed_bug", 0),
                "high_confidence_candidate": f_metrics.by_classification.get("high_confidence_candidate", 0),
                "needs_manual_review": f_metrics.by_classification.get("needs_manual_review", 0),
                "expected_behavior": f_metrics.by_classification.get("expected_behavior", 0),
                "informational": f_metrics.by_classification.get("informational", 0),
                "duplicate": f_metrics.by_classification.get("duplicate", 0),
                "priority": f_metrics.by_priority,
                "regression_summary": f_metrics.by_regression,
            },
            "qa_metrics": canonical.to_dict(),
        }

        if test_cases:
            report["test_cases"] = test_cases
            report["test_case_metrics"] = {
                "total": tc_metrics.total,
                "executed": tc_metrics.executed,
                "passed": tc_metrics.passed,
                "failed": tc_metrics.failed,
                "blocked": tc_metrics.blocked,
                "manual_review": tc_metrics.skipped,
                "skipped": tc_metrics.skipped,
                "errored": tc_metrics.errored,
                "pass_rate": tc_metrics.pass_rate,
                "fail_rate": tc_metrics.fail_rate,
                "skip_rate": tc_metrics.skip_rate,
                "block_rate": tc_metrics.block_rate,
                "errored_rate": tc_metrics.errored_rate,
                "duration_ms": tc_metrics.duration_ms,
            }

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
        
        if meta.get("interactive_metrics"):
            im = meta["interactive_metrics"]
            md.extend([
                "## 3. Interactive Testing\n",
                f"- **Elements discovered:** {im.get('elements_discovered', 0)}",
                f"- **Interactions attempted:** {im.get('interactions_attempted', 0)}",
                f"- **Passed:** {im.get('passed', 0)}",
                f"- **Failed:** {im.get('failed', 0)}",
                f"- **Skipped (Manual Review required):** {im.get('manual_review', 0)}\n"
            ])
            md.append("## 4. Test Coverage\n")
        else:
            md.append("## 3. Test Coverage\n")
        
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
        
        triage_metrics = json_report.get("triage_metrics", {})
        if triage_metrics:
            md.extend([
                "## 3. AI Bug Triage\n",
                "### Summary\n",
                f"- **Confirmed Bugs:** {triage_metrics.get('confirmed_bug', 0)}",
                f"- **High Confidence Candidates:** {triage_metrics.get('high_confidence_candidate', 0)}",
                f"- **Needs Manual Review:** {triage_metrics.get('needs_manual_review', 0)}",
                f"- **Expected Behavior:** {triage_metrics.get('expected_behavior', 0)}",
                f"- **Informational:** {triage_metrics.get('informational', 0)}",
                f"- **Duplicates:** {triage_metrics.get('duplicate', 0)}\n",
                "### Priority Breakdown\n"
            ])
            
            pri = triage_metrics.get("priority", {})
            for p in ["P0", "P1", "P2", "P3", "P4"]:
                md.append(f"- **{p}:** {pri.get(p, 0)}")
            md.append("")
                
            reg = triage_metrics.get("regression_summary", {})
            md.extend([
                "### Regression Analysis\n",
                f"- **New:** {reg.get('new', 0)}",
                f"- **Fixed:** {reg.get('fixed', 0)}",
                f"- **Unchanged:** {reg.get('unchanged', 0)}",
                f"- **Worsened:** {reg.get('worsened', 0)}",
                f"- **Improved:** {reg.get('improved', 0)}\n",
            ])
            
            md.append("## 4. Findings Summary\n")
        else:
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

        if triage_metrics:
            md.append("\n## 5. Detailed Findings\n")
        else:
            md.append("\n## 4. Detailed Findings\n")

        for f in json_report["findings"]:
            md.append(f"### {f['id']} — {f['title']}\n")

            # Bullets rather than bare lines: consecutive plain lines are
            # merged into a single paragraph by every Markdown renderer, which
            # collapsed all of these labels onto one line.
            md.append(f"- **Severity:** {f['severity'].upper()}")
            md.append(f"- **Confidence:** {f['confidence'].title()}")
            md.append(f"- **Classification:** {f['classification']}")
            md.append(f"- **Priority:** {f.get('priority', 'P3')}")
            md.append(f"- **Regression Status:** {f.get('regression_status', 'NEW')}")
            md.append(f"- **User Impact:** {f.get('user_impact', 'unknown').title()}")
            
            rc = f.get('root_cause', {})
            if rc:
                md.append(f"- **Root Cause Category:** {rc.get('category', 'unknown').replace('_', ' ').title()}")
                
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
            
            if rc and rc.get('summary'):
                md.append(f"**Root Cause Summary:**\n\n{rc.get('summary')}\n")

            md.append(f"**Description:**\n\n{f['description']}\n")
            md.append(f"**Expected Result:**\n\n{f.get('expected_result', 'Not specified.')}\n")
            md.append(f"**Actual Result:**\n\n{f.get('actual_result', 'Not specified.')}\n")
            
            # Reproduction
            repro = f.get("reproduction", {})
            if repro and repro.get("steps"):
                md.append("**Reproduction Steps:**\n")
                for i, step in enumerate(repro.get("steps", [])):
                    md.append(f"{i+1}. {step}")
                md.append("")

            # Evidence
            md.append("**Evidence:**\n")
            ev = f.get("evidence", {}) or {}
            has_evidence = False
            
            if ev.get("http_error"):
                req = ev["http_error"].get("request", {})
                md.append(f"- Status: {req.get('status')}")
                md.append(f"- URL: {req.get('url')}")
                has_evidence = True
            elif ev.get("http_errors"):  # Fallback to old format
                md.append("- HTTP Errors:")
                for e in ev["http_errors"][:3]:
                    md.append(f"  - {e.get('status')} {e.get('method')} {e.get('url')}")
                has_evidence = True
                
            if ev.get("console_errors"):
                md.append("- Console Errors:")
                for e in ev["console_errors"][:3]:
                    md.append(f"  - {e.get('text') or e.get('message')}")
                has_evidence = True
                
            if ev.get("network_failures"):
                md.append("- Network Failures:")
                for e in ev["network_failures"][:3]:
                    md.append(f"  - {e.get('failure')} for {e.get('url')}")
                has_evidence = True
                
            if ev.get("responsive"):
                r = ev["responsive"]
                md.append(f"- Device: {r.get('device')}")
                if r.get("viewport"):
                    md.append(f"- Viewport: {r['viewport'].get('width')}x{r['viewport'].get('height')}")
                has_evidence = True

            if not has_evidence:
                md.append("No specific event evidence recorded.")
            md.append("")
            
            # Screenshots
            screenshots = f.get("screenshots") or []
            if screenshots:
                md.append("**Screenshot:**\n")
                for s in screenshots:
                    if self._screenshot_exists(s):
                        md.append(f"- [{s}](../{s})")
                    else:
                        md.append(f"- Screenshot: Not available ({s})")
            elif ev.get("screenshot"):
                s = ev.get("screenshot")
                md.append("**Screenshot:**\n")
                if self._screenshot_exists(s):
                    md.append(f"- [{s}](../{s})")
                else:
                    md.append(f"- Screenshot: Not available ({s})")
            else:
                md.append("**Screenshot:** Not available")
            md.append("")

            md.append(f"**Recommendation:**\n\n{f['recommendation']}\n")
            md.append(f"**Manual Verification:**\n\n{f['manual_verification']}\n")
            md.append("---\n")

        if "test_case_metrics" in json_report:
            tcm = json_report["test_case_metrics"]
            pass_rate_str = f" ({tcm.get('pass_rate', 0)}%)" if tcm.get('pass_rate') is not None else ""
            md.extend([
                "## 5. Test Case Summary\n",
                f"- **Total:** {tcm['total']}",
                f"- **Executed:** {tcm['executed']}",
                f"- **Passed:** {tcm['passed']}{pass_rate_str}",
                f"- **Failed:** {tcm['failed']}",
                f"- **Manual Review:** {tcm['manual_review']}",
                f"- **Blocked:** {tcm['blocked']}\n",
                "### Test Cases\n"
            ])
            for tc in json_report.get("test_cases", []):
                md.append(f"**{tc['id']}** - {tc['title']} ({tc.get('status', 'manual_review').upper()})")
                md.append(f"- **Page:** {tc.get('source_page', 'Unknown')}")
                md.append(f"- **Expected:** {tc.get('expected_result', '')}")
                if tc.get('actual_result'):
                    md.append(f"- **Actual:** {tc['actual_result']}")
                md.append("")

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
