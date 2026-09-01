#!/usr/bin/env python3
"""
Test Case Executor.
Safely executes deterministic test cases, captures evidence,
and converts failures into QA findings.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from crawler.network import NetworkMonitor

class TestCaseExecutor:
    """Executes safe test cases and tracks results."""

    def __init__(self, test_cases_file, qa_findings_file=None, output_dir=None):
        self.test_cases_file = test_cases_file
        self.qa_findings_file = qa_findings_file
        self.base_dir = os.path.abspath(output_dir) if output_dir else os.getcwd()
        self.results_dir = os.path.join(self.base_dir, "results")
        self.screenshot_dir = os.path.join(self.base_dir, "screenshots", "tests")
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.screenshot_dir, exist_ok=True)

    async def execute(self):
        if not os.path.exists(self.test_cases_file):
            print(f"Executor Error: {self.test_cases_file} not found.")
            return None

        with open(self.test_cases_file, "r") as f:
            data = json.load(f)
            
        run_id = data.get("run_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
        test_cases = data.get("test_cases", [])

        results = []
        new_findings = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            # Dismiss dialogs
            context.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))
            page = await context.new_page()

            for tc in test_cases:
                start_time = time.time()
                status = "blocked"
                actual_result = "Test not executed."
                evidence = {
                    "screenshot": None,
                    "console_errors": [],
                    "network_failures": [],
                    "http_errors": []
                }

                if tc.get("execution_policy") == "manual_review":
                    status = "manual_review"
                    actual_result = "Execution skipped due to safety policy (potential destructive action)."
                    
                elif tc.get("execution_policy") == "safe":
                    source_page = tc.get("source_page")
                    target_el = tc.get("target_element", {})
                    selector = target_el.get("selector")
                    text = target_el.get("text")
                    
                    try:
                        await page.goto(source_page, wait_until="domcontentloaded", timeout=10000)
                        await page.wait_for_timeout(500)
                        
                        monitor = NetworkMonitor()
                        def on_response(response, m=monitor):
                            m.record_response(response, source_page)
                        def on_request_failure(request, m=monitor):
                            m.record_request_failure(request, source_page)
                        def on_console(msg, m=monitor):
                            m.record_console(msg, source_page)

                        page.on("response", on_response)
                        page.on("requestfailed", on_request_failure)
                        page.on("console", on_console)
                        
                        # Find element
                        locator = None
                        if selector:
                            try:
                                # Sometimes generated selectors are invalid or too broad, try exact text first if button/link
                                if text and target_el.get("type") in ["button", "link"]:
                                    locator = page.get_by_text(text, exact=True).first
                                    if not await locator.is_visible(timeout=500):
                                        locator = page.locator(selector).first
                                else:
                                    locator = page.locator(selector).first
                            except Exception:
                                pass
                                
                        if not locator:
                            status = "blocked"
                            actual_result = "Failed to locate target element."
                        else:
                            try:
                                if target_el.get("type") == "input":
                                    await locator.fill("test data", timeout=5000)
                                else:
                                    await locator.click(timeout=5000)
                                    
                                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                                await page.wait_for_timeout(1000)
                                
                                has_500 = any(e.get("status", 200) >= 500 for e in monitor.http_errors)
                                has_404 = any(e.get("status", 200) == 404 for e in monitor.http_errors)
                                
                                if has_500 or has_404:
                                    status = "failed"
                                    actual_result = f"Test triggered HTTP {500 if has_500 else 404} error."
                                elif len(monitor.console_errors) > 0:
                                    status = "failed"
                                    actual_result = "Test triggered JavaScript console errors."
                                else:
                                    status = "passed"
                                    actual_result = "Interaction completed successfully without errors."
                                    
                            except PlaywrightTimeoutError:
                                status = "failed"
                                actual_result = "Interaction timed out."
                            except Exception as e:
                                status = "failed"
                                actual_result = f"Exception during interaction: {str(e)}"
                        
                        evidence["console_errors"] = monitor.console_errors
                        evidence["network_failures"] = monitor.network_failures
                        evidence["http_errors"] = monitor.http_errors
                        
                        if status == "failed":
                            # Take screenshot
                            try:
                                screenshot_path = os.path.join(self.screenshot_dir, f"{tc['id']}.png")
                                await page.screenshot(path=screenshot_path, full_page=True)
                                evidence["screenshot"] = os.path.relpath(screenshot_path, self.base_dir)
                            except Exception:
                                pass
                                
                        page.remove_listener("response", on_response)
                        page.remove_listener("requestfailed", on_request_failure)
                        page.remove_listener("console", on_console)
                        
                    except Exception as e:
                        status = "blocked"
                        actual_result = f"Navigation failed: {str(e)}"
                        
                duration = int((time.time() - start_time) * 1000)
                
                result = {
                    "test_id": tc["id"],
                    "status": status,
                    "duration_ms": duration,
                    "page": tc.get("source_page"),
                    "steps": tc.get("steps"),
                    "expected_result": tc.get("expected_result"),
                    "actual_result": actual_result,
                    "evidence": evidence,
                    "failure_reason": actual_result if status == "failed" else None
                }
                results.append(result)

                # Create bug finding if failed
                if status == "failed":
                    finding_type = "http_error" if len(evidence["http_errors"]) > 0 else ("console_error" if len(evidence["console_errors"]) > 0 else "interactive_failure")
                    finding = {
                        "id": f"TESTBUG-{tc['id']}",
                        "finding_type": finding_type,
                        "url": tc.get("source_page"),
                        "title": f"Test Failure: {tc.get('title')}",
                        "description": actual_result,
                        "severity": "high",
                        "affected_pages": [tc.get("source_page")],
                        "occurrences": 1,
                        "evidence": evidence
                    }
                    new_findings.append(finding)

            await browser.close()
            
        # Append findings if provided
        if self.qa_findings_file and os.path.exists(self.qa_findings_file) and new_findings:
            try:
                with open(self.qa_findings_file, "r") as f:
                    existing = json.load(f)
                
                # We could run full deduplication here, but for simplicity, append uniquely
                existing_findings = existing.get("findings", [])
                
                # Check for duplicates by title and url
                for nf in new_findings:
                    is_dup = False
                    for ef in existing_findings:
                        if ef.get("finding_type") == nf["finding_type"] and ef.get("url") == nf["url"]:
                            is_dup = True
                            break
                    if not is_dup:
                        existing_findings.append(nf)
                
                existing["findings"] = existing_findings
                with open(self.qa_findings_file, "w") as f:
                    json.dump(existing, f, indent=2)
            except Exception as e:
                print(f"Error appending findings: {e}")
                
        output_file = os.path.join(self.results_dir, f"test_results_{run_id}.json")
        with open(output_file, "w") as f:
            json.dump({
                "run_id": run_id,
                "generated_at": datetime.now().isoformat(),
                "results": results
            }, f, indent=2)
            
        return output_file

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_case_executor.py <test_cases_file> [qa_findings_file]")
        sys.exit(1)
        
    qa_file = sys.argv[2] if len(sys.argv) > 2 else None
    executor = TestCaseExecutor(sys.argv[1], qa_file)
    asyncio.run(executor.execute())
