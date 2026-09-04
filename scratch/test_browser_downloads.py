import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

DOWNLOAD_DIR = Path("/home/devxgamer/ai-qa-agent/scratch/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            viewport={"width": 1400, "height": 900}
        )
        page = await context.new_page()

        # Capture browser console logs and errors
        page.on("console", lambda msg: print(f"[BROWSER CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[BROWSER ERROR] {err}"))

        print("Navigating to http://localhost:3000/dashboard...")
        await page.goto("http://localhost:3000/dashboard", wait_until="networkidle")

        # Check if login or registration is needed or if dev token is used
        print("Page title:", await page.title())
        await page.screenshot(path=str(DOWNLOAD_DIR / "dashboard_view.png"))

        # Look for target input field
        target_input = page.locator("input[type='url'], input[placeholder*='http'], input[placeholder*='URL']").first
        if await target_input.is_visible():
            print("Found target input. Filling with https://dplms.com...")
            await target_input.fill("https://dplms.com")
            
            # Click start scan button
            start_btn = page.locator("button:has-text('Start QA Scan'), button:has-text('Launch Scan'), button:has-text('Scan')").first
            if await start_btn.is_visible():
                print("Clicking start scan button...")
                await start_btn.click()

                # Wait for scan progress or results
                print("Waiting for scan to complete...")
                try:
                    await page.wait_for_selector("button:has-text('PDF Report'), button:has-text('Excel Sheet')", timeout=60000)
                    print("Scan completed! Results view is visible.")
                except Exception as e:
                    print("Timeout waiting for results view:", e)
                    await page.screenshot(path=str(DOWNLOAD_DIR / "scan_timeout_view.png"))

        # Test download buttons if results are visible
        pdf_btn = page.locator("button:has-text('PDF Report')").first
        excel_btn = page.locator("button:has-text('Excel Sheet')").first
        json_btn = page.locator("button:has-text('JSON')").first
        md_btn = page.locator("button:has-text('Markdown')").first

        results = {}

        if await pdf_btn.is_visible():
            print("Testing PDF Download...")
            try:
                async with page.expect_download(timeout=10000) as download_info:
                    await pdf_btn.click()
                download = await download_info.value
                pdf_path = DOWNLOAD_DIR / download.suggested_filename
                await download.save_as(pdf_path)
                print(f"Downloaded PDF: {pdf_path} (size: {pdf_path.stat().st_size} bytes)")
                results["pdf"] = (str(pdf_path), pdf_path.stat().st_size)
            except Exception as e:
                print("PDF download error:", e)
                results["pdf"] = str(e)

        if await excel_btn.is_visible():
            print("Testing Excel Download...")
            try:
                async with page.expect_download(timeout=10000) as download_info:
                    await excel_btn.click()
                download = await download_info.value
                excel_path = DOWNLOAD_DIR / download.suggested_filename
                await download.save_as(excel_path)
                print(f"Downloaded Excel: {excel_path} (size: {excel_path.stat().st_size} bytes)")
                results["excel"] = (str(excel_path), excel_path.stat().st_size)
            except Exception as e:
                print("Excel download error:", e)
                results["excel"] = str(e)

        if await json_btn.is_visible():
            print("Testing JSON Download...")
            try:
                async with page.expect_download(timeout=10000) as download_info:
                    await json_btn.click()
                download = await download_info.value
                json_path = DOWNLOAD_DIR / download.suggested_filename
                await download.save_as(json_path)
                print(f"Downloaded JSON: {json_path} (size: {json_path.stat().st_size} bytes)")
                results["json"] = (str(json_path), json_path.stat().st_size)
            except Exception as e:
                print("JSON download error:", e)
                results["json"] = str(e)

        if await md_btn.is_visible():
            print("Testing Markdown Download...")
            try:
                async with page.expect_download(timeout=10000) as download_info:
                    await md_btn.click()
                download = await download_info.value
                md_path = DOWNLOAD_DIR / download.suggested_filename
                await download.save_as(md_path)
                print(f"Downloaded Markdown: {md_path} (size: {md_path.stat().st_size} bytes)")
                results["md"] = (str(md_path), md_path.stat().st_size)
            except Exception as e:
                print("Markdown download error:", e)
                results["md"] = str(e)

        await page.screenshot(path=str(DOWNLOAD_DIR / "final_results_view.png"))
        await browser.close()
        print("Test complete. Results summary:", results)

if __name__ == "__main__":
    asyncio.run(run_test())
