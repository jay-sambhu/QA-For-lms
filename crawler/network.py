API_RESOURCE_TYPES = ("xhr", "fetch")

# Upper bound on recorded API calls per crawl; a chatty SPA can fire
# thousands of polling requests and the list lives in memory and in the
# crawl JSON.
MAX_API_CALLS = 500


class NetworkMonitor:
    """Collects HTTP errors, failed requests, console errors and XHR/fetch
    calls (with timing) during a crawl."""

    def __init__(self):
        self.http_errors = []
        self.network_failures = []
        self.console_errors = []
        self.api_calls = []

    @staticmethod
    def _timing_ms(request):
        """Request duration in ms from Playwright's timing dict, or None."""
        try:
            timing = request.timing
        except Exception:
            return None
        if not isinstance(timing, dict):
            return None
        # At the `response` event the body is still streaming, so responseEnd
        # is usually -1; responseStart (time to first byte) is the measured
        # latency available at that point.
        end = timing.get("responseEnd")
        if end is None or end < 0:
            end = timing.get("responseStart")
        start = timing.get("requestStart")
        if end is None or end < 0:
            return None
        if start is None or start < 0:
            start = 0
        return round(max(0.0, float(end) - float(start)), 1)

    def record_response(self, response, page_url):
        status = response.status
        request = response.request

        resource_type = ""
        method = ""
        try:
            resource_type = request.resource_type
            method = request.method
        except Exception:
            pass

        if resource_type in API_RESOURCE_TYPES and len(self.api_calls) < MAX_API_CALLS:
            self.api_calls.append({
                "page": page_url,
                "url": response.url,
                "method": method,
                "status": status,
                "resource_type": resource_type,
                "timing_ms": self._timing_ms(request),
            })

        # Record real HTTP errors.
        if status >= 400:
            self.http_errors.append({
                "page": page_url,
                "url": response.url,
                "status": status,
                "method": method,
                "resource_type": resource_type,
            })

    def record_request_failure(self, request, page_url=""):
        # Playwright reports `failure` as None when it has no reason string.
        # Normalize to "" so downstream consumers can always treat it as text.
        failure = request.failure or ""

        # Ignore normal browser-cancelled requests.
        if failure == "net::ERR_ABORTED":
            return

        self.network_failures.append({
            # Recording the page lets the detector attribute the failure to a
            # page and group repeats across the crawl.
            "page": page_url,
            "url": request.url,
            "method": request.method,
            "resource_type": request.resource_type,
            "failure": failure,
        })

    @staticmethod
    def _read(obj, name):
        """Playwright for Python exposes ConsoleMessage.type/text/location as
        properties (they are methods only in the JavaScript API). Accept both so
        test doubles with methods keep working."""
        value = getattr(obj, name)
        return value() if callable(value) else value

    def record_console(self, message, page_url):
        """Record console error messages from Playwright."""
        try:
            msg_type = self._read(message, "type")
            text = self._read(message, "text")
        except Exception:
            return
        if msg_type != "error":
            return

        entry = {
            "page": page_url,
            # Always "error" given the filter above, but kept so the recorded
            # schema stays compatible with existing crawl_*.json files.
            "type": msg_type,
            "text": text,
        }

        # Source location makes console errors far easier to act on. It is not
        # always populated, so failures here must not break the crawl.
        try:
            location = self._read(message, "location")
        except Exception:
            location = None

        if location:
            entry["location"] = {
                "url": location.get("url", ""),
                "line": location.get("lineNumber"),
                "column": location.get("columnNumber"),
            }

        self.console_errors.append(entry)

    def record_page_error(self, error, page_url):
        """Record an uncaught JavaScript exception (Playwright "pageerror").

        These never reach the console listener, so without this an unhandled
        exception on page load goes unreported."""
        name = getattr(error, "name", "") or ""
        message = getattr(error, "message", "") or str(error)
        text = f"Uncaught {name}: {message}" if name and not message.startswith(name) else f"Uncaught {message}"
        self.console_errors.append({
            "page": page_url,
            "type": "error",
            "source": "pageerror",
            "text": text,
        })
