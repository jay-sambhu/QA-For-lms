import asyncio
import json
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from playwright.async_api import async_playwright


BASE_URL = "https://dplms.com/"
MAX_PAGES = 30

RESULTS_DIR = Path("results")
SCREENSHOTS_DIR = Path("screenshots")

RESULTS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def normalize_url(url: str) -> str:
    """
    Normalize a URL so the crawler does not visit the same
    page multiple times because of fragments or trailing slashes.
    """
    url, _ = urldefrag(url)

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower() if parsed.hostname else ""

    path = parsed.path or "/"

    if path != "/" and path.endswith("/"):
        path = path[:-1]

    return f"{scheme}://{hostname}{path}"


def is_internal_url(url: str) -> bool:
    """
    Only allow URLs belonging to dplms.com.
    """
    try:
        parsed = urlparse(url)

        return (
            parsed.scheme in ("http", "https")
            and parsed.hostname is not None
            and parsed.hostname.lower() == "dplms.com"
        )

    except Exception:
        return False


def should_skip_url(url: str) -> bool:
    """
    Skip files and special URLs that aren't useful for
    normal website exploration.
    """

    parsed = urlparse(url)
    path = parsed.path.lower()

    blocked_extensions = (
        ".pdf",
        ".zip",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".mp4",
        ".mp3",
        ".css",
        ".js",
        ".xml",
    )

    if path.endswith(blocked_extensions):
        return True

    return False


async def extract_page_data(page, url, screenshot_path, console_errors, network_errors):

    title = await page.title()

    headings = await page.locator("h1, h2, h3, h4, h5, h6").evaluate_all(
        """
        elements => elements.map(e => ({
            tag: e.tagName.toLowerCase(),
            text: e.innerText.trim()
        })).filter(x => x.text)
        """
    )

    links = await page.locator("a[href]").evaluate_all(
        """
        elements => elements.map(a => ({
            text: a.innerText.trim(),
            href: a.href
        }))
        """
    )

    buttons = await page.locator("button, input[type='button'], input[type='submit']").evaluate_all(
        """
        elements => elements.map(b => ({
            text: (b.innerText || b.value || '').trim(),
            type: b.getAttribute('type'),
            aria_label: b.getAttribute('aria-label')
        }))
        """
    )

    forms = await page.locator("form").evaluate_all(
        """
        forms => forms.map(form => ({
            action: form.action,
            method: form.method,
            inputs: Array.from(
                form.querySelectorAll('input, textarea, select')
            ).map(input => ({
                tag: input.tagName.toLowerCase(),
                type: input.type || null,
                name: input.name || null,
                placeholder: input.placeholder || null,
                required: input.required
            }))
        }))
        """
    )

    inputs = await page.locator(
        "input, textarea, select"
    ).evaluate_all(
        """
        elements => elements.map(input => ({
            tag: input.tagName.toLowerCase(),
            type: input.type || null,
            name: input.name || null,
            placeholder: input.placeholder || null,
            aria_label: input.getAttribute('aria-label'),
            required: input.required
        }))
        """
    )

    # Capture screenshot
    await page.screenshot(
        path=str(screenshot_path),
        full_page=True
    )

    return {
        "url": url,
        "final_url": page.url,
        "title": title,
        "headings": headings,
        "links": links,
        "buttons": buttons,
        "forms": forms,
        "inputs": inputs,
        "console_errors": console_errors,
        "network_errors": network_errors,
        "screenshot": str(screenshot_path),
    }


async def main():

    visited = set()
    queue = deque([normalize_url(BASE_URL)])

    pages = []
    all_links = set()
    all_console_errors = []
    all_network_errors = []

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=False
        )

        context = await browser.new_context(
            viewport={
                "width": 1366,
                "height": 768,
            }
        )

        page = await context.new_page()

        while queue and len(visited) < MAX_PAGES:

            url = queue.popleft()

            if url in visited:
                continue

            if not is_internal_url(url):
                continue

            if should_skip_url(url):
                continue

            visited.add(url)

            print()
            print("=" * 70)
            print(f"PAGE {len(visited)}/{MAX_PAGES}")
            print(url)
            print("=" * 70)

            console_errors = []
            network_errors = []

            def handle_console(message):
                if message.type == "error":
                    console_errors.append({
                        "type": message.type,
                        "text": message.text
                    })

            def handle_request_failed(request):
                network_errors.append({
                    "url": request.url,
                    "method": request.method,
                    "failure": request.failure
                })

            page.on("console", handle_console)
            page.on("requestfailed", handle_request_failed)

            try:

                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                await page.wait_for_timeout(1500)

                status = response.status if response else None

                screenshot_name = (
                    f"{len(visited):03d}_page.png"
                )

                screenshot_path = (
                    SCREENSHOTS_DIR / screenshot_name
                )

                data = await extract_page_data(
                    page,
                    url,
                    screenshot_path,
                    console_errors,
                    network_errors
                )

                data["http_status"] = status

                pages.append(data)

                print(f"Title: {data['title']}")
                print(f"HTTP status: {status}")
                print(f"Links: {len(data['links'])}")
                print(f"Buttons: {len(data['buttons'])}")
                print(f"Forms: {len(data['forms'])}")
                print(f"Inputs: {len(data['inputs'])}")
                print(f"Console errors: {len(console_errors)}")
                print(f"Network errors: {len(network_errors)}")
                print(f"Screenshot: {screenshot_path}")

                # Collect new internal links
                for link in data["links"]:

                    href = link.get("href")

                    if not href:
                        continue

                    normalized = normalize_url(href)

                    if not is_internal_url(normalized):
                        continue

                    if should_skip_url(normalized):
                        continue

                    all_links.add(normalized)

                    if (
                        normalized not in visited
                        and normalized not in queue
                        and len(visited) + len(queue) < MAX_PAGES
                    ):
                        queue.append(normalized)

                all_console_errors.extend(
                    [
                        {
                            "page": url,
                            **error
                        }
                        for error in console_errors
                    ]
                )

                all_network_errors.extend(
                    [
                        {
                            "page": url,
                            **error
                        }
                        for error in network_errors
                    ]
                )

            except Exception as error:

                print(f"ERROR: {error}")

                pages.append({
                    "url": url,
                    "error": str(error)
                })

            finally:

                # Remove listeners before moving to another page.
                try:
                    page.remove_listener(
                        "console",
                        handle_console
                    )
                    page.remove_listener(
                        "requestfailed",
                        handle_request_failed
                    )
                except Exception:
                    pass

        await browser.close()

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    exploration = {
        "target": BASE_URL,
        "started": timestamp,
        "max_pages": MAX_PAGES,
        "pages_crawled": len(pages),
        "pages": pages,
        "links": sorted(all_links),
        "console_errors": all_console_errors,
        "network_errors": all_network_errors,
    }

    output_file = (
        RESULTS_DIR /
        f"exploration_{timestamp}.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            exploration,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)
    print("CRAWL COMPLETE")
    print("=" * 70)

    print(f"Pages crawled: {len(pages)}")
    print(f"Links discovered: {len(all_links)}")
    print(
        f"Console errors: "
        f"{len(all_console_errors)}"
    )
    print(
        f"Network errors: "
        f"{len(all_network_errors)}"
    )

    print()
    print(f"Results: {output_file}")
    print(f"Screenshots: {SCREENSHOTS_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
