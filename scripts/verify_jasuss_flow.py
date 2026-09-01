import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = "/home/devxgamer/.gemini/antigravity-ide/brain/c65bc44a-49ae-428a-a5b0-6c92cdc5420d"
BASE_URL = "http://localhost:3000"

async def main():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        print("[1/4] Navigating to Landing Page (/) ...")
        await page.goto(f"{BASE_URL}/", wait_until="networkidle")
        await page.wait_for_selector("header")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "route_home.png"), full_page=True)
        print("  ✓ Saved route_home.png")

        print("[2/4] Navigating to Pricing Page (/pricing) ...")
        await page.goto(f"{BASE_URL}/pricing", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "route_pricing.png"), full_page=True)
        print("  ✓ Saved route_pricing.png")

        print("[3/4] Navigating to Dashboard Page (/dashboard) ...")
        await page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "route_dashboard.png"), full_page=True)
        print("  ✓ Saved route_dashboard.png")

        print("[4/4] Navigating to Admin Console (/admin) ...")
        await page.goto(f"{BASE_URL}/admin", wait_until="networkidle")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "route_admin.png"), full_page=True)
        print("  ✓ Saved route_admin.png")

        await browser.close()
        print("All App Router route verifications completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
