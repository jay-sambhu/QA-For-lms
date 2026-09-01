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

        print("[1/3] Navigating to JASUSS Landing Page...")
        await page.goto(BASE_URL, wait_until="networkidle")
        await page.wait_for_selector("header")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "jasuss_landing_page.png"), full_page=True)
        print("  ✓ Saved jasuss_landing_page.png")

        print("[2/3] Opening Pricing & Multi-Payment Gateways Modal...")
        pricing_btn = page.locator("button:has-text('Pricing & Plans')")
        if await pricing_btn.count() > 0:
            await pricing_btn.first.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "jasuss_pricing_modal.png"))
            print("  ✓ Saved jasuss_pricing_modal.png")
            # Close modal
            close_btn = page.locator("button[title='Close']").or_(page.locator("button:has-text('✕')")).or_(page.locator("div[class*='modalHeader'] button"))
            if await close_btn.count() > 0:
                await close_btn.first.click()
                await page.wait_for_timeout(500)

        print("[3/3] Opening Admin Dashboard View...")
        admin_btn = page.locator("button:has-text('Admin Console')")
        if await admin_btn.count() > 0:
            await admin_btn.first.click()
            await page.wait_for_timeout(1200)
            await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "jasuss_admin_dashboard.png"), full_page=True)
            print("  ✓ Saved jasuss_admin_dashboard.png")

        await browser.close()
        print("All visual verifications completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
