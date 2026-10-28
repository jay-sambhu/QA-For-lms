import sys
import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import inspect
from playwright.async_api import async_playwright

from .network import NetworkMonitor
from .devices import DeviceConfigManager

logger = logging.getLogger(__name__)

async def _safe_wait_load_state(page, state="networkidle", timeout=3000):
    """Safely wait for page load state without failing if unsupported or mocked."""
    if hasattr(page, "wait_for_load_state"):
        try:
            res = page.wait_for_load_state(state, timeout=timeout)
            if inspect.isawaitable(res):
                await res
        except Exception:
            pass

# Schemes we are willing to fetch. Everything else (mailto:, tel:,
# javascript:, data: ...) is left untouched and treated as external.
FETCHABLE_SCHEMES = ("http", "https")

DEFAULT_PORTS = {"http": "80", "https": "443"}

# Short aliases accepted in QA_VIEWPORTS (comma separated) to limit which
# device profiles are crawled. Each extra viewport is another full render +
# screenshot per page; on a 1 GB droplet "desktop" alone is the safe choice.
VIEWPORT_ALIASES = {
    "desktop": "Desktop Chrome",
    "mobile": "iPhone 13",
    "iphone": "iPhone 13",
    "tablet": "iPad (gen 7)",
    "ipad": "iPad (gen 7)",
}

# A redirect landing on one of these paths means the requested page sits
# behind a login wall.
AUTH_PATH_RE = re.compile(r"/(login|log-in|signin|sign-in|sign_in|auth|sso|oauth|account/login|users/sign_in)(/|$|\?)", re.I)

# Buttons whose accessible name suggests a state change on the customer's
# site. Click exploration (opt-in) never presses these.
DANGEROUS_CLICK_RE = re.compile(
    r"log ?out|sign ?out|delete|remove|submit|pay|buy|checkout|send|confirm|unsubscribe|cancel|purchase|order|apply",
    re.I,
)

# Maximum full-page capture height in CSS pixels. Chromium rasterises the
# whole clip in memory (width x height x 4 bytes), so an infinite-scroll page
# is capped instead of exhausting the worker's memory limit.
DEFAULT_SCREENSHOT_MAX_HEIGHT = 6000

# JavaScript evaluated in the page for the deterministic responsive and
# accessibility checks. Only elements that are rendered, visible, not hidden
# by an overflow-clipping ancestor and not deliberately off-canvas count as
# "outside the viewport"; otherwise every mobile drawer, carousel slide and
# collapsed menu on a normal site produced a HIGH finding.
RESPONSIVE_CHECK_JS = """() => {
    const docEl = document.documentElement;
    const docWidth = docEl ? docEl.scrollWidth : 0;
    const winWidth = window.innerWidth || 1000;
    const winHeight = window.innerHeight || 800;
    const overflowPixels = Math.max(0, docWidth - winWidth);
    const hasHorizontalOverflow = docWidth > (winWidth + 5);

    const isVisible = (el) => {
        try {
            if (typeof el.checkVisibility === 'function') {
                if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return false;
            } else {
                const cs = getComputedStyle(el);
                if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return false;
            }
        } catch (e) { return false; }
        if (el.getAttribute('aria-hidden') === 'true' || el.getAttribute('tabindex') === '-1') return false;
        if (el.closest('[aria-hidden="true"], [hidden], [inert]')) return false;
        return true;
    };

    const clippedByAncestor = (el, rect) => {
        let node = el.parentElement;
        while (node && node !== document.body && node !== docEl) {
            let cs;
            try { cs = getComputedStyle(node); } catch (e) { break; }
            const ox = cs.overflowX, oy = cs.overflowY;
            if (ox !== 'visible' || oy !== 'visible' || cs.clipPath !== 'none' || cs.contain.includes('paint')) {
                const r = node.getBoundingClientRect();
                if (rect.left >= r.right - 1 || rect.right <= r.left + 1 || rect.top >= r.bottom - 1 || rect.bottom <= r.top + 1) {
                    return true;
                }
                if (ox === 'hidden' || ox === 'clip' || ox === 'auto' || ox === 'scroll') {
                    if (rect.right > r.right + 1 || rect.left < r.left - 1) return true;
                }
            }
            node = node.parentElement;
        }
        return false;
    };

    let elementsOutside = 0;
    let formsOutside = 0;
    let clippedButtons = 0;
    const samples = [];

    const elements = Array.from(document.querySelectorAll('button, a, input, select, form, [role="button"], img, h1, h2, h3, header, nav'));
    for (const el of elements) {
        try {
            const rect = el.getBoundingClientRect();
            if (!rect || (rect.width === 0 && rect.height === 0)) continue;
            if (rect.bottom < 0 || rect.top > Math.max(winHeight * 4, 4000)) continue;
            const outsideRight = rect.right > (winWidth + 10) && rect.left < winWidth;
            const outsideLeft = rect.left < -10 && rect.right > 0;
            if (!outsideRight && !outsideLeft) continue;
            if (!isVisible(el)) continue;
            if (clippedByAncestor(el, rect)) continue;
            const cs = getComputedStyle(el);
            if (cs.position === 'fixed' && (cs.transform !== 'none' || cs.translate !== 'none')) continue;

            elementsOutside++;
            const tag = (el.tagName || '').toUpperCase();
            if (tag === 'FORM' || tag === 'INPUT' || tag === 'SELECT') formsOutside++;
            if (tag === 'BUTTON' || tag === 'A' || el.getAttribute('role') === 'button') clippedButtons++;
            if (samples.length < 5) {
                const text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('alt') || '').trim().slice(0, 40);
                samples.push(`${tag.toLowerCase()}${el.id ? '#' + el.id : ''}${text ? ' "' + text + '"' : ''} right=${Math.round(rect.right)}`);
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
        viewport_height: winHeight,
        samples: samples
    };
}"""

