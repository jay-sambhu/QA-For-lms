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
from bug_detector import generate_qa_findings
from gemini_analyzer import generate_report
from qa_report_generator import QAReportGenerator

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


async def run_pipeline(url, max_pages=30, auth_token=None, run_id=None, output_dir=None):
    """Run all four stages, returning the final report dict or None."""
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.abspath(output_dir) if output_dir else ROOT_DIR
    results_dir = os.path.join(base_dir, "results")

    print(f"Starting AI QA Pipeline for: {url}")
    print(f"Run ID: {run_id}")
    print("=" * 60)

    def report_progress(stage, percent, message):
        progress_file = os.path.join(results_dir, f"progress_{run_id}.json")
        try:
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump({"stage": stage, "percent": percent, "message": message}, f)
        except Exception:
            pass

    report_progress("crawling", 0, "Initializing crawler...")

    print("\n[Stage 1] Crawling website...")
    crawler = WebsiteCrawler(
        url,
        max_pages=max_pages,
        auth_token=auth_token,
        output_dir=base_dir,
        run_id=run_id,
        progress_cb=lambda pct, msg: report_progress("crawling", pct, msg)
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

    report_progress("bug_detection", 60, "Running deterministic bug detector...")

    print("\n[Stage 2] Running deterministic bug detector...")
    findings = generate_qa_findings(
        crawl_file=crawl_file,
        results_dir=results_dir,
        run_id=run_id,
    )
    if not findings:
        print("ERROR: Stage 2 produced no findings file.")
        return None

    report_progress("ai_analysis", 70, "Running Gemini AI analysis...")

    print("\n[Stage 3] Running Gemini AI analysis...")
    gemini_result = await generate_report(
        findings_file=findings["output_file"],
        results_dir=results_dir,
        run_id=run_id,
    )
    if not gemini_result:
        print("ERROR: Stage 3 produced no Gemini report.")
        return None

    report_progress("report_generation", 90, "Generating final QA report...")

    print("\n[Stage 4] Generating final QA report...")
    generator = QAReportGenerator(results_dir=results_dir, base_dir=base_dir)
    result = generator.generate(
        source_path=gemini_result["json_path"],
        run_id=run_id,
    )
    if not result:
        print("ERROR: Stage 4 produced no final report.")
        return None

    report_progress("completed", 100, "Pipeline completed successfully!")

    print("\nPipeline completed successfully!")
    # The API parses these two lines from stdout; keep the prefixes stable.
    print(f"Final JSON: {result['json_path']}")
    print(f"Final Markdown: {result['md_path']}")

    return result


async def main():
    parser = argparse.ArgumentParser(description="End-to-end AI QA Agent Pipeline")
    parser.add_argument("url", help="Target URL to crawl and analyze")
    parser.add_argument("--max-pages", type=int, default=30, help="Maximum pages to crawl")
    parser.add_argument("--auth-token", help="Optional Bearer token for authentication")
    parser.add_argument(
        "--run-id",
        help="Identifier used to name this run's output files (default: timestamp)",
    )
    parser.add_argument(
        "--output-dir",
        help="Base directory for results/ and screenshots/ (default: repo root)",
    )

    args = parser.parse_args()

    if args.max_pages < 1:
        parser.error("--max-pages must be at least 1")

    try:
        result = await run_pipeline(
            args.url,
            max_pages=args.max_pages,
            auth_token=args.auth_token,
            run_id=args.run_id,
            output_dir=args.output_dir,
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
