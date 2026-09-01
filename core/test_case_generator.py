#!/usr/bin/env python3
"""
Deterministic Test Case Generator.
Consumes crawler output to extract DOM elements and draft test cases.
Optionally uses Gemini to refine text, falling back to deterministic drafts.
"""

import asyncio
import json
import os
from datetime import datetime

from playwright.async_api import async_playwright
from qa_report_generator import SecretRedactor

DESTRUCTIVE_KEYWORDS = {
    "delete", "remove", "deactivate", "cancel subscription",
    "pay", "purchase", "send", "transfer", "reset password",
    "change password", "buy", "checkout", "submit", "logout", "sign out", "account deletion"
}

class TestCaseGenerator:
    """Generates structured test cases from crawled pages."""

    def __init__(self, crawl_file, output_dir=None, max_pages=5, max_tests_per_page=10):
        self.crawl_file = crawl_file
        self.base_dir = os.path.abspath(output_dir) if output_dir else os.getcwd()
        self.results_dir = os.path.join(self.base_dir, "results")
        self.max_pages = max_pages
        self.max_tests_per_page = max_tests_per_page
        os.makedirs(self.results_dir, exist_ok=True)
        self.test_cases = []
        self.tc_counter = 0

    def _generate_id(self):
        self.tc_counter += 1
        return f"TC-{self.tc_counter:03d}"

    def _is_destructive(self, text):
        text_lower = (text or "").lower().strip()
        for kw in DESTRUCTIVE_KEYWORDS:
            if kw in text_lower:
                return True
        return False

    def _categorize(self, el_type, metadata):
        text_lower = (metadata.get("text") or "").lower()
        href = (metadata.get("href") or "").lower()
        placeholder = (metadata.get("placeholder") or "").lower()
        name = (metadata.get("name") or "").lower()
        
        if "login" in text_lower or "password" in name or "password" in placeholder or "sign in" in text_lower:
            return "authentication"
        if "search" in text_lower or "search" in name or "search" in placeholder:
            return "search"
        if el_type == "form":
            return "forms"
        if el_type == "link":
            if any(nav in href for nav in ["nav", "menu", "header"]):
                return "navigation"
            return "links"
        if el_type == "button":
            return "buttons"
        return "other"

    def _assign_priority(self, category, metadata):
        text_lower = (metadata.get("text") or "").lower()
        if category in ["authentication", "search"]:
            return "high"
        if category == "navigation" or "buy" in text_lower or "checkout" in text_lower or "cart" in text_lower:
            return "high"
        if category in ["forms", "buttons"]:
            return "medium"
        if "social" in text_lower or "privacy" in text_lower or "terms" in text_lower:
            return "low"
        return "medium"

    async def _extract_elements(self, page, url):
        """Extract actionable elements from the DOM deterministically."""
        script = """
        () => {
            const elements = [];
            
            const extractMetadata = (el, type) => {
                const rect = el.getBoundingClientRect();
                return {
                    tag: el.tagName.toLowerCase(),
                    type: type,
                    text: el.innerText ? el.innerText.substring(0, 50).trim() : (el.value ? el.value.substring(0, 50) : ''),
                    ariaLabel: el.getAttribute('aria-label') || '',
                    role: el.getAttribute('role') || '',
                    href: el.getAttribute('href') || '',
                    name: el.getAttribute('name') || '',
                    placeholder: el.getAttribute('placeholder') || '',
                    selector: el.tagName.toLowerCase() + (el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ').join('.') : '')),
                    isVisible: rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden',
                    isEnabled: !el.disabled
                };
            };

            document.querySelectorAll('a[href]').forEach(el => elements.push(extractMetadata(el, 'link')));
            document.querySelectorAll('button, input[type=button], input[type=submit], [role=button]').forEach(el => elements.push(extractMetadata(el, 'button')));
            document.querySelectorAll('form').forEach(el => elements.push(extractMetadata(el, 'form')));
            document.querySelectorAll('input:not([type=hidden]):not([type=button]):not([type=submit]), textarea, select').forEach(el => elements.push(extractMetadata(el, 'input')));
            
            return elements;
        }
        """
        try:
            return await page.evaluate(script)
        except Exception as e:
            print(f"Failed to extract elements from {url}: {e}")
            return []

    async def generate(self):
        """Run the generator."""
        if not os.path.exists(self.crawl_file):
            print(f"Test Case Generator Error: Crawl file {self.crawl_file} not found.")
            return None

        with open(self.crawl_file, "r") as f:
            crawl_data = json.load(f)

        run_id = crawl_data.get("run_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
        target = crawl_data.get("target")

        # Get unique URLs to visit
        pages = crawl_data.get("pages", [])
        urls_to_visit = []
        visited = set()
        for p in pages:
            url = p.get("actual_url", p.get("url"))
            if url and url not in visited:
                urls_to_visit.append(url)
                visited.add(url)
                
        urls_to_visit = urls_to_visit[:self.max_pages]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            seen_selectors = set()
            
            for url in urls_to_visit:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                    await page.wait_for_timeout(1000)
                except Exception:
                    continue
                    
                elements = await self._extract_elements(page, url)
                
                # Filter visible and enabled, and avoid extreme duplicates
                count_for_page = 0
                for el in elements:
                    if count_for_page >= self.max_tests_per_page:
                        break
                        
                    if not el.get("isVisible") or not el.get("isEnabled"):
                        continue
                        
                    # Skip empty elements
                    if not el.get("text") and not el.get("ariaLabel") and not el.get("placeholder"):
                        continue
                        
                    dedup_key = f"{url}|{el['type']}|{el['selector']}|{el['text']}"
                    if dedup_key in seen_selectors:
                        continue
                    seen_selectors.add(dedup_key)
                    
                    category = self._categorize(el["type"], el)
                    priority = self._assign_priority(category, el)
                    
                    # Execution Policy
                    is_dest = self._is_destructive(el.get("text") or el.get("ariaLabel"))
                    policy = "manual_review" if is_dest else "safe"
                    
                    # Deterministic drafting
                    element_desc = el.get("text") or el.get("ariaLabel") or el.get("name") or el.get("placeholder") or "element"
                    title = f"Verify {el['type']} '{element_desc}'"
                    expected_result = f"Interaction with {element_desc} should complete without errors."
                    
                    steps = [
                        f"Open {url}",
                        f"Locate the {el['type']} ({element_desc})",
                        f"Interact with the {el['type']}"
                    ]
                    
                    test_case = {
                        "id": self._generate_id(),
                        "title": SecretRedactor.redact(title),
                        "category": category,
                        "priority": priority,
                        "preconditions": [f"User is on {url}"],
                        "steps": SecretRedactor.redact(steps),
                        "expected_result": SecretRedactor.redact(expected_result),
                        "source_page": url,
                        "target_element": el,
                        "test_type": "functional",
                        "execution_policy": policy
                    }
                    self.test_cases.append(test_case)
                    count_for_page += 1

            await browser.close()
            
        output_file = os.path.join(self.results_dir, f"test_cases_{run_id}.json")
        with open(output_file, "w") as f:
            json.dump({
                "run_id": run_id,
                "target": target,
                "generated_at": datetime.now().isoformat(),
                "test_cases": self.test_cases
            }, f, indent=2)
            
        return output_file

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_case_generator.py <crawl_file>")
        sys.exit(1)
    
    generator = TestCaseGenerator(sys.argv[1])
    asyncio.run(generator.generate())