# Cheap, deterministic accessibility counts. Only rules that can be judged
# from the DOM without heuristics; the perf/a11y engine turns them into
# violations.
A11Y_CHECK_JS = """() => {
    const visible = (el) => {
        try { return el.getClientRects().length > 0; } catch (e) { return false; }
    };
    const imgs = Array.from(document.images || []);
    const imagesMissingAlt = imgs.filter(i => visible(i) && !i.hasAttribute('alt') && i.getAttribute('role') !== 'presentation').length;
    const inputs = Array.from(document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]), select, textarea'));
    const inputsWithoutLabel = inputs.filter(i => {
        if (!visible(i)) return false;
        if (i.getAttribute('aria-label') || i.getAttribute('aria-labelledby') || i.getAttribute('title')) return false;
        if (i.id && document.querySelector(`label[for="${CSS.escape(i.id)}"]`)) return false;
        return !i.closest('label');
    }).length;
    const buttons = Array.from(document.querySelectorAll('button, [role="button"], a[href]'));
    const controlsWithoutName = buttons.filter(b => {
        if (!visible(b)) return false;
        const name = (b.innerText || '').trim() || b.getAttribute('aria-label') || b.getAttribute('aria-labelledby') || b.getAttribute('title');
        if (name) return false;
        const img = b.querySelector('img[alt], svg[aria-label], svg title');
        return !img;
    }).length;
    return {
        images_missing_alt: imagesMissingAlt,
        inputs_without_label: inputsWithoutLabel,
        controls_without_name: controlsWithoutName,
        has_lang: !!(document.documentElement.getAttribute('lang') || '').trim(),
        has_title: !!(document.title || '').trim(),
        h1_count: document.querySelectorAll('h1').length,
        has_main_landmark: !!document.querySelector('main, [role="main"]'),
        total_images: imgs.length,
        total_inputs: inputs.length
    };
}"""

# Real navigation timings from the Navigation Timing API. Values are 0 until
# the corresponding event fires, which the caller turns into null.
TIMING_JS = """() => {
    const entries = performance.getEntriesByType ? performance.getEntriesByType('navigation') : [];
    const n = entries && entries[0];
    if (!n) return null;
    const resources = performance.getEntriesByType('resource') || [];
    let slow = 0;
    let bytes = 0;
    for (const r of resources) {
        if (r.duration > 1000) slow++;
        bytes += r.transferSize || 0;
    }
    return {
        dom_content_loaded_ms: Math.round(n.domContentLoadedEventEnd || 0),
        load_event_ms: Math.round(n.loadEventEnd || 0),
        response_end_ms: Math.round(n.responseEnd || 0),
        ttfb_ms: Math.round(n.responseStart || 0),
        transfer_size: n.transferSize || 0,
        resource_count: resources.length,
        resource_bytes: bytes,
        slow_resources: slow
    };
}"""

LOGIN_FORM_ERROR_JS = """() => {
    const visible = (el) => {
        try {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
        } catch (e) { return false; }
    };
    const scopes = [];
    for (const f of document.querySelectorAll('form')) {
        if (f.querySelector("input[type='password'], input[name*='pass' i], input[type='email'], input[name*='user' i]")) {
            scopes.push(f);
            if (f.parentElement) scopes.push(f.parentElement);
        }
    }
    if (!scopes.length) return '';
    for (const scope of scopes) {
        for (const el of scope.querySelectorAll("[role='alert'], .error, [class*='error' i], [class*='invalid' i], [aria-invalid='true'], .alert-danger")) {
            const text = (el.innerText || el.textContent || '').trim();
            if (text && visible(el)) return text.slice(0, 160);
        }
    }
    return '';
}"""

PASSWORD_VISIBLE_JS = """() => {
    for (const el of document.querySelectorAll("input[type='password']")) {
        try {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) return true;
        } catch (e) {}
    }
    return false;
}"""


