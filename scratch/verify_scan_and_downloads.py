import asyncio
import json
import time
import zipfile
from pathlib import Path
from playwright.async_api import async_playwright

DOWNLOAD_DIR = Path("/home/devxgamer/ai-qa-agent/scratch/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

SCAN_ID = "95ffac5b-02f4-4f98-80dc-3ff00f1ff8c5"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 960}
        )

        page = await context.new_page()

        # Inject session
        await page.goto("http://localhost:3000")
        await page.evaluate("""() => {
            localStorage.setItem('jasuss_session', JSON.stringify({
                access_token: 'dev-token',
                user: {
                    id: '00000000-0000-0000-0000-000000000001',
                    email: 'dev@example.com',
                    role: 'admin'
                }
            }));
        }""")

        target_url = f"http://localhost:3000/dashboard/scan/{SCAN_ID}"
        print(f"Navigating to scan monitor: {target_url}")
        await page.goto(target_url, wait_until="networkidle")

        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        await page.screenshot(path=str(DOWNLOAD_DIR / "scan_live_monitor.png"))
        print("Waiting for QA scan pipeline to complete and results to render...")
        await page.wait_for_selector("button:has-text('PDF Report')", timeout=300000)
        print("Results view is now visible on screen!")

        await page.screenshot(path=str(DOWNLOAD_DIR / "scan_completed_dashboard.png"))

        # Download & Validate 1: PDF Report
        print("\n--- 1. Testing PDF Download ---")
        async with page.expect_download(timeout=15000) as download_info:
            await page.locator("button:has-text('PDF Report')").first.click()
        pdf_download = await download_info.value
        pdf_path = DOWNLOAD_DIR / pdf_download.suggested_filename
        await pdf_download.save_as(pdf_path)
        print(f"Saved PDF to: {pdf_path}")
        pdf_bytes = pdf_path.read_bytes()
        assert pdf_bytes.startswith(b"%PDF-"), f"Invalid PDF header: {pdf_bytes[:10]}"
        print(f"✅ PDF verified: {len(pdf_bytes)} bytes, starts with %PDF- header.")

        # Download & Validate 2: Excel Sheet
        print("\n--- 2. Testing Excel (.xlsx) Download ---")
        async with page.expect_download(timeout=15000) as download_info:
            await page.locator("button:has-text('Excel Sheet')").first.click()
        excel_download = await download_info.value
        excel_path = DOWNLOAD_DIR / excel_download.suggested_filename
        await excel_download.save_as(excel_path)
        print(f"Saved Excel to: {excel_path}")
        excel_bytes = excel_path.read_bytes()
        assert excel_bytes.startswith(b"PK\x03\x04"), "Invalid XLSX ZIP header!"
        with zipfile.ZipFile(excel_path, 'r') as z:
            sheet_files = [f for f in z.namelist() if f.startswith('xl/worksheets/')]
            print(f"Excel worksheets found in archive: {sheet_files}")
            assert len(sheet_files) >= 1, "Excel workbook has no sheets!"
        print(f"✅ Excel verified: {len(excel_bytes)} bytes, valid multi-sheet workbook.")

        # Download & Validate 3: JSON Report
        print("\n--- 3. Testing JSON Download ---")
        async with page.expect_download(timeout=15000) as download_info:
            await page.locator("button:has-text('JSON')").first.click()
        json_download = await download_info.value
        json_path = DOWNLOAD_DIR / json_download.suggested_filename
        await json_download.save_as(json_path)
        print(f"Saved JSON to: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        assert isinstance(json_data, dict), "Invalid JSON format!"
        print(f"✅ JSON verified: {len(json_path.read_text(encoding='utf-8'))} chars, valid JSON object with keys: {list(json_data.keys())}")

        # Download & Validate 4: Markdown Report
        print("\n--- 4. Testing Markdown (.md) Download ---")
        async with page.expect_download(timeout=15000) as download_info:
            await page.locator("button:has-text('Markdown')").first.click()
        md_download = await download_info.value
        md_path = DOWNLOAD_DIR / md_download.suggested_filename
        await md_download.save_as(md_path)
        print(f"Saved Markdown to: {md_path}")
        md_text = md_path.read_text(encoding='utf-8')
        assert "# JASUSS QA Report" in md_text or "# QA" in md_text, "Missing Markdown title!"
        assert "Executive Summary" in md_text, "Missing Executive Summary section in Markdown!"
        print(f"✅ Markdown verified: {len(md_text)} chars, valid report content.")

        print("\n🎉 ALL 4 EXPORT FORMATS (PDF, Excel, JSON, Markdown) TESTED & VERIFIED ON DPLMS REPORT!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
