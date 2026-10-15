class NetworkMonitor:
    """Collects HTTP errors, failed requests, and console errors during a crawl."""

    def __init__(self):
        self.http_errors = []
        self.network_failures = []
        self.console_errors = []

    def record_response(self, response, page_url):
        status = response.status

        # Record real HTTP errors.
        if status >= 400:
            request = response.request
            self.http_errors.append({
                "page": page_url,
                "url": response.url,
                "status": status,
                "method": request.method,
                "resource_type": request.resource_type,
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
