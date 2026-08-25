class NetworkMonitor:
    def __init__(self):
        self.http_errors = []
        self.network_failures = []
        self.console_errors = []

    def record_response(self, response, page_url):
        status = response.status

        # Record real HTTP errors.
        if status >= 400:
            self.http_errors.append({
                "page": page_url,
                "url": response.url,
                "status": status,
                "method": response.request.method,
                "resource_type": response.request.resource_type,
            })

    def record_request_failure(self, request):
        failure = request.failure

        # Ignore normal browser-cancelled requests.
        if failure == "net::ERR_ABORTED":
            return

        self.network_failures.append({
            "url": request.url,
            "method": request.method,
            "resource_type": request.resource_type,
            "failure": failure,
        })

    def record_console(self, message, page_url):
        if message.type == "error":
            self.console_errors.append({
                "page": page_url,
                "text": message.text,
            })