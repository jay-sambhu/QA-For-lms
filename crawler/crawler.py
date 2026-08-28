import asyncio
import json
import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from .network import NetworkMonitor
from .devices import DeviceConfigManager

# Schemes we are willing to fetch. Everything else (mailto:, tel:,
# javascript:, data: ...) is left untouched and treated as external.
FETCHABLE_SCHEMES = ("http", "https")

DEFAULT_PORTS = {"http": "80", "https": "443"}


class WebsiteCrawler:

    def __init__(self, start_url, max_pages=30, auth_token=None,
                 output_dir=None, run_id=None, progress_cb=None):
        self.start_url = self.normalize_url(start_url)
        self.progress_cb = progress_cb

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

            devices_config = DeviceConfigManager.get_devices_config(p)

            contexts = {}
            pages = {}

            for dev_name, dev_config in devices_config.items():
                # Make a copy so we don't mutate the global playwright device configs
                ctx_kwargs = dict(dev_config)
                if self.auth_token:
                    ctx_kwargs["extra_http_headers"] = {"Authorization": f"Bearer {self.auth_token}"}
                
                context = await browser.new_context(**ctx_kwargs)
                page = await context.new_page()
                
                page.on(
                    "response",
                    lambda response, n=dev_name, p=page: monitor.record_response(
                        response,
                        f"{p.url} [{n}]"
                    )
                )

                page.on(
                    "requestfailed",
                    lambda request, n=dev_name, p=page: monitor.record_request_failure(
                        request,
                        f"{p.url} [{n}]"
                    )
                )

                page.on(
                    "console",
                    lambda message, n=dev_name, p=page: monitor.record_console(
                        message,
                        f"{p.url} [{n}]"
                    )
                )
                
                contexts[dev_name] = context
                pages[dev_name] = page

            try:
                while self.queue and len(self.visited) < self.max_pages:

                    url = self.queue.pop(0)

                    url = self.normalize_url(url)

                    if url in self.visited:
                        continue

                    self.visited.add(url)
                    
                    if self.progress_cb:
                        pct = int((len(self.visited) / self.max_pages) * 60)
                        self.progress_cb(pct, f"Crawling page {len(self.visited)} of {self.max_pages}")

                    print()
                    print("=" * 70)
                    print(
                        f"PAGE {len(self.visited)}/{self.max_pages}"
                    )
                    print(url)
                    print("=" * 70)
                    
                    # Navigate Desktop first to extract internal links
                    for dev_name, page in pages.items():
                        try:
                            # Use f"{url} [{dev_name}]" as the canonical page ID for this device
                            page_id = f"{url} [{dev_name}]"
                            print(f"[{dev_name}] Navigating...")
                            response = await page.goto(
                                url,
                                wait_until="domcontentloaded",
                                timeout=30000
                            )

                            await page.wait_for_timeout(1500)

                            status = response.status if response else None
                            title = await page.title()
                            
                            # Execute deterministic responsive checks in page JS
                            responsive_checks = {"horizontal_overflow": False, "overflow_pixels": 0, "elements_outside_viewport": 0, "forms_outside_viewport": 0, "clipped_buttons": 0, "navigation_visible": True, "viewport_width": 1366, "viewport_height": 768}
                            try:
                                responsive_checks = await page.evaluate("""() => {
                                    const docWidth = document.documentElement ? document.documentElement.scrollWidth : 0;
                                    const winWidth = window.innerWidth || 1000;
                                    const winHeight = window.innerHeight || 800;
                                    const overflowPixels = Math.max(0, docWidth - winWidth);
                                    const hasHorizontalOverflow = docWidth > (winWidth + 5);

                                    let elementsOutside = 0;
                                    let formsOutside = 0;
                                    let clippedButtons = 0;

                                    const elements = Array.from(document.querySelectorAll('button, a, input, select, form, [role="button"], img, h1, h2, h3, header, nav'));
                                    for (const el of elements) {
                                        try {
                                            const rect = el.getBoundingClientRect();
                                            if (!rect || (rect.width === 0 && rect.height === 0)) continue;
                                            
                                            if (rect.right > (winWidth + 10) || rect.left < -10) {
                                                elementsOutside++;
                                                const tag = (el.tagName || '').toUpperCase();
                                                if (tag === 'FORM' || tag === 'INPUT' || tag === 'SELECT') {
                                                    formsOutside++;
                                                }
                                                if (tag === 'BUTTON' || tag === 'A' || el.getAttribute('role') === 'button') {
                                                    clippedButtons++;
                                                }
                                            }
                                        } catch (e) {}
                                    }

                                    const nav = document.querySelector('nav, header, [role="navigation"]');
                                    let navVisible = false;
                                    if (nav) {
                                        try {
                                            const rect = nav.getBoundingClientRect();
                                            navVisible = rect && rect.width > 0 && rect.height > 0 && rect.top < winHeight && rect.bottom > 0;
                                        } catch (e) {}
                                    }

                                    return {
                                        horizontal_overflow: hasHorizontalOverflow,
                                        overflow_pixels: overflowPixels,
                                        elements_outside_viewport: elementsOutside,
                                        forms_outside_viewport: formsOutside,
                                        clipped_buttons: clippedButtons,
                                        navigation_visible: navVisible,
                                        viewport_width: winWidth,
                                        viewport_height: winHeight
                                    };
                                }""")
                            except Exception as ev_err:
                                print(f"Responsive check warning on {dev_name}: {ev_err}")

                            internal_links = []
                            
                            # Only extract links on Desktop Chrome to avoid duplication
                            if dev_name == "Desktop Chrome":
                                links = await page.locator("a").all()
                                for link in links:
                                    href = await link.get_attribute("href")
                                    if not href:
                                        continue

                                    absolute_url = urljoin(url, href)
                                    absolute_url = self.normalize_url(absolute_url)

                                    if self.is_internal_url(absolute_url):
                                        internal_links.append(absolute_url)
                                        if (
                                            absolute_url not in self.visited
                                            and absolute_url not in self.queue
                                        ):
                                            self.queue.append(absolute_url)

                            safe_dev_name = dev_name.replace(" ", "_")
                            screenshot_path = os.path.join(
                                self.screenshot_dir,
                                f"{len(self.visited):03d}_{safe_dev_name}_page.png"
                            )

                            await page.screenshot(
                                path=screenshot_path,
                                full_page=True
                            )

                            rel_screenshot = os.path.relpath(
                                screenshot_path, self.base_dir
                            )

                            page_data = {
                                "url": page_id,
                                "actual_url": url,
                                "device": dev_name,
                                "title": title,
                                "status": status,
                                "links": len(internal_links),
                                "screenshot": rel_screenshot,
                                "responsive_checks": responsive_checks,
                                "timestamp": datetime.now().isoformat(),
                            }

                            self.pages.append(page_data)

                        except Exception as error:
                            print(f"ERROR on {dev_name}: {error}")
                            self.pages.append({
                                "url": f"{url} [{dev_name}]",
                                "actual_url": url,
                                "device": dev_name,
                                "title": None,
                                "status": None,
                                "links": 0,
                                "screenshot": None,
                                "error": str(error),
                                "timestamp": datetime.now().isoformat(),
                            })
            finally:
                for context in contexts.values():
                    await context.close()
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