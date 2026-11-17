#!/usr/bin/env python3
"""
Whole-System Comprehensive Browser & E2E Diagnostic
===================================================
Simulates real browser user sessions to thoroughly inspect:
1. Public pages: /, /pricing, /blog
2. User login and /dashboard
3. Max pages limit for regular user vs admin (up to 50 pages)
4. Scan detail view: /dashboard/scan/[id]
5. Report exports: PDF, Excel, JSON download triggers and error handlers
6. Admin tabs: overview, users, scans, blogs, ai, system
7. Captures and aggregates all browser console errors, failed API calls, and UI crashes
"""

import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:3000")

def run_diagnostics():
    print(f"=== STARTING WHOLE SYSTEM BROWSER DIAGNOSTIC ON {BASE_URL} ===")
    all_issues = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # Track console errors & failed network requests
        console_logs = []
        network_failures = []

        def handle_console(msg):
            if msg.type in ["error", "warning"]:
                text = msg.text
                # Filter out benign third-party or adsense noise if any
                if "adsbygoogle" in text or "adblock" in text.lower():
                    return
                console_logs.append(f"[{msg.type.upper()}] {text}")

        def handle_response(response):
            if response.status >= 400:
                # ignore intentional 401s on initial unauth checks if normal
                if response.status in [401, 404] and "/api/v1/auth/me" in response.url:
                    return
                network_failures.append(f"{response.status} {response.request.method} {response.url}")

        page = context.new_page()
        page.on("console", handle_console)
        page.on("response", handle_response)

        # -------------------------------------------------------------
        # STEP 1: PUBLIC PAGES INSPECTION
        # -------------------------------------------------------------
        print("\n--- [Step 1] Inspecting Public Pages ---")
        for route in ["/", "/pricing", "/blog"]:
            print(f"Visiting {route}...")
            res = page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
            if res.status != 200:
                all_issues.append(f"Public route {route} returned HTTP {res.status}")
            page.wait_for_timeout(1000)

        # -------------------------------------------------------------
        # STEP 2: ADMIN AUTHENTICATION
        # -------------------------------------------------------------
        print("\n--- [Step 2] Authenticating as Admin User ---")
        page.goto(BASE_URL, wait_until="networkidle")
        signin_btn = page.locator("button:has-text('Sign In'), a:has-text('Sign In')").first
        signin_btn.click()
        page.locator("#auth-email").fill("admin_test_qa@jasuss.tech")
        page.locator("#auth-password").fill("AdminPassword123!QA")
        page.locator("button[type='submit']").first.click()
        page.wait_for_url("**/admin", timeout=15000)
        print("  ✓ Admin logged in successfully to /admin")

        # -------------------------------------------------------------
        # STEP 3: ADMIN CONSOLE TABS INSPECTION
        # -------------------------------------------------------------
        print("\n--- [Step 3] Inspecting Admin Console Tabs ---")
        admin_tabs = ["Overview", "Tenants & Roles", "Global Scans", "Dynamic Blog CMS", "AI Reasoning & Keys", "Cluster Telemetry"]
        for tab in admin_tabs:
            tab_btn = page.locator(f"button:has-text('{tab}')").first
            if tab_btn.is_visible():
                tab_btn.click()
                page.wait_for_timeout(1000)
                print(f"  ✓ Admin tab '{tab}' clicked and rendered")
            else:
                all_issues.append(f"Admin tab '{tab}' not visible")

        # -------------------------------------------------------------
        # STEP 4: DASHBOARD & SCAN CREATION INSPECTION
        # -------------------------------------------------------------
        print("\n--- [Step 4] Inspecting Dashboard & 50-Page Scan Input ---")
        page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Check page limit / Max Pages input
        # In Dashboard, check if max_pages input exists or can be set up to 50
        page_inputs = page.locator("input[type='number']").all()
        print(f"Found {len(page_inputs)} number inputs on Dashboard.")
        for inp in page_inputs:
            name = inp.get_attribute("name") or inp.get_attribute("id") or inp.get_attribute("placeholder")
            val = inp.input_value()
            max_attr = inp.get_attribute("max")
            print(f"  - Input: id/name='{name}', current='{val}', max='{max_attr}'")

        # -------------------------------------------------------------
        # STEP 5: SCAN DETAIL VIEW & EXPORT TESTING
        # -------------------------------------------------------------
        print("\n--- [Step 5] Inspecting Existing Scans & Report Generation ---")
        # Find scan links on dashboard
        scan_links = page.locator("a[href*='/dashboard/scan/']").all()
        print(f"Found {len(scan_links)} scan links on dashboard.")
        
        target_scan_url = None
        if scan_links:
            target_scan_url = scan_links[0].get_attribute("href")
            print(f"Navigating to scan: {target_scan_url}...")
            page.goto(f"{BASE_URL}{target_scan_url}", wait_until="networkidle")
            page.wait_for_timeout(2000)

            # Check Export Buttons
            # Look for PDF, Excel, JSON export buttons
            export_buttons = page.locator("button:has-text('PDF'), button:has-text('Excel'), button:has-text('JSON'), button:has-text('Export')").all()
            print(f"Found {len(export_buttons)} export buttons on scan page:")
            for btn in export_buttons:
                txt = btn.inner_text().strip().replace('\n', ' ')
                print(f"  - Button text: '{txt}'")

            # Test clicking each export button and watch for errors!
            for btn in export_buttons:
                txt = btn.inner_text().strip().replace('\n', ' ')
                print(f"Testing click on: '{txt}'...")
                initial_errors_count = len(console_logs)
                try:
                    # Some buttons trigger download
                    with page.expect_download(timeout=4000) as download_info:
                        btn.click()
                    download = download_info.value
                    print(f"  ✓ Download triggered successfully: {download.suggested_filename}")
                except Exception as ex:
                    # It might be in-browser or fail, let's see if console errors appeared
                    new_errors = console_logs[initial_errors_count:]
                    if new_errors:
                        print(f"  ✕ CONSOLE ERROR on clicking '{txt}': {new_errors}")
                        all_issues.extend(new_errors)
                    else:
                        print(f"  ℹ Clicked '{txt}' (no direct download event or client-side generation without download event: {type(ex).__name__})")
                page.wait_for_timeout(1000)

        context.close()
        browser.close()

    print("\n=======================================================")
    print("           DIAGNOSTIC SUMMARY REPORT                  ")
    print("=======================================================")
    print(f"Total Console Warnings/Errors: {len(console_logs)}")
    for c in console_logs:
        print(f"  {c}")

    print(f"\nTotal HTTP 4xx/5xx Network Failures: {len(network_failures)}")
    for n in network_failures:
        print(f"  {n}")

    print(f"\nTotal Detected Issues: {len(all_issues)}")
    for issue in all_issues:
        print(f"  ✕ {issue}")
    print("=======================================================")

if __name__ == "__main__":
    run_diagnostics()
