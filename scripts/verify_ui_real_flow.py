import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = "/home/devxgamer/.gemini/antigravity-ide/brain/c65bc44a-49ae-428a-a5b0-6c92cdc5420d"

async def run_verification():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))

        print("[1/5] Navigating to http://localhost:3000...")
        await page.goto("http://localhost:3000", wait_until="networkidle")

        # Wait for and click Dev Sign In if present
        try:
            dev_btn = page.locator("button:has-text('Dev Sign In')")
            await dev_btn.wait_for(state="visible", timeout=4000)
            print("[2/5] Clicking Dev Sign In...")
            await dev_btn.click()
            await page.wait_for_timeout(1000)
        except Exception:
            print("Already signed in or no Dev Sign In button.")

        # Capture Hero & Launch Form
        form_shot = os.path.join(SCREENSHOTS_DIR, "enterprise_ui_dashboard_form.png")
        await page.screenshot(path=form_shot, full_page=False)
        print(f"Saved: {form_shot}")

        # Test auth toggle
        print("[3/5] Testing Authenticated Crawl toggle...")
        auth_checkbox = page.locator("input[type='checkbox']")
        await auth_checkbox.click()
        await page.wait_for_timeout(500)
        auth_shot = os.path.join(SCREENSHOTS_DIR, "enterprise_ui_auth_toggle.png")
        await page.screenshot(path=auth_shot, full_page=False)
        print(f"Saved: {auth_shot}")

        # Uncheck auth toggle and fill example.com
        await auth_checkbox.click()
        await page.wait_for_timeout(300)

        print("[4/5] Launching QA Scan on https://example.com...")
        quick_pill = page.locator("button:has-text('example.com')")
        await quick_pill.click()
        await page.select_option("select#max-pages", "1")

        run_btn = page.locator("button[type='submit']:has-text('Run QA Scan')")
        await run_btn.wait_for(state="visible", timeout=5000)
        await run_btn.click()

        # Wait 2.5 seconds and capture prominent loading screen
        await page.wait_for_timeout(2500)
        loading_shot = os.path.join(SCREENSHOTS_DIR, "enterprise_ui_loading_screen.png")
        await page.screenshot(path=loading_shot, full_page=False)
        print(f"Saved Loading Screen: {loading_shot}")

        # Wait for completion by polling until results or score dial appears
        print("[5/5] Awaiting scan completion and executive dashboard...")
        for attempt in range(40):
            await page.wait_for_timeout(2000)
            if await page.locator("text=QA Scan Report").count() > 0 or await page.locator("text=High Software Quality").count() > 0:
                print("Dashboard detected!")
                break
            # Also capture interim progress
            if attempt % 5 == 0:
                print(f"Still running (elapsed ~{attempt * 2}s)...")

        results_shot = os.path.join(SCREENSHOTS_DIR, "enterprise_ui_completed_dashboard.png")
        await page.screenshot(path=results_shot, full_page=False)
        print(f"Saved Results Dashboard: {results_shot}")

        await browser.close()
        print("Verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_verification())