def _chromium_launch_args():
    """Memory-lean Chromium flags for small hosts."""
    args = [
        "--disable-dev-shm-usage",  # /dev/shm is 64 MB in Docker
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-sync",
        "--mute-audio",
        "--no-first-run",
        "--no-default-browser-check",
        f"--renderer-process-limit={max(1, int(os.environ.get('QA_RENDERER_PROCESS_LIMIT', '2')))}",
    ]
    # The image runs as a non-root user under Docker's default seccomp
    # profile, where Chromium's sandbox usually cannot start, so it stays
    # disabled unless explicitly enabled.
    if os.environ.get("PLAYWRIGHT_CHROMIUM_SANDBOX", "").lower() != "true":
        args += ["--no-sandbox", "--disable-setuid-sandbox"]
    return args


def _selected_devices(devices_config):
    raw = (os.environ.get("QA_VIEWPORTS") or "all").strip().lower()
    if raw in ("", "all", "*"):
        return devices_config
    wanted = set()
    for token in raw.split(","):
        token = token.strip()
        if token:
            wanted.add(VIEWPORT_ALIASES.get(token, token))
    selected = {k: v for k, v in devices_config.items() if k.lower() in {w.lower() for w in wanted}}
    return selected or devices_config


def _env_flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name, default):
    try:
        return int((os.environ.get(name) or "").strip() or default)
    except ValueError:
        return default


def default_crawl_budget_seconds():
    """Wall-clock budget for the crawl: 60% of the pipeline timeout so the
    detector, AI triage and report stages still fit before the API kills the
    subprocess."""
    explicit = _env_int("QA_CRAWL_BUDGET_SECONDS", 0)
    if explicit > 0:
        return explicit
    return int(_env_int("QA_PIPELINE_TIMEOUT", 1800) * 0.6)


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


