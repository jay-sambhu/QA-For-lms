import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = "/home/devxgamer/.gemini/antigravity-ide/brain/c65bc44a-49ae-428a-a5b0-6c92cdc5420d"

async def run_verification():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 950})
        page = await context.new_page()

        print("[1/5] Navigating to http://localhost:3000...")
        await page.goto("http://localhost:3000", wait_until="networkidle")

        # Capture Clean Landing with Get Started & Sign In buttons and Testing Methods
        landing_shot = os.path.join(SCREENSHOTS_DIR, "production_ui_landing_get_started.png")
        await page.screenshot(path=landing_shot, full_page=False)
        print(f"Saved: {landing_shot}")

        # Test Get Started modal
        print("[2/5] Testing Get Started button & registration modal...")
        get_started_btn = page.locator("button:has-text('Get Started')")
        await get_started_btn.wait_for(state="visible", timeout=5000)
        await get_started_btn.click()
        await page.wait_for_timeout(600)

        signup_shot = os.path.join(SCREENSHOTS_DIR, "production_ui_auth_modal_signup.png")
        await page.screenshot(path=signup_shot, full_page=False)
        print(f"Saved: {signup_shot}")

        # Switch to Sign In tab inside modal
        print("[3/5] Switching to Sign In tab inside modal...")
        signin_tab = page.locator("button.page-module___8aEwW__modalTab:has-text('Sign In')")
        await signin_tab.click()
        await page.wait_for_timeout(500)

        signin_shot = os.path.join(SCREENSHOTS_DIR, "production_ui_auth_modal_signin.png")
        await page.screenshot(path=signin_shot, full_page=False)
        print(f"Saved: {signin_shot}")

        # Close modal
        close_btn = page.locator("button.page-module___8aEwW__modalCloseBtn")
        await close_btn.click()
        await page.wait_for_timeout(500)

        # Scroll down to Testing Methods section and capture
        print("[4/5] Inspecting Comprehensive QA Testing Methods section...")
        methods_section = page.locator("h2:has-text('Comprehensive QA Testing Methods')")
        await methods_section.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)

        methods_shot = os.path.join(SCREENSHOTS_DIR, "production_ui_testing_methods.png")
        await page.screenshot(path=methods_shot, full_page=False)
        print(f"Saved: {methods_shot}")

        await browser.close()
        print("[5/5] All production UI verifications completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_verification())
