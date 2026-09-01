#!/usr/bin/env python3
"""Test suite for the secret-redaction layers.

Two independent redactors exist and both must behave:

  * ``GeminiQAAnalyzer._redact`` runs before anything is sent to the model.
  * ``SecretRedactor.redact`` runs before anything is written to the report.

Redaction has two failure modes and this suite covers both. A *miss* leaks a
credential into a prompt or a report. An *over-match* mangles a benign URL that
the QA reader needs in order to reproduce the bug, and is just as damaging
because it silently rewrites evidence.
"""

import unittest

from gemini_analyzer import GeminiQAAnalyzer
from qa_report_generator import SecretRedactor

REDACTED_MARKERS = ("[REDACTED]", "[REDACTED_JWT]")

# Values every redactor must hide, regardless of which names it knows.
COMMON_SECRETS = [
    ("api_key in a query string", "https://a.com/v1?api_key=abc123def456", "abc123def456"),
    ("api_key in JSON", '{"api_key": "abc123def456"}', "abc123def456"),
    ("token in JSON", '{"token": "abc123def456"}', "abc123def456"),
    ("token in JSON, spaced colon", '{ "token" : "abc123def456" }', "abc123def456"),
    ("password in a form body", "email=a%40b.com&password=hunter2sekrit", "hunter2sekrit"),
    ("Authorization header", "Authorization: Bearer abc123def456", "abc123def456"),
    ("bare bearer token", "bearer abc123def456", "abc123def456"),
    ("secret in JSON", '{"secret": "abc123def456"}', "abc123def456"),
    ("cookie header", "Cookie: abc123def456", "abc123def456"),
    (
        "JWT anywhere in free text",
        "Failed to verify eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk",
        "eyJhbGciOiJIUzI1NiJ9",
    ),
]

# Names only the Gemini-side pattern list knows about.
GEMINI_ONLY_SECRETS = [
    ("bare ?key= (Google style)", "https://maps.com/api?key=AIzaSyABCDEF123", "AIzaSyABCDEF123"),
    ("apikey without separator", "https://a.com/?apikey=abc123def456", "abc123def456"),
    ("access_token in JSON", '{"access_token": "abc123def456"}', "abc123def456"),
    ("refresh_token in JSON", '{"refresh_token": "abc123def456"}', "abc123def456"),
    ("client_secret in a body", "client_secret=abc123def456&grant_type=x", "abc123def456"),
    ("underscore-prefixed name", "?user_session_id=abc123def456", "abc123def456"),
    ("X-API-Key header", "X-API-Key: abc123def456", "abc123def456"),
]

# Strings that must survive untouched. These are ordinary query parameters that
# merely *contain* a credential name as a substring. Rewriting them destroys the
# reproduction URL in the report.
MUST_NOT_CHANGE = [
    "https://a.com/list?monkey=1",
    "https://a.com/list?sortkey=name",
    "https://a.com/list?hotkey=ctrl%2Bk",
    "https://a.com/list?donkey=grey",
    "https://a.com/list?author=jane",
    "https://a.com/count?tokens=5",
    "https://a.com/count?keys=3",
    "https://a.com/oauth=start",
    "https://a.com/products/turkey-sandwich",
    "GET https://a.com/api/users 500 Internal Server Error",
    "Uncaught TypeError: Cannot read properties of undefined (reading 'map')",
]


class TestRedaction(unittest.TestCase):
    def _is_redacted(self, original, redacted, secret):
        """A secret counts as handled only if it is gone and a marker replaced it."""
        return secret not in redacted and any(m in redacted for m in REDACTED_MARKERS)

    def _run_secret_cases(self, redact, cases):
        for description, payload, secret in cases:
            with self.subTest(msg=description):
                result = redact(payload)
                self.assertTrue(
                    self._is_redacted(payload, result, secret),
                    f"Failed to redact secret in {description}.\nIn: {payload}\nOut: {result}"
                )

    def _run_passthrough_cases(self, redact):
        for payload in MUST_NOT_CHANGE:
            with self.subTest(msg=payload):
                result = redact(payload)
                self.assertEqual(
                    payload, result,
                    f"Benign string was unexpectedly modified.\nIn: {payload}\nOut: {result}"
                )

    def test_gemini_redact_secrets(self):
        """Test GeminiQAAnalyzer._redact with secrets."""
        self._run_secret_cases(GeminiQAAnalyzer._redact, COMMON_SECRETS + GEMINI_ONLY_SECRETS)

    def test_gemini_redact_passthrough(self):
        """Test GeminiQAAnalyzer._redact with benign strings."""
        self._run_passthrough_cases(GeminiQAAnalyzer._redact)

    def test_secret_redactor_secrets(self):
        """Test SecretRedactor.redact with secrets."""
        self._run_secret_cases(SecretRedactor.redact, COMMON_SECRETS)

    def test_secret_redactor_passthrough(self):
        """Test SecretRedactor.redact with benign strings."""
        self._run_passthrough_cases(SecretRedactor.redact)

    def test_nested_structures(self):
        """Redaction must reach into nested dicts and lists, not just top-level."""
        payload = {
            "candidate": {
                "evidence": {
                    "network_failures": [
                        {"url": "https://a.com/x?api_key=abc123def456", "failure": "net::ERR"},
                    ],
                    "console_errors": [
                        {"text": 'auth failed for {"token": "abc123def456"}'},
                    ],
                },
                "affected_pages": ["https://a.com/list?monkey=1"],
                "occurrences": 3,
                "status": None,
            }
        }

        for label, redact in (
            ("GeminiQAAnalyzer", GeminiQAAnalyzer._redact),
            ("SecretRedactor", SecretRedactor.redact),
        ):
            with self.subTest(redactor=label):
                result = redact(payload)
                flat = repr(result)

                self.assertNotIn("abc123def456", flat, f"Secret removed from nested list item in {label}")
                self.assertIn("?monkey=1", flat, f"Benign nested URL preserved in {label}")
                self.assertEqual(result["candidate"]["occurrences"], 3, f"Non-string values preserved in {label}")
                self.assertIsNone(result["candidate"]["status"], f"None preserved in {label}")
                self.assertIn("abc123def456", repr(payload), f"Input not mutated in {label}")

if __name__ == "__main__":
    unittest.main()
