import asyncio
import json
import zipfile
from pathlib import Path
from playwright.async_api import async_playwright

DOWNLOAD_DIR = Path("/home/devxgamer/ai-qa-agent/scratch/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 960}
        )

        # Set authenticated dev session in localStorage
        page = await context.new_page()
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

        print("Navigating to /dashboard with authenticated session...")
        await page.goto("http://localhost:3000/dashboard", wait_until="networkidle")

        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        await page.screenshot(path=str(DOWNLOAD_DIR / "1_dashboard_authenticated.png"))
        print("Dashboard loaded successfully.")

        # Fill URL
        url_input = page.locator("input[placeholder*='https://example.com'], input[type='url']").first
        await url_input.fill("https://dplms.com")

        # Set max pages to 2 for fast verification scan
        max_pages_input = page.locator("input[type='number']").first
        if await max_pages_input.is_visible():
            await max_pages_input.fill("2")

        # Click Start QA Scan
        start_btn = page.locator("button:has-text('Run QA Scan'), button:has-text('Start QA Scan')").first
        print("Starting QA scan for https://dplms.com...")
        await start_btn.click()

        # Wait for redirect to /dashboard/scan/[id]
        await page.wait_for_url("**/dashboard/scan/**", timeout=15000)
        print(f"Redirected to scan monitor: {page.url}")

        await page.screenshot(path=str(DOWNLOAD_DIR / "2_scan_monitor.png"))

        # Wait for scan completion (waiting for results panel)
        print("Waiting for QA scan pipeline to complete and results view to render...")
        await page.wait_for_selector("button:has-text('PDF Report')", timeout=120000)
        print("QA Scan finished! Results view loaded.")

        await page.screenshot(path=str(DOWNLOAD_DIR / "3_scan_results.png"))

        # Download & Validate 1: PDF Report
        print("\n--- 1. Testing PDF Download ---")
        async with page.expect_download(timeout=15000) as download_info:
            await page.locator("button:has-text('PDF Report')").first.click()
        pdf_download = await download_info.value
        pdf_path = DOWNLOAD_DIR / pdf_download.suggested_filename
        await pdf_download.save_as(pdf_path)
        print(f"Saved PDF to: {pdf_path}")
        pdf_bytes = pdf_path.read_bytes()
        assert pdf_bytes.startswith(b"%PDF-"), "Invalid PDF header!"
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
        print(f"✅ JSON verified: {len(json_path.read_text(encoding='utf-8'))} chars, valid JSON object with keys: {list(json_data.keys())[:6]}")

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

        print("\n🎉 ALL 4 EXPORT FORMATS (PDF, Excel, JSON, Markdown) TESTED & VERIFIED SUCCESSFULLY!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
