import asyncio
import json
import os
from datetime import datetime
from urllib.parse import urlparse, urljoin

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Re-use NetworkMonitor from crawler
from crawler.network import NetworkMonitor

# Destructive action keywords (case-insensitive)
DESTRUCTIVE_KEYWORDS = {
    "delete", "remove", "deactivate", "cancel subscription",
    "pay", "purchase", "send", "transfer", "reset password",
    "change password", "buy", "checkout"
}

class InteractiveTester:
    """Deterministic Interactive QA Testing Engine."""
    
    def __init__(
        self,
        crawl_result,
        target_domain=None,
        max_interactions_per_page=5,
        interaction_timeout=5000,
        output_dir=None,
        run_id=None,
        progress_cb=None
    ):
        self.crawl_result = crawl_result
        self.target_url = crawl_result.get("target")
        # Infer target domain if not provided
        self.target_domain = target_domain or urlparse(self.target_url).netloc
        self.max_interactions_per_page = max_interactions_per_page
        self.interaction_timeout = interaction_timeout
        self.progress_cb = progress_cb
        
        self.run_id = run_id or crawl_result.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = os.path.abspath(output_dir) if output_dir else os.getcwd()
        self.results_dir = os.path.join(self.base_dir, "results")
        self.screenshot_dir = os.path.join(self.base_dir, "screenshots", "interactions")
        
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        self.interaction_id_counter = 0
        self.interactions = []
        self.visited_urls = set()
        self.tested_selectors = set()
        
        # Load credentials safely
        self.test_email = os.environ.get("QA_TEST_EMAIL")
        self.test_password = os.environ.get("QA_TEST_PASSWORD")

    def _generate_id(self):
        self.interaction_id_counter += 1
        return f"INT-{self.interaction_id_counter:03d}"

    def _is_destructive(self, text):
        text_lower = (text or "").lower().strip()
        for kw in DESTRUCTIVE_KEYWORDS:
            if kw in text_lower:
                return True
        return False

    def _is_third_party(self, url):
        if not url:
            return False
        host = urlparse(url).netloc.lower()
        if not host:
            return False
        # Strip port
        host = host.split(":")[0]
        # Strip www.
        if host.startswith("www."):
            host = host[4:]
        
        target_host = self.target_domain.lower()
        target_host = target_host.split(":")[0]
        if target_host.startswith("www."):
            target_host = target_host[4:]
            
        return host != target_host and not host.endswith("." + target_host)

    async def _safe_navigate(self, page, url):
        """Navigate to a URL and wait safely."""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.interaction_timeout)
            await page.wait_for_timeout(1000)
            return True
        except Exception:
            return False

    async def run(self):
        """Run the interactive testing engine."""
        pages_to_test = []
        for p in self.crawl_result.get("pages", []):
            url = p.get("actual_url", p.get("url"))
            if p.get("status") == 200 and not p.get("error") and url not in self.visited_urls:
                pages_to_test.append(url)
                self.visited_urls.add(url)
                
        elements_discovered = 0
        interactions_attempted = 0
        passed = 0
        failed = 0
        manual_review = 0

        if not pages_to_test:
            return self._build_result(0, 0, 0, 0, 0)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                ignore_https_errors=True
            )
            
            # Dismiss dialogs by default for safety
            context.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))
            
            page = await context.new_page()
            
            for index, page_url in enumerate(pages_to_test):
                if self.progress_cb:
                    pct = int((index / len(pages_to_test)) * 100)
                    self.progress_cb(pct, f"Interactive testing page {index+1} of {len(pages_to_test)}")

                nav_success = await self._safe_navigate(page, page_url)
                if not nav_success:
                    continue
                    
                # Discover Elements
                try:
                    # Collect basic interactive elements
                    # We query simple elements that we can safely test.
                    locators = []
                    
                    # Buttons
                    buttons = await page.locator("button, input[type=button], input[type=submit], [role=button]").all()
                    for b in buttons:
                        locators.append({"type": "button", "locator": b})
                        
                    # Links (internal only, skipping already visited)
                    links = await page.locator("a[href]").all()
                    for l in links:
                        locators.append({"type": "link", "locator": l})
                        
                    # Forms
                    forms = await page.locator("form").all()
                    for f in forms:
                        locators.append({"type": "form", "locator": f})
                        
                except Exception as e:
                    print("Discovery error:", e)
                    continue

                print(f"Discovered {len(locators)} locators")
                page_interactions = 0
                for item in locators:
                    if page_interactions >= self.max_interactions_per_page:
                        break
                        
                    el_type = item["type"]
                    locator = item["locator"]
                    
                    try:
                        is_visible = await locator.is_visible(timeout=500)
                        is_enabled = await locator.is_enabled(timeout=500)
                        if not is_visible or not is_enabled:
                            print(f"Skipped because visible={is_visible}, enabled={is_enabled}")
                            continue
                            
                        # Extract metadata
                        text = await locator.inner_text(timeout=500)
                        if not text:
                            # Try value attribute for inputs
                            text = await locator.get_attribute("value", timeout=500)
                        text = (text or "").strip()[:50]
                        
                        # Calculate a simple hash/selector for deduplication
                        if el_type == "link":
                            href = await locator.get_attribute("href", timeout=500)
                            if not href:
                                continue
                            absolute_url = urljoin(page_url, href)
                            if self._is_third_party(absolute_url):
                                continue
                            if absolute_url in self.visited_urls:
                                continue
                            dedup_key = f"link|{absolute_url}"
                        else:
                            html = await locator.evaluate("el => el.outerHTML")
                            dedup_key = f"{page_url}|{el_type}|{text}|{hash(html)}"
                            
                        if dedup_key in self.tested_selectors:
                            continue
                        self.tested_selectors.add(dedup_key)
                        
                        elements_discovered += 1
                        
                        # Destructive Check
                        if self._is_destructive(text):
                            self.interactions.append({
                                "interaction_id": self._generate_id(),
                                "page": page_url,
                                "element_type": el_type,
                                "element_text": text,
                                "action": "click",
                                "before_url": page_url,
                                "after_url": page_url,
                                "result": "manual_review",
                                "severity": "info",
                                "confidence": "high",
                                "description": f"Element appears destructive ('{text}'). Skipping automated interaction.",
                                "evidence": {"console_errors": [], "network_failures": [], "http_errors": []}
                            })
                            manual_review += 1
                            continue

                        # Execute Interaction safely
                        interactions_attempted += 1
                        
                        monitor = NetworkMonitor()
                        # Setup listeners specifically for this interaction
                        # We use simple wrappers to capture state
                        def on_response(response, m=monitor):
                            m.record_response(response, page_url)
                        def on_request_failure(request, m=monitor):
                            m.record_request_failure(request, page_url)
                        def on_console(msg, m=monitor):
                            m.record_console(msg, page_url)

                        page.on("response", on_response)
                        page.on("requestfailed", on_request_failure)
                        page.on("console", on_console)
                        
                        before_url = page.url
                        interaction_failed = False
                        severity = "info"
                        desc = "Interaction passed."
                        
                        try:
                            if el_type == "link":
                                await locator.click(timeout=self.interaction_timeout)
                            elif el_type == "button":
                                await locator.click(timeout=self.interaction_timeout)
                            elif el_type == "form":
                                # Safely test empty form submission
                                await locator.evaluate("form => form.submit()")
                                
                            await page.wait_for_load_state("domcontentloaded", timeout=self.interaction_timeout)
                            await page.wait_for_timeout(1000) # Let network settle
                            
                        except PlaywrightTimeoutError:
                            interaction_failed = True
                            severity = "medium"
                            desc = "Interaction timed out."
                        except Exception as e:
                            interaction_failed = True
                            severity = "high"
                            desc = f"JavaScript exception or Playwright error during interaction: {str(e)}"
                            
                        after_url = page.url
                        
                        # Check errors
                        has_500 = any(e.get("status", 200) >= 500 for e in monitor.http_errors)
                        has_404 = any(e.get("status", 200) == 404 for e in monitor.http_errors)
                        has_js_err = len(monitor.console_errors) > 0
                        
                        if has_500:
                            interaction_failed = True
                            severity = "high"
                            desc = "Interaction caused a 500 Server Error."
                        elif has_404:
                            interaction_failed = True
                            severity = "high"
                            desc = "Interaction caused a 404 Not Found error."
                        elif has_js_err and not interaction_failed:
                            interaction_failed = True
                            severity = "high"
                            desc = "Interaction caused a JavaScript console error."
                        
                        # Blank page check
                        if not interaction_failed:
                            content = await page.content()
                            if len(content.strip()) < 50:
                                interaction_failed = True
                                severity = "high"
                                desc = "Interaction resulted in a blank page."
                        
                        # Screenshot
                        screenshot_rel_path = None
                        if interaction_failed:
                            iid = self._generate_id()
                            screenshot_path = os.path.join(self.screenshot_dir, f"{iid}.png")
                            try:
                                await page.screenshot(path=screenshot_path, full_page=True)
                                screenshot_rel_path = os.path.relpath(screenshot_path, self.base_dir)
                            except Exception:
                                pass
                        else:
                            iid = self._generate_id()
                            
                        result_state = "failed" if interaction_failed else "passed"
                        if interaction_failed:
                            failed += 1
                        else:
                            passed += 1
                            
                        self.interactions.append({
                            "interaction_id": iid,
                            "page": page_url,
                            "element_type": el_type,
                            "element_text": text,
                            "action": "click" if el_type in ["link", "button"] else "submit",
                            "before_url": before_url,
                            "after_url": after_url,
                            "result": result_state,
                            "severity": severity,
                            "confidence": "high",
                            "description": desc,
                            "evidence": {
                                "console_errors": monitor.console_errors,
                                "network_failures": monitor.network_failures,
                                "http_errors": monitor.http_errors,
                                "screenshot": screenshot_rel_path
                            }
                        })
                        
                        # Cleanup listeners
                        page.remove_listener("response", on_response)
                        page.remove_listener("requestfailed", on_request_failure)
                        page.remove_listener("console", on_console)
                        
                        # Return to original page if we navigated away
                        if page.url != page_url:
                            await self._safe_navigate(page, page_url)
                            
                        page_interactions += 1
                        
                    except Exception as loop_e:
                        print("Interaction loop error:", loop_e)
                        pass
                    
            await context.close()
            await browser.close()
            
        return self._build_result(
            len(pages_to_test),
            elements_discovered,
            interactions_attempted,
            passed,
            failed,
            manual_review
        )
        
    def _build_result(self, pages_tested, elements_discovered, attempted, passed, failed, manual_review):
        result = {
            "target": self.target_url,
            "generated_at": datetime.now().isoformat(),
            "pages_tested": pages_tested,
            "summary": {
                "elements_discovered": elements_discovered,
                "interactions_attempted": attempted,
                "passed": passed,
                "failed": failed,
                "manual_review": manual_review
            },
            "interactions": self.interactions
        }
        
        output_file = os.path.join(
            self.results_dir,
            f"interactive_qa_{self.run_id}.json"
        )
        
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(result, file, indent=2, ensure_ascii=False)
            
        result["output_file"] = output_file
        return result
