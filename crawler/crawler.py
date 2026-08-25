import asyncio
import json
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse

from playwright.async_api import async_playwright

from network import NetworkMonitor


class WebsiteCrawler:

    def __init__(self, start_url, max_pages=30):
        self.start_url = self.normalize_url(start_url)
        self.max_pages = max_pages

        parsed = urlparse(self.start_url)
        self.domain = parsed.netloc

        self.visited = set()
        self.queue = [self.start_url]
        self.pages = []

        os.makedirs("screenshots", exist_ok=True)
        os.makedirs("results", exist_ok=True)

    def normalize_url(self, url):
        """
        Normalize a URL to a canonical form.
        
        Rules:
        - Lowercase scheme and netloc
        - Remove URL fragments
        - Root paths become "/"
        - Non-root paths have trailing slashes removed
        - Query parameters are preserved
        """
        parsed = urlparse(url)

        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove trailing slashes from path, but keep "/" for root
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Preserve query parameters
        query = parsed.query

        # Reconstruct the URL without fragment
        if query:
            return f"{scheme}://{netloc}{path}?{query}"
        else:
            return f"{scheme}://{netloc}{path}"

    def is_internal_url(self, url):
        """Check if URL belongs to the target domain."""
        parsed = urlparse(url)

        return (
            parsed.scheme in ("http", "https")
            and parsed.netloc.lower() == self.domain.lower()
        )

    async def crawl(self):

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True
            )

            page = await browser.new_page(
                viewport={
                    "width": 1366,
                    "height": 768
                }
            )

            monitor = NetworkMonitor()

            page.on(
                "response",
                lambda response: monitor.record_response(
                    response,
                    page.url
                )
            )

            page.on(
                "requestfailed",
                monitor.record_request_failure
            )

            page.on(
                "console",
                lambda message: monitor.record_console(
                    message,
                    page.url
                )
            )

            while self.queue and len(self.visited) < self.max_pages:

                url = self.queue.pop(0)
                
                # Normalize URL before processing
                url = self.normalize_url(url)

                if url in self.visited:
                    continue

                self.visited.add(url)

                print()
                print("=" * 70)
                print(
                    f"PAGE {len(self.visited)}/{self.max_pages}"
                )
                print(url)
                print("=" * 70)

                try:

                    response = await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=30000
                    )

                    await page.wait_for_timeout(1500)

                    status = response.status if response else None
                    title = await page.title()

                    links = await page.locator("a").all()

                    internal_links = []

                    for link in links:

                        href = await link.get_attribute("href")

                        if not href:
                            continue

                        absolute_url = urljoin(
                            url,
                            href
                        )
                        
                        # Normalize the discovered URL
                        absolute_url = self.normalize_url(absolute_url)

                        if self.is_internal_url(
                            absolute_url
                        ):
                            internal_links.append(
                                absolute_url
                            )

                            if (
                                absolute_url not in self.visited
                                and absolute_url not in self.queue
                            ):
                                self.queue.append(
                                    absolute_url
                                )

                    screenshot_path = (
                        f"screenshots/"
                        f"{len(self.visited):03d}_page.png"
                    )

                    await page.screenshot(
                        path=screenshot_path,
                        full_page=True
                    )

                    page_data = {
                        "url": url,
                        "title": title,
                        "status": status,
                        "links": len(internal_links),
                        "screenshot": screenshot_path,
                        "timestamp": datetime.now().isoformat(),
                    }

                    self.pages.append(page_data)

                    print(f"Title: {title}")
                    print(f"HTTP status: {status}")
                    print(
                        f"Internal links: "
                        f"{len(internal_links)}"
                    )
                    print(
                        f"Screenshot: "
                        f"{screenshot_path}"
                    )

                except Exception as error:

                    print(f"ERROR: {error}")

            await browser.close()

        result = {
            "target": self.start_url,
            "pages_crawled": len(self.pages),
            "pages": self.pages,
            "http_errors": monitor.http_errors,
            "network_failures": monitor.network_failures,
            "console_errors": monitor.console_errors,
        }

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_file = (
            f"results/"
            f"crawl_{timestamp}.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                result,
                file,
                indent=2,
                ensure_ascii=False
            )

        print()
        print("=" * 70)
        print("CRAWL COMPLETE")
        print("=" * 70)

        print(f"Pages: {len(self.pages)}")
        print(
            f"HTTP errors: "
            f"{len(monitor.http_errors)}"
        )
        print(
            f"Network failures: "
            f"{len(monitor.network_failures)}"
        )
        print(
            f"Console errors: "
            f"{len(monitor.console_errors)}"
        )
        print(f"Result: {output_file}")

        return result


async def main():

    crawler = WebsiteCrawler(
        "https://dplms.com",
        max_pages=30
    )

    await crawler.crawl()


if __name__ == "__main__":
    asyncio.run(main())