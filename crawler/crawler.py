import asyncio
import json
import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from .network import NetworkMonitor

# Schemes we are willing to fetch. Everything else (mailto:, tel:,
# javascript:, data: ...) is left untouched and treated as external.
FETCHABLE_SCHEMES = ("http", "https")

DEFAULT_PORTS = {"http": "80", "https": "443"}


class WebsiteCrawler:

    def __init__(self, start_url, max_pages=30, auth_token=None,
                 output_dir=None, run_id=None):
        self.start_url = self.normalize_url(start_url)

        parsed = urlparse(self.start_url)
        if parsed.scheme not in FETCHABLE_SCHEMES or not parsed.netloc:
            raise ValueError(
                f"Invalid start URL {start_url!r}: expected an absolute "
                f"http(s) URL such as 'https://example.com'."
            )

        self.max_pages = max_pages
        self.auth_token = auth_token

        self.domain = parsed.netloc
        # Compare on the registrable-ish host, ignoring a leading "www.",
        # so apex and www are treated as the same site.
        self.base_host = self._base_host(self.start_url)

        self.visited = set()
        self.queue = [self.start_url]
        self.pages = []

        # Every run gets its own screenshot sub-directory, otherwise reruns
        # overwrite earlier images and older reports end up pointing at the
        # wrong screenshots.
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        base = os.path.abspath(output_dir) if output_dir else os.getcwd()
        self.base_dir = base
        self.results_dir = os.path.join(base, "results")
        self.screenshot_dir = os.path.join(base, "screenshots", self.run_id)

        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)

    @staticmethod
    def _safe_port(parsed):
        """Return parsed.port, or None if the port is not a valid integer.

        `urlparse(...).port` raises ValueError on input like
        'http://host:port/' (a template placeholder that really does appear in
        hrefs). Callers must never propagate that out of URL handling.
        """
        try:
            return parsed.port
        except ValueError:
            return None

    @classmethod
    def _base_host(cls, url):
        """Return the comparable host: lowercased, no 'www.', non-default port kept.

        The port is part of site identity. Dropping it made
        http://localhost:8000 look internal to a crawl of http://localhost:3000,
        so the crawler would wander from a dev frontend into its own API.
        """
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if host.startswith("www."):
            host = host[4:]

        port = cls._safe_port(parsed)
        if port is not None and str(port) != DEFAULT_PORTS.get(parsed.scheme.lower()):
            host = f"{host}:{port}"

        return host

    def normalize_url(self, url):
        """
        Normalize a URL to a canonical form.

        Rules:
        - Lowercase scheme and host (but never the userinfo or the path)
        - Drop the default port for the scheme (:80 for http, :443 for https)
        - Remove URL fragments
        - Collapse duplicate slashes in the path
        - Root paths become "/"; non-root paths have trailing slashes removed
        - Query parameters are preserved
        - Non-http(s) URLs (mailto:, javascript:, ...) are returned unchanged
        """
        if url is None:
            return ""

        url = str(url).strip()
        if not url:
            return ""

        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        # Leave non-fetchable schemes alone; mangling them into "mailto://..."
        # produces nonsense URLs.
        if scheme and scheme not in FETCHABLE_SCHEMES:
            return url

        # Lowercase only the host, preserving any userinfo verbatim so that
        # credentials are not corrupted.
        userinfo = ""
        hostpart = parsed.netloc
        if "@" in hostpart:
            userinfo, hostpart = hostpart.rsplit("@", 1)
            userinfo += "@"

        host = parsed.hostname or ""
        host = host.lower().rstrip(".")

        port = self._safe_port(parsed)
        if port is not None and str(port) != DEFAULT_PORTS.get(scheme):
            host = f"{host}:{port}"

        netloc = f"{userinfo}{host}"

        # Collapse duplicate slashes, then trim trailing slashes.
        path = re.sub(r"/{2,}", "/", parsed.path)
        path = path.rstrip("/")
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
        """Check if URL belongs to the target site (apex and www are equal)."""
        parsed = urlparse(url)

        return (
            parsed.scheme in FETCHABLE_SCHEMES
            and self._base_host(url) == self.base_host
        )

    async def crawl(self):

        # Created up front so the summary below always has a monitor to read,
        # regardless of where the event listeners are attached.
        monitor = NetworkMonitor()

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True
            )

            kwargs = {
                "viewport": {
                    "width": 1366,
                    "height": 768
                }
            }
            if self.auth_token:
                kwargs["extra_http_headers"] = {"Authorization": f"Bearer {self.auth_token}"}

            page = await browser.new_page(**kwargs)

            page.on(
                "response",
                lambda response: monitor.record_response(
                    response,
                    page.url
                )
            )

            page.on(
                "requestfailed",
                lambda request: monitor.record_request_failure(
                    request,
                    page.url
                )
            )

            page.on(
                "console",
                lambda message: monitor.record_console(
                    message,
                    page.url
                )
            )

            try:
                while self.queue and len(self.visited) < self.max_pages:

                    url = self.queue.pop(0)

                    # Queue entries are already normalized, but normalize again
                    # so externally-seeded queues stay canonical.
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

                        screenshot_path = os.path.join(
                            self.screenshot_dir,
                            f"{len(self.visited):03d}_page.png"
                        )

                        await page.screenshot(
                            path=screenshot_path,
                            full_page=True
                        )

                        # Relative to the output base, not the CWD. Reports and
                        # screenshots share that base, so this keeps the paths
                        # valid regardless of where the pipeline was launched.
                        rel_screenshot = os.path.relpath(
                            screenshot_path, self.base_dir
                        )

                        page_data = {
                            "url": url,
                            "title": title,
                            "status": status,
                            "links": len(internal_links),
                            "screenshot": rel_screenshot,
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
                            f"{rel_screenshot}"
                        )

                    except Exception as error:

                        print(f"ERROR: {error}")

                        self.pages.append({
                            "url": url,
                            "title": None,
                            "status": None,
                            "links": 0,
                            "screenshot": None,
                            "error": str(error),
                            "timestamp": datetime.now().isoformat(),
                        })
            finally:
                await browser.close()

        successful_pages = [p for p in self.pages if not p.get("error")]

        result = {
            "target": self.start_url,
            "run_id": self.run_id,
            "pages_crawled": len(successful_pages),
            "pages_attempted": len(self.pages),
            "pages": self.pages,
            "http_errors": monitor.http_errors,
            "network_failures": monitor.network_failures,
            "console_errors": monitor.console_errors,
        }

        output_file = os.path.join(
            self.results_dir,
            f"crawl_{self.run_id}.json"
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

        result["output_file"] = output_file

        print()
        print("=" * 70)
        print("CRAWL COMPLETE")
        print("=" * 70)

        print(f"Pages: {len(successful_pages)}")
        if len(self.pages) != len(successful_pages):
            print(
                f"Pages failed: "
                f"{len(self.pages) - len(successful_pages)}"
            )
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
        max_pages=30,
        auth_token=None
    )

    await crawler.crawl()


if __name__ == "__main__":
    asyncio.run(main())