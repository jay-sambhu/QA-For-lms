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

import sys

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


def _is_redacted(original, redacted, secret):
    """A secret counts as handled only if it is gone and a marker replaced it."""
    return secret not in redacted and any(m in redacted for m in REDACTED_MARKERS)


def _run_secret_cases(label, redact, cases):
    print(f"\n{label}: secrets that must be hidden")
    print("-" * 80)

    failures = 0
    for description, payload, secret in cases:
        result = redact(payload)
        if _is_redacted(payload, result, secret):
            print(f"  [PASS] {description}")
        else:
            failures += 1
            print(f"  [FAIL] {description}")
            print(f"         in:  {payload}")
            print(f"         out: {result}")
    return failures


def _run_passthrough_cases(label, redact):
    print(f"\n{label}: benign strings that must not be rewritten")
    print("-" * 80)

    failures = 0
    for payload in MUST_NOT_CHANGE:
        result = redact(payload)
        if result == payload:
            print(f"  [PASS] {payload}")
        else:
            failures += 1
            print(f"  [FAIL] {payload}")
            print(f"         became: {result}")
    return failures


def test_nested_structures():
    """Redaction must reach into nested dicts and lists, not just top-level."""
    print("\nNested structure traversal")
    print("-" * 80)

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

    failures = 0
    for label, redact in (
        ("GeminiQAAnalyzer._redact", GeminiQAAnalyzer._redact),
        ("SecretRedactor.redact", SecretRedactor.redact),
    ):
        result = redact(payload)
        flat = repr(result)

        checks = [
            ("secret removed from nested list item", "abc123def456" not in flat),
            ("benign nested URL preserved", "?monkey=1" in flat),
            ("non-string values preserved", result["candidate"]["occurrences"] == 3),
            ("None preserved", result["candidate"]["status"] is None),
            ("input not mutated", "abc123def456" in repr(payload)),
        ]
        for name, ok in checks:
            if ok:
                print(f"  [PASS] {label}: {name}")
            else:
                failures += 1
                print(f"  [FAIL] {label}: {name}")

    return failures == 0


def main():
    print("\n" + "=" * 80)
    print("SECRET REDACTION TEST SUITE")
    print("=" * 80)

    failures = 0

    failures += _run_secret_cases(
        "GeminiQAAnalyzer._redact",
        GeminiQAAnalyzer._redact,
        COMMON_SECRETS + GEMINI_ONLY_SECRETS,
    )
    failures += _run_passthrough_cases(
        "GeminiQAAnalyzer._redact", GeminiQAAnalyzer._redact
    )

    failures += _run_secret_cases(
        "SecretRedactor.redact", SecretRedactor.redact, COMMON_SECRETS
    )
    failures += _run_passthrough_cases("SecretRedactor.redact", SecretRedactor.redact)

    if not test_nested_structures():
        failures += 1

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    if failures == 0:
        print("✓ All redaction tests PASSED!")
        return 0

    print(f"✗ {failures} redaction check(s) FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