class WebsiteCrawler:

    def __init__(self, start_url, max_pages=30, auth_token=None,
                 output_dir=None, run_id=None, progress_cb=None,
                 login_url=None, username=None, password=None,
                 deadline=None, explore_clicks=None):
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
        self.login_url = self.normalize_url(login_url) if login_url else None
        self.username = username
        self.password = password
        self.auth_test_cases = []
        self.auth_findings = []

        # time.monotonic() value after which no new page is started. None
        # means "use the default budget" (see default_crawl_budget_seconds).
        self.deadline = deadline
        self.partial = False
        self.explore_clicks = _env_flag("QA_EXPLORE_CLICKS", False) if explore_clicks is None else bool(explore_clicks)

        self.domain = parsed.netloc
        # Compare on the registrable-ish host, ignoring a leading "www.",
        # so apex and www are treated as the same site.
        self.base_host = self._base_host(self.start_url)

        self.visited = set()
        self.queue = [self.start_url]
        # Mirror of self.queue for O(1) membership checks.
        self.queued = {self.start_url}
        self.discovered_links = set()
        self.pages = []
        self._private_hosts = {}

        # Every run gets its own screenshot sub-directory, otherwise reruns
        # overwrite earlier images and older reports end up pointing at the
        # wrong screenshots.
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        base = os.path.abspath(output_dir) if output_dir else os.getcwd()
        self.base_dir = base
        self.results_dir = os.path.join(base, "results")
        self.screenshot_dir = os.path.join(base, "screenshots", self.run_id)
        self.output_file = os.path.join(self.results_dir, f"crawl_{self.run_id}.json")

        self.screenshot_lossless = _env_flag("QA_SCREENSHOT_LOSSLESS", False)
        self.screenshot_quality = max(30, min(95, _env_int("QA_SCREENSHOT_QUALITY", 70)))
        self.screenshot_max_height = max(1000, _env_int("QA_SCREENSHOT_MAX_HEIGHT", DEFAULT_SCREENSHOT_MAX_HEIGHT))

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

    async def _host_is_private(self, host):
        """Resolve `host` (once per run) and tell whether it maps to a private
        address. Literal checks run inline; DNS runs in a thread so the route
        handler never blocks the event loop."""
        from security.url_guard import is_blocked_host, resolve_private_reason

        key = (host or "").lower()
        if is_blocked_host(key):
            return True
        cached = self._private_hosts.get(key)
        if cached is not None:
            return cached
        try:
            reason = await asyncio.to_thread(resolve_private_reason, key)
        except Exception:
            reason = None
        self._private_hosts[key] = bool(reason)
        if reason:
            logger.warning("Blocked host during crawl: %s", reason)
        return bool(reason)

    def _build_route_handler(self, block_private: bool):
        """Route handler: same-site-only auth header + private network block.

        Every browser-initiated request (navigations, redirects, subresources)
        passes through here, so a target that 302s to an internal address or a
        DNS name pointing at 10.x is aborted before Chromium connects."""

        async def _handler(route, request=None):
            req = request or route.request
            req_url = req.url
            parsed = urlparse(req_url)
            if parsed.scheme in FETCHABLE_SCHEMES:
                if block_private and await self._host_is_private(parsed.hostname):
                    logger.warning("Blocked request to private address: %s", req_url)
                    await route.abort("blockedbyclient")
                    return
                if self.auth_token and self.is_internal_url(req_url):
                    headers = dict(req.headers)
                    headers["authorization"] = f"Bearer {self.auth_token}"
                    await route.continue_(headers=headers)
                    return
            await route.continue_()

        return _handler

    def is_internal_url(self, url):
        """Check if URL belongs to the target site (apex and www are equal)."""
        parsed = urlparse(url)

        return (
            parsed.scheme in FETCHABLE_SCHEMES
            and self._base_host(url) == self.base_host
        )

    def is_auth_wall(self, requested_url, final_url):
        """A navigation that ended on another site or on a login path is an
        authentication wall, not the requested page."""
        if not final_url or final_url == requested_url:
            return False
        if not self.is_internal_url(final_url):
            return True
        return bool(AUTH_PATH_RE.search(urlparse(final_url).path or ""))

    async def perform_login(self, page, dev_name: str, auto_detect: bool = False) -> dict:
        """
        Executes automated form login if login_url is provided, or if auto_detect is True.
        Returns a dict with {'success': bool, 'error': Optional[str], 'status': str}.

        Success is judged by a state change (password field gone, URL moved
        away from the login page, new cookies) and failure by an error shown
        inside the submitted form; a stray ".error" wrapper elsewhere on the
        page no longer counts as a rejected login.
        """
        if not auto_detect:
            if not self.login_url:
                return {"success": True, "status": "no_auth"}

            print(f"[{dev_name}] Performing automated login at: {self.login_url}")
            try:
                await page.goto(self.login_url, wait_until="domcontentloaded", timeout=20000)
                await _safe_wait_load_state(page, "networkidle", timeout=3000)
            except Exception as e:
                return {"success": False, "error": f"Failed to load login page: {str(e)}", "status": "errored"}

        # Detect password field to determine if this is a login form
        password_input = None
        if self.password:
            for sel in [
                "input[type='password']",
                "input[name*='pass' i]",
                "input[id*='pass' i]",
                "input[placeholder*='pass' i]",
            ]:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        password_input = el
                        break
                except Exception:
                    continue

        if auto_detect and not password_input:
            return {"success": True, "status": "no_login_form_detected"}

        # Fill username / email
        username_input = None
        if self.username:
            for sel in [
                "input[type='email']",
                "input[name='email']",
                "input[name='username']",
                "input[name='user']",
                "input[name='login']",
                "input[id='email']",
                "input[id='username']",
                "input[id='user']",
                "input[placeholder*='email' i]",
                "input[placeholder*='username' i]",
                "input[type='text']",
            ]:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        username_input = el
                        break
                except Exception:
                    continue
            if username_input:
                try:
                    await username_input.fill(self.username)
                except Exception:
                    pass

        # Fill password
        if password_input:
                try:
                    await password_input.fill(self.password)
                except Exception:
                    pass

        # Submit
        submit_btn = None
        for sel in [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Sign In')",
            "button:has-text('Log In')",
            "button:has-text('Login')",
            "button:has-text('Submit')",
        ]:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    submit_btn = el
                    break
            except Exception:
                continue

        pre_url = self.normalize_url(getattr(page, "url", "") or "")
        cookies_before = await self._cookie_count(page)

        post_status = None
        try:
            submit_action = None
            if submit_btn:
                submit_action = submit_btn.click()
            elif password_input:
                submit_action = password_input.press("Enter")
            elif username_input:
                submit_action = username_input.press("Enter")
            if submit_action is not None:
                post_status = await self._submit_and_capture_post(page, submit_action)
            await _safe_wait_load_state(page, "networkidle", timeout=3000)
        except Exception as e:
            return {"success": False, "error": f"Failed submitting login form: {str(e)}", "status": "errored"}

        # Validate outcome by state change rather than by any ".error" node
        form_error = ""
        password_visible = True
        try:
            form_error = await page.evaluate(LOGIN_FORM_ERROR_JS) or ""
        except Exception:
            form_error = ""
        try:
            password_visible = bool(await page.evaluate(PASSWORD_VISIBLE_JS))
        except Exception:
            password_visible = True

        post_url = self.normalize_url(getattr(page, "url", "") or "")
        url_changed = bool(post_url) and post_url != pre_url
        cookies_after = await self._cookie_count(page)
        cookies_grew = cookies_after > cookies_before

        if post_status is not None and post_status >= 400:
            return {"success": False, "error": f"Login request was rejected with HTTP {post_status}", "status": "errored"}
        if form_error and password_visible:
            return {"success": False, "error": f"Login form reported an error: {form_error}", "status": "errored"}
        if not password_visible or url_changed or cookies_grew:
            return {"success": True, "status": "passed"}
        return {
            "success": False,
            "error": "No session change after submitting the login form (password field still shown, URL unchanged).",
            "status": "errored",
        }

    @staticmethod
    async def _cookie_count(page):
        try:
            context = getattr(page, "context", None)
            if context is None:
                return 0
            cookies = await _maybe_await(context.cookies())
            return len(cookies or [])
        except Exception:
            return 0

    @staticmethod
    async def _submit_and_capture_post(page, submit_action):
        """Run the submit action; return the status of the POST it triggered,
        or None when the login is not a plain POST (JS/XHR login flows)."""
        if not hasattr(page, "expect_response"):
            await submit_action
            return None
        submitted = False
        try:
            async with page.expect_response(
                lambda r: r.request.method == "POST", timeout=5000
            ) as response_info:
                await submit_action
                submitted = True
            response = await response_info.value
            return response.status
        except Exception:
            # Once the click/Enter went through, any error here is the
            # response wait (JS logins never POST a document), not the submit.
            if submitted:
                return None
            raise

    def _mark_partial(self, reason):
        if not self.partial:
            self.partial = True
            print(f"[CRAWL] Stopping early: {reason}")

    def _time_left(self):
        if self.deadline is None:
            return float("inf")
        return self.deadline - time.monotonic()

    def _screenshot_path(self, dev_name):
        safe_dev_name = dev_name.replace(" ", "_")
        ext = "png" if self.screenshot_lossless else "jpg"
        return os.path.join(
            self.screenshot_dir,
            f"{len(self.visited):03d}_{safe_dev_name}_page.{ext}"
        )

    async def _capture_screenshot(self, page, dev_name, responsive_checks, viewport=None):
        """Capture a height-capped, JPEG-compressed page screenshot."""
        screenshot_path = self._screenshot_path(dev_name)
        viewport = viewport or {}
        viewport_w = int(responsive_checks.get("viewport_width") or viewport.get("width") or 0) or None
        viewport_h = int(responsive_checks.get("viewport_height") or viewport.get("height") or 0) or 800

        doc_height = 0
        try:
            doc_height = int(await page.evaluate(
                "() => Math.max(document.documentElement ? document.documentElement.scrollHeight : 0, document.body ? document.body.scrollHeight : 0)"
            ) or 0)
        except Exception:
            doc_height = 0

        kwargs = {
            "path": screenshot_path,
            "timeout": 10000,
            # scale="css": one pixel per CSS pixel. A 3x DPR full-page
            # iPhone capture is otherwise a ~100 MB bitmap.
            "scale": "css",
        }
        if self.screenshot_lossless:
            kwargs["type"] = "png"
        else:
            kwargs["type"] = "jpeg"
            kwargs["quality"] = self.screenshot_quality

        capture_h = min(max(doc_height, viewport_h), self.screenshot_max_height)
        if viewport_w and capture_h:
            kwargs["full_page"] = True
            kwargs["clip"] = {"x": 0, "y": 0, "width": viewport_w, "height": capture_h}
        else:
            kwargs["full_page"] = True

        try:
            await page.screenshot(**kwargs)
            return os.path.relpath(screenshot_path, self.base_dir), doc_height
        except Exception as ss_err:
            logger.warning(
                f"Full page screenshot failed on {dev_name} ({ss_err}); attempting standard viewport capture"
            )
            kwargs.pop("clip", None)
            kwargs["full_page"] = False
            kwargs["timeout"] = 5000
            try:
                await page.screenshot(**kwargs)
                return os.path.relpath(screenshot_path, self.base_dir), doc_height
            except Exception:
                return None, doc_height

    async def _extract_links(self, page, url):
        """Collect same-site links in one round trip and queue the new ones."""
        internal_links = []
        try:
            hrefs = await page.eval_on_selector_all(
                "a[href]", "els => els.map(a => a.getAttribute('href'))"
            )
        except Exception:
            hrefs = []
            try:
                for link in await page.locator("a").all():
                    hrefs.append(await link.get_attribute("href"))
            except Exception:
                pass

        seen_here = set()
        for href in hrefs or []:
            if not href or not isinstance(href, str):
                continue
            href = href.strip()
            if not href or href.startswith("#"):
                continue

            absolute_url = self.normalize_url(urljoin(url, href))
            if not absolute_url or absolute_url in seen_here:
                continue
            seen_here.add(absolute_url)

            if self.is_internal_url(absolute_url):
                internal_links.append(absolute_url)
                self.discovered_links.add(absolute_url)
                self._enqueue(absolute_url)
        return internal_links

    def _enqueue(self, absolute_url):
        if (
            absolute_url not in self.visited
            and absolute_url not in self.queued
            and len(self.visited) + len(self.queue) < self.max_pages
        ):
            self.queue.append(absolute_url)
            self.queued.add(absolute_url)
            return True
        return False

    async def _explore_clicks(self, page, url):
        """Opt-in: press up to 8 safe, non-form buttons to surface SPA routes.

        Never presses submit controls, buttons inside a form, or anything
        whose accessible name looks like a state change (log out, delete,
        pay ...). After a click that navigated away, the discovered URL is
        queued and the page is restored to `url`."""
        discovered = []
        try:
            buttons = await page.locator("button:not([type='submit']), [role='button']").all()
        except Exception:
            return discovered

        clicked = 0
        for btn in buttons:
            if clicked >= 8:
                break
            try:
                if not await btn.is_visible():
                    continue
                info = await btn.evaluate(
                    "el => ({text: ((el.innerText || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.title || '')).trim(), inForm: !!el.closest('form')})"
                )
                if not isinstance(info, dict) or info.get("inForm"):
                    continue
                if DANGEROUS_CLICK_RE.search(info.get("text") or ""):
                    continue

                clicked += 1
                await btn.click(timeout=1500)
                await _safe_wait_load_state(page, "domcontentloaded", timeout=1000)

                curr_url = self.normalize_url(page.url)
                if curr_url != url:
                    if self.is_internal_url(curr_url):
                        discovered.append(curr_url)
                        self.discovered_links.add(curr_url)
                        self._enqueue(curr_url)
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                        await _safe_wait_load_state(page, "networkidle", timeout=2000)
                    except Exception:
                        break
            except Exception:
                continue
        return discovered

    def _build_result(self, monitor, devices_config, complete):
        successful_pages = [p for p in self.pages if not p.get("error")]
        # self.pages holds one record per URL per device; report unique pages so a
        # one-page site crawled in 3 viewports isn't shown as "3 pages".
        unique_pages = {p.get("actual_url") or p.get("url", "").rsplit(" [", 1)[0] for p in successful_pages}
        attempted_urls = {p.get("actual_url") or p.get("url", "").rsplit(" [", 1)[0] for p in self.pages}
        auth_wall_urls = {p.get("actual_url") for p in successful_pages if p.get("auth_wall")}

        return {
            "target": self.start_url,
            "run_id": self.run_id,
            "pages_crawled": len(unique_pages),
            "page_views_crawled": len(successful_pages),
            "pages_attempted": len(self.pages),
            "pages_failed": len(attempted_urls - unique_pages),
            "page_views_failed": len(self.pages) - len(successful_pages),
            "pages_discovered": len(self.visited | self.queued | self.discovered_links),
            "max_pages": self.max_pages,
            "devices_tested": len(devices_config),
            "devices": list(devices_config.keys()),
            "partial": bool(self.partial),
            "complete": bool(complete),
            "auth_wall_pages": len(auth_wall_urls),
            "auth_credentials_supplied": bool(self.password or self.auth_token),
            "explore_clicks": bool(self.explore_clicks),
            "pages": self.pages,
            "http_errors": monitor.http_errors,
            "network_failures": monitor.network_failures,
            "console_errors": monitor.console_errors,
            "api_calls": monitor.api_calls,
            "auth_test_cases": self.auth_test_cases,
            "auth_findings": self.auth_findings,
        }

    def _write_result(self, result):
        """Write crawl_<run>.json atomically so a kill mid-crawl leaves the
        last complete snapshot, never a truncated file."""
        tmp_path = f"{self.output_file}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(result, file, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.output_file)

    async def crawl(self):

        # Created up front so the summary below always has a monitor to read,
        # regardless of where the event listeners are attached.
        monitor = NetworkMonitor()

        if self.deadline is None:
            self.deadline = time.monotonic() + default_crawl_budget_seconds()

        devices_config = {}

        async with async_playwright() as p:

            headless_mode = os.environ.get("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
            launch_args = _chromium_launch_args()
            try:
                browser = await p.chromium.launch(
                    headless=headless_mode,
                    args=launch_args,
                )
            except Exception as launch_err:
                if "Executable doesn't exist" in str(launch_err):
                    logger.warning("Chromium executable missing. Running automatic playwright installation...")
                    install_proc = await asyncio.create_subprocess_exec(
                        sys.executable, "-m", "playwright", "install", "chromium",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await install_proc.communicate()
                    browser = await p.chromium.launch(
                        headless=headless_mode,
                        args=launch_args,
                    )
                else:
                    raise

            devices_config = _selected_devices(DeviceConfigManager.get_devices_config(p))

            contexts = {}
            pages = {}

            block_private = os.environ.get("QA_BLOCK_PRIVATE_NETWORK", "").lower() == "true"
            route_handler = self._build_route_handler(block_private) if (self.auth_token or block_private) else None

            try:
                for dev_name, dev_config in devices_config.items():
                    # Make a copy so we don't mutate the global playwright device configs
                    ctx_kwargs = dict(dev_config)
                    ctx_kwargs["ignore_https_errors"] = True
                    # The bearer token used to go in extra_http_headers, which
                    # Chromium sends to EVERY origin (analytics, CDNs, ...),
                    # leaking the customer's token. The route handler adds it only
                    # to same-site requests.

                    context = await browser.new_context(**ctx_kwargs)
                    contexts[dev_name] = context
                    if route_handler is not None:
                        await _maybe_await(context.route("**/*", route_handler))
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

                    page.on(
                        "pageerror",
                        lambda error, n=dev_name, p=page: monitor.record_page_error(
                            error,
                            f"{p.url} [{n}]"
                        )
                    )

                    pages[dev_name] = page

                # If authentication is configured, perform login across pages before crawl
                if self.login_url:
                    for dev_name, page in pages.items():
                        auth_res = await self.perform_login(page, dev_name)
                        if not auth_res.get("success"):
                            if dev_name in ("desktop", "Desktop Chrome"):
                                self.auth_test_cases.append({
                                    "id": "TC-AUTH-001",
                                    "title": "Website Authentication & Session Initialization",
                                    "category": "Authentication",
                                    "priority": "P0",
                                    "status": "errored",
                                    "duration_ms": 1500,
                                    "source_page": self.login_url,
                                    "expected_result": "User authenticated successfully and session initialized.",
                                    "actual_result": auth_res.get("error", "Authentication failed."),
                                })
                                self.auth_findings.append({
                                    "id": f"AUTH-FAIL-{self.run_id[:6]}",
                                    "severity": "high",
                                    "priority": "P1",
                                    "classification": "confirmed_bug",
                                    "title": "Authentication Failed on Login Page",
                                    "page": self.login_url,
                                    "description": f"Automated login failed at {self.login_url}: {auth_res.get('error')}",
                                    "recommendation": "Verify login credentials and authentication endpoint configuration.",
                                })
                            break
                        else:
                            if dev_name in ("desktop", "Desktop Chrome"):
                                self.auth_test_cases.append({
                                    "id": "TC-AUTH-001",
                                    "title": "Website Authentication & Session Initialization",
                                    "category": "Authentication",
                                    "priority": "P0",
                                    "status": "passed",
                                    "duration_ms": 1500,
                                    "source_page": self.login_url,
                                    "expected_result": "User authenticated successfully and session initialized.",
                                    "actual_result": "User logged in.",
                                })

                # Dictionary to track if a device has successfully auto-logged in
                auto_logged_in_devices = {}

                print(f"[CRAWL] Strict page limit: {self.max_pages} pages")

                while self.queue and len(self.visited) < self.max_pages:

                    if self._time_left() <= 0:
                        self._mark_partial("crawl time budget exhausted")
                        break

                    url = self.queue.pop(0)
                    self.queued.discard(url)

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

                    # Navigate Desktop first to extract internal links
                    for dev_idx, (dev_name, page) in enumerate(pages.items()):
                        if self.progress_cb:
                            max_p = max(1, self.max_pages)
                            num_devs = max(1, len(pages))
                            # Spread progress evenly across the DISCOVERING band (10% - 30%)
                            page_fraction = (len(self.visited) - 1 + (dev_idx + 1) / num_devs) / max_p
                            pct = int(10 + page_fraction * 20)
                            safe_pct = min(30, max(10, pct))
                            try:
                                self.progress_cb(
                                    safe_pct,
                                    f"Crawling page {len(self.visited)}/{max_p} · [{dev_name}]",
                                    active_device=dev_name,
                                    active_url=url,
                                    page_current=len(self.visited),
                                    page_total=max_p,
                                )
                            except TypeError:
                                self.progress_cb(
                                    safe_pct,
                                    f"Crawling page {len(self.visited)}/{max_p} · [{dev_name}]"
                                )

                        if dev_idx > 0 and self._time_left() <= 0:
                            self._mark_partial("crawl time budget exhausted")
                            break

                        page_started = time.monotonic()
                        try:
                            # Use f"{url} [{dev_name}]" as the canonical page ID for this device
                            page_id = f"{url} [{dev_name}]"
                            print(f"[{dev_name}] Navigating...")
                            # The desktop pass warms the server cache; the
                            # other viewports fetch the same page, so give them
                            # less time before falling back.
                            goto_timeout = 25000 if dev_idx == 0 else 15000
                            try:
                                response = await page.goto(
                                    url,
                                    wait_until="domcontentloaded",
                                    timeout=goto_timeout
                                )
                            except Exception as nav_err:
                                if "timeout" in str(nav_err).lower() and self._time_left() > 20:
                                    print(f"[{dev_name}] DOMContentLoaded timeout on {url}, attempting commit fallback...")
                                    response = await page.goto(
                                        url,
                                        wait_until="commit",
                                        timeout=15000
                                    )
                                else:
                                    raise

                            await _safe_wait_load_state(page, "networkidle", timeout=3000)

                            # Auto-detect login if enabled and not already logged in
                            if not self.login_url and self.username and self.password and not auto_logged_in_devices.get(dev_name):
                                login_res = await self.perform_login(page, dev_name, auto_detect=True)
                                if login_res.get("success") and login_res.get("status") != "no_login_form_detected":
                                    print(f"[{dev_name}] Auto-login successful on {url}")
                                    auto_logged_in_devices[dev_name] = True
                                    await _safe_wait_load_state(page, "networkidle", timeout=3000)

                            status = response.status if response else None
                            title = await page.title()

                            final_url = self.normalize_url(getattr(page, "url", "") or url) or url
                            redirected = final_url != url
                            auth_wall = self.is_auth_wall(url, final_url)
                            if auth_wall:
                                print(f"[{dev_name}] {url} redirected to a login/external page: {final_url}")

                            # Execute deterministic responsive checks in page JS
                            dev_viewport = (devices_config.get(dev_name) or {}).get("viewport") or {}
                            responsive_checks = {
                                "horizontal_overflow": False, "overflow_pixels": 0, "elements_outside_viewport": 0,
                                "forms_outside_viewport": 0, "clipped_buttons": 0, "navigation_visible": True,
                                "viewport_width": int(dev_viewport.get("width") or 1920),
                                "viewport_height": int(dev_viewport.get("height") or 1080),
                                "checked": False,
                            }
                            try:
                                evaluated = await page.evaluate(RESPONSIVE_CHECK_JS)
                                if isinstance(evaluated, dict):
                                    responsive_checks = dict(evaluated, checked=True)
                            except Exception as ev_err:
                                print(f"Responsive check warning on {dev_name}: {ev_err}")

                            timings = None
                            try:
                                raw_timing = await page.evaluate(TIMING_JS)
                                if isinstance(raw_timing, dict):
                                    timings = {
                                        key: (value if not (isinstance(value, (int, float)) and value <= 0 and key.endswith("_ms")) else None)
                                        for key, value in raw_timing.items()
                                    }
                            except Exception:
                                timings = None

                            a11y_checks = None
                            if dev_idx == 0:
                                try:
                                    a11y_checks = await page.evaluate(A11Y_CHECK_JS)
                                except Exception:
                                    a11y_checks = None

                            # Screenshot and checks are captured BEFORE any
                            # interaction so the record describes the page as
                            # it loaded, not a modal or route a click opened.
                            rel_screenshot, doc_height = await self._capture_screenshot(
                                page, dev_name, responsive_checks, viewport=dev_viewport
                            )

                            internal_links = []

                            # Extract links & (optionally) explore interactive controls on Desktop Chrome
                            if dev_idx == 0 and not auth_wall:
                                internal_links = await self._extract_links(page, url)

                                if self.explore_clicks and self._time_left() > 30:
                                    internal_links.extend(await self._explore_clicks(page, url))

                            page_data = {
                                "url": page_id,
                                "actual_url": url,
                                "final_url": final_url,
                                "redirected": redirected,
                                "auth_wall": auth_wall,
                                "device": dev_name,
                                "title": title,
                                "status": status,
                                "links": len(internal_links),
                                "screenshot": rel_screenshot,
                                "document_height": doc_height,
                                "responsive_checks": responsive_checks,
                                "timings": timings,
                                "a11y_checks": a11y_checks,
                                "render_ms": int((time.monotonic() - page_started) * 1000),
                                "timestamp": datetime.now().isoformat(),
                            }

                            self.pages.append(page_data)

                            # Drop the rendered DOM of this viewport before
                            # moving to the next one, so only one heavy page
                            # is alive at a time (cookies/session persist in
                            # the context).
                            if len(pages) > 1 and os.environ.get("QA_BLANK_IDLE_PAGES", "true").lower() != "false":
                                try:
                                    await page.goto("about:blank", timeout=5000)
                                except Exception:
                                    pass

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
                                "render_ms": int((time.monotonic() - page_started) * 1000),
                                "timestamp": datetime.now().isoformat(),
                            })

                    # Persist after every URL so a kill mid-crawl still leaves
                    # usable data for the detector and report stages.
                    try:
                        self._write_result(self._build_result(monitor, devices_config, complete=False))
                    except Exception as write_err:
                        logger.debug("incremental crawl write failed: %s", write_err)

                if self.queue and len(self.visited) < self.max_pages and not self.partial:
                    self._mark_partial("crawl loop ended with pages still queued")
            finally:
                # Close everything even if one close fails, so no Chromium
                # renderer outlives the crawl.
                for context in contexts.values():
                    try:
                        await context.close()
                    except Exception as close_err:
                        logger.debug("context.close failed: %s", close_err)
                try:
                    await browser.close()
                except Exception as close_err:
                    logger.debug("browser.close failed: %s", close_err)

        result = self._build_result(monitor, devices_config, complete=not self.partial)
        self._write_result(result)
        output_file = self.output_file
        result["output_file"] = output_file

        successful_pages = result["page_views_crawled"]

        print()
        print("=" * 70)
        print("CRAWL COMPLETE" if not self.partial else "CRAWL STOPPED EARLY (partial results)")
        print("=" * 70)

        print(f"Pages: {result['pages_crawled']} ({successful_pages} page views across {result['devices_tested']} device(s))")
        if result["page_views_failed"]:
            print(
                f"Pages failed: "
                f"{result['pages_failed']} ({result['page_views_failed']} page views)"
            )
        if result["auth_wall_pages"]:
            print(f"Pages behind a login wall: {result['auth_wall_pages']}")
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
        print(f"API calls observed: {len(monitor.api_calls)}")
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
