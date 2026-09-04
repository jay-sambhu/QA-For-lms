#!/usr/bin/env python3
"""End-to-end AI QA Agent pipeline.

Stages communicate by explicit file paths rather than by globbing for the
newest file in results/. That matters because the API can run several scans
concurrently, and "newest file on disk" is not a per-scan identity: two
overlapping scans would read each other's output.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

from crawler.crawler import WebsiteCrawler
from core.bug_detector import generate_qa_findings
from core.gemini_analyzer import generate_report
from core.qa_report_generator import QAReportGenerator

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


async def run_pipeline(url, max_pages=30, auth_token=None, run_id=None, output_dir=None,
                       login_url=None, username=None, password=None, **kwargs):
    """Run all four stages, returning the final report dict or None."""
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.abspath(output_dir) if output_dir else ROOT_DIR
    results_dir = os.path.join(base_dir, "results")

    print(f"Starting AI QA Pipeline for: {url}")
    print(f"Run ID: {run_id}")
    print("=" * 60)

    def report_progress(stage, percent, message, **kwargs):
        progress_file = os.path.join(results_dir, f"progress_{run_id}.json")
        try:
            data = {
                "stage": stage,
                "percent": max(0, min(100, int(percent))),
                "message": message,
                **kwargs
            }
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    report_progress("crawling", 5, "Initializing multi-device crawler...")

    print("\n[Stage 1] Crawling website...")
    crawler = WebsiteCrawler(
        url,
        max_pages=max_pages,
        auth_token=auth_token,
        output_dir=base_dir,
        run_id=run_id,
        progress_cb=lambda pct, msg, **kw: report_progress("crawling", pct, msg, **kw),
        login_url=login_url,
        username=username,
        password=password,
    )
    crawl_result = await crawler.crawl()
    crawl_file = crawl_result.get("output_file")
    if not crawl_file:
        print("ERROR: Stage 1 produced no crawl file.")
        return None

    # Zero pages loaded is a failed scan, not a clean one. Continuing would
    # produce an empty report and print "completed successfully", so the API
    # would mark the scan completed and the UI would tell the user their site
    # looks healthy -- when in fact the site was never reached (bad DNS, target
    # down, wrong URL, blocked by a WAF).
    if not crawl_result.get("pages_crawled"):
        attempted = crawl_result.get("pages_attempted", 0)
        print(
            f"ERROR: Stage 1 loaded 0 pages successfully "
            f"({attempted} attempted). The target may be unreachable, "
            f"blocking automated browsers, or the URL may be wrong. "
            f"Not generating a report from an empty crawl."
        )
        for page in crawl_result.get("pages", [])[:3]:
            if page.get("error"):
                print(f"  {page.get('url')}: {page['error']}")
        return None

    report_progress("interactive_testing", 30, "Running deterministic interactive tests...")

    print("\n[Stage 2] Running deterministic interactive testing...")
    from core.interactive_tester import InteractiveTester
    tester = InteractiveTester(
        crawl_result,
        max_interactions_per_page=3,
        output_dir=base_dir,
        run_id=run_id,
        progress_cb=lambda pct, msg: report_progress("interactive_testing", 30 + int(pct * 0.3), msg)
    )
    interactive_result = await tester.run()
    interactive_file = interactive_result.get("output_file")
    if not interactive_file:
        print("ERROR: Stage 2 produced no interactive test file.")
        # Proceed anyway so we don't drop crawl findings
        interactive_file = None

    report_progress("bug_detection", 60, "Running deterministic bug detector...")

    print("\n[Stage 3] Running deterministic bug detector...")
    findings = generate_qa_findings(
        crawl_file=crawl_file,
        results_dir=results_dir,
        run_id=run_id,
        interactive_file=interactive_file
    )
    if not findings:
        print("ERROR: Stage 3 produced no findings file.")
        return None

    report_progress("test_generation", 65, "Generating test cases...")
    print("\n[Stage 3.5] Generating AI Test Cases...")
    from core.test_case_generator import TestCaseGenerator
    tc_generator = TestCaseGenerator(crawl_file=crawl_file, output_dir=base_dir)
    test_cases_file = await tc_generator.generate()
    
    test_results_file = None
    if test_cases_file:
        print("\n[Stage 3.6] Executing Safe Test Cases...")
        from core.test_case_executor import TestCaseExecutor
        tc_executor = TestCaseExecutor(test_cases_file=test_cases_file, qa_findings_file=findings["output_file"], output_dir=base_dir)
        test_results_file = await tc_executor.execute()

    report_progress("evidence_engine", 70, "Generating deterministic evidence...")
    
    print("\n[Stage 4] Running Deterministic Evidence Engine...")
    from core.evidence_engine import EvidenceEngine
    evidence_enriched_path = EvidenceEngine.run(findings["output_file"], crawl_file)
    if not evidence_enriched_path:
        print("ERROR: Stage 4 produced no enriched evidence report.")
        evidence_enriched_path = findings["output_file"]
        
    report_progress("bug_triage", 75, "Running deterministic bug triage...")
    
    print("\n[Stage 4.5] Running Deterministic Bug Triage...")
    from core.bug_triage import BugTriageEngine
    triage_engine = BugTriageEngine(evidence_enriched_path)
    triaged_path = triage_engine.triage()
    
    print("\n[Stage 4.6] Running Regression Detection...")
    from core.regression_detector import RegressionDetector
    baseline_file = kwargs.get('baseline_file')
    regression_engine = RegressionDetector(triaged_path, results_dir, baseline_file)
    final_triaged_path = regression_engine.detect()

    report_progress("ai_analysis", 80, "Running Gemini AI analysis...")

    print("\n[Stage 5] Running Gemini AI analysis...")
    gemini_result = await generate_report(
        findings_file=final_triaged_path,
        results_dir=results_dir,
        run_id=run_id,
    )
    if not gemini_result:
        print("ERROR: Stage 5 produced no Gemini report.")
        return None
        
    report_progress("report_generation", 90, "Generating final QA report...")

    print("\n[Stage 6] Generating final QA report...")
    generator = QAReportGenerator(results_dir=results_dir, base_dir=base_dir)
    # Pass test cases and test results if available so they can be included in the report
    generator.test_cases_file = test_cases_file if 'test_cases_file' in locals() else None
    generator.test_results_file = test_results_file if 'test_results_file' in locals() else None
    
    result = generator.generate(
        source_path=gemini_result['json_path'],
        run_id=run_id,
    )
    if not result:
        print("ERROR: Stage 6 produced no final report.")
        return None

    report_progress("completed", 100, "Pipeline completed successfully!")

    print("\nPipeline completed successfully!")
    # The API parses these two lines from stdout; keep the prefixes stable.
    print(f"Final JSON: {result['json_path']}")
    print(f"Final Markdown: {result['md_path']}")

    if kwargs.get('ci_mode'):
        from core import ci_quality_gate
        exit_code = ci_quality_gate.evaluate_quality_gate(result['json_path'])
        if exit_code != 0:
            print(f"\nCI Quality Gate Failed with exit code {exit_code}")
            sys.exit(exit_code)
        else:
            print("\nCI Quality Gate Passed")

    return result


async def main():
    parser = argparse.ArgumentParser(description="End-to-end AI QA Agent Pipeline")
    parser.add_argument("url", help="Target URL to crawl and analyze")
    parser.add_argument("--max-pages", type=int, default=30, help="Maximum pages to crawl")
    parser.add_argument("--auth-token", help="Optional Bearer token for authentication")
    parser.add_argument("--login-url", help="Optional Login URL for form authentication")
    parser.add_argument("--username", help="Optional Username/Email for form authentication")
    parser.add_argument("--password", help="Optional Password for form authentication")
    parser.add_argument(
        "--run-id",
        help="Identifier used to name this run's output files (default: timestamp)",
    )
    parser.add_argument(
        "--output-dir",
        help="Base directory for results/ and screenshots/ (default: repo root)",
    )
    parser.add_argument(
        "--ci", action="store_true", help="Run in CI mode and exit with status based on quality gate."
    )
    parser.add_argument(
        "--baseline", help="Explicit path to a known good QA report to compare against."
    )

    args = parser.parse_args()

    if args.max_pages < 1:
        parser.error("--max-pages must be at least 1")

    password = args.password or os.environ.get("QA_AUTH_PASSWORD")

    try:
        result = await run_pipeline(
            args.url,
            max_pages=args.max_pages,
            auth_token=args.auth_token,
            run_id=args.run_id,
            output_dir=args.output_dir,
            login_url=args.login_url,
            username=args.username,
            password=password,
            ci_mode=args.ci,
            baseline_file=args.baseline,
        )
    except ValueError as error:
        # Raised by WebsiteCrawler for an unusable target URL.
        print(f"ERROR: {error}")
        return 2
    except Exception as error:
        print(f"ERROR: Pipeline failed: {error}")
        return 1

    # Non-zero exit tells the API layer the scan did not complete.
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
