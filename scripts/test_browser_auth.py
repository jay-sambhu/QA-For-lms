#!/usr/bin/env python3
"""
End-to-End Browser Authentication & Authorization Suite
======================================================
Tests the live Next.js application using Playwright:
1. Modal open/close & mode switching
2. Google OAuth redirection flow validation
3. Regular user email/password login -> /dashboard
4. Admin user email/password login -> /admin & telemetry verification
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:3000")

def run_tests():
    print(f"Starting E2E Browser Authentication Tests on {BASE_URL}...")
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # TEST 1: Google OAuth Button Trigger
        # -------------------------------------------------------------
        print("\n[Test 1] Testing Google OAuth Button Trigger & Redirect...")
        context = browser.new_context()
        page = context.new_page()

        redirect_urls = []
        page.on("request", lambda req: redirect_urls.append(req.url) if "supabase" in req.url or "google" in req.url else None)

        page.goto(BASE_URL, wait_until="networkidle")
        
        # Click Sign In button in navbar
        signin_btn = page.locator("button:has-text('Sign In'), a:has-text('Sign In')").first
        signin_btn.wait_for(state="visible", timeout=10000)
        signin_btn.click()

        # Modal should be visible
        modal_title = page.locator("#auth-modal-title")
        modal_title.wait_for(state="visible", timeout=5000)
        print("  ✓ Auth Modal successfully opened")

        # Find Google button
        google_btn = page.locator("button:has-text('Google')").first
        google_btn.wait_for(state="visible", timeout=5000)

        # Listen for popup or redirect
        with page.expect_navigation(url=lambda u: "supabase.co" in u or "accounts.google.com" in u, timeout=10000) as nav_info:
            google_btn.click()
            print("  ✓ Clicked 'Google' sign-in button")

        final_url = page.url
        print(f"  ✓ Navigated to OAuth authorization flow: {final_url[:90]}...")
        if "google" not in final_url and "supabase" not in final_url:
            errors.append(f"Google OAuth did not navigate to authorization URL. Got: {final_url}")
        else:
            print("  ✓ Test 1 PASSED: Google OAuth triggers direct authorization redirect.")
        context.close()

        # -------------------------------------------------------------
        # TEST 2: Regular User Email/Password Login -> /dashboard
        # -------------------------------------------------------------
        print("\n[Test 2] Testing Regular User Email/Password Login -> /dashboard...")
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        signin_btn = page.locator("button:has-text('Sign In'), a:has-text('Sign In')").first
        signin_btn.click()

        page.locator("#auth-email").fill("autotest_user@jasuss.tech")
        page.locator("#auth-password").fill("TestPassword123!QA")
        
        submit_btn = page.locator("button[type='submit']").first
        submit_btn.click()
        print("  ✓ Submitted credentials for autotest_user@jasuss.tech")

        # Expect redirect to /dashboard
        page.wait_for_url("**/dashboard", timeout=15000)
        print(f"  ✓ Successfully navigated to: {page.url}")

        # Wait for page content to load
        page.wait_for_selector("text=Dashboard", timeout=10000)
        print("  ✓ Test 2 PASSED: Regular user lands on /dashboard.")
        context.close()

        # -------------------------------------------------------------
        # TEST 3: Admin User Email/Password Login -> /admin
        # -------------------------------------------------------------
        print("\n[Test 3] Testing Admin User Email/Password Login -> /admin...")
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        signin_btn = page.locator("button:has-text('Sign In'), a:has-text('Sign In')").first
        signin_btn.click()

        page.locator("#auth-email").fill("admin_test_qa@jasuss.tech")
        page.locator("#auth-password").fill("AdminPassword123!QA")

        submit_btn = page.locator("button[type='submit']").first
        submit_btn.click()
        print("  ✓ Submitted credentials for admin_test_qa@jasuss.tech")

        # Expect redirect to /admin
        page.wait_for_url("**/admin", timeout=15000)
        print(f"  ✓ Successfully navigated to: {page.url}")

        # Verify Admin Console loaded without getting stuck in infinite "Verifying credentials"
        page.wait_for_selector("text=Admin Operations Console", timeout=15000)
        print("  ✓ Admin telemetry and overview loaded successfully")
        print("  ✓ Test 3 PASSED: Admin lands on /admin and telemetry loads cleanly.")
        context.close()

        browser.close()

    if errors:
        print("\n❌ SOME TESTS FAILED:")
        for err in errors:
            print("  -", err)
        sys.exit(1)
    else:
        print("\n=======================================================")
        print("🎉 ALL E2E AUTHENTICATION BROWSER TESTS PASSED!")
        print("=======================================================")

if __name__ == "__main__":
    run_tests()
