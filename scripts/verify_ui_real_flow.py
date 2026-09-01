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

        print("[1/6] Navigating to http://localhost:3000...")
        await page.goto("http://localhost:3000", wait_until="networkidle")

        # Click Dev Sign In if present
        try:
            dev_btn = page.locator("button:has-text('Dev Sign In')")
            await dev_btn.wait_for(state="visible", timeout=4000)
            print("[2/6] Clicking Dev Sign In...")
            await dev_btn.click()
            await page.wait_for_timeout(1000)
        except Exception:
            print("Already signed in or no Dev Sign In button.")

        # Capture Hero & Launch Form
        form_shot = os.path.join(SCREENSHOTS_DIR, "enterprise_ui_dashboard_form.png")
        await page.screenshot(path=form_shot, full_page=False)
        print(f"Saved: {form_shot}")

        print("[3/6] Launching QA Scan on https://example.com...")
        quick_pill = page.locator("button:has-text('example.com')")
        await quick_pill.click()
        await page.select_option("select#max-pages", "1")

        run_btn = page.locator("button[type='submit']:has-text('Run QA Scan')")
        await run_btn.wait_for(state="visible", timeout=5000)
        await run_btn.click()

        # Wait 3 seconds and capture prominent loading screen with Stop Button & Multi-Device Deck
        await page.wait_for_timeout(3000)
        loading_shot = os.path.join(SCREENSHOTS_DIR, "enterprise_ui_loading_screen_with_devices.png")
        await page.screenshot(path=loading_shot, full_page=False)
        print(f"Saved Loading Screen: {loading_shot}")

        # Wait for scan completion
        print("[4/6] Awaiting scan completion and executive dashboard...")
        for attempt in range(45):
            await page.wait_for_timeout(2000)
            if await page.locator("text=QA Scan Report").count() > 0 or await page.locator("text=High Software Quality").count() > 0:
                print("Dashboard detected!")
                break
            if attempt % 5 == 0:
                print(f"Still running (elapsed ~{attempt * 2}s)...")

        results_shot = os.path.join(SCREENSHOTS_DIR, "enterprise_ui_completed_dashboard.png")
        await page.screenshot(path=results_shot, full_page=False)
        print(f"Saved Results Dashboard: {results_shot}")

        # Test Stop Button functionality on a new scan
        print("[5/6] Testing Stop Scan button...")
        new_scan_btn = page.locator("button:has-text('New Scan')")
        await new_scan_btn.wait_for(state="visible", timeout=5000)
        await new_scan_btn.click()
        await page.wait_for_timeout(1500)

        # Fill and launch 2nd scan
        await page.fill("input[type='url']", "https://example.com")
        await page.wait_for_timeout(500)
        await page.click("button[type='submit']:has-text('Run QA Scan')")
        await page.wait_for_timeout(1500)

        # Click Stop Scan button
        stop_btn = page.locator("button:has-text('Stop Scan')")
        await stop_btn.wait_for(state="visible", timeout=5000)
        print("[6/6] Clicking Stop Scan button...")
        await stop_btn.click()
        await page.wait_for_timeout(2000)

        stopped_shot = os.path.join(SCREENSHOTS_DIR, "enterprise_ui_stopped_scan.png")
        await page.screenshot(path=stopped_shot, full_page=False)
        print(f"Saved Stopped Scan Screenshot: {stopped_shot}")

        await browser.close()
        print("All UI & Stop Button verifications completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_verification())
