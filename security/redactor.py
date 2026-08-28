"""
security/redactor.py — Canonical secret-redaction module for the AI QA platform.

This is the ONE authoritative implementation. Both the Gemini analyzer and the
report generator import from here. Do not create another copy.

Pattern coverage (superset of both previous implementations):
  - Bearer / Authorization header tokens
  - JWTs (eyJ…eyJ…signature format)
  - api_key / apikey / api-key / key= (Google-style bare key)
  - access_token / refresh_token / id_token
  - client_secret
  - session_id / user_session_id
  - token (bare)
  - password / passwd / pwd
  - secret
  - cookie
  - auth (bare)
  - private_key / private-key

Safe-guard (load-bearing lookbehind):
  A lookbehind (?<![A-Za-z0-9]) prevents short names from matching the tail
  of ordinary words. Without it ?monkey=1, ?sortkey=name, and
  ?hotkey=x were rewritten to ?mon[REDACTED] — silently corrupting the
  reproduction URLs that QA engineers need to file bugs.
"""

import re


# Compiled once at module import.  Iteration order over patterns determines
# which substitution wins when two patterns could both match.
REDACTION_PATTERNS = [
    # 1. Full "Authorization: Bearer <token>" header lines.
    (
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;\"']+"),
        r"\1[REDACTED]",
    ),
    # 2. Bare "Bearer <token>" anywhere (console errors, network logs).
    (
        re.compile(r"(?i)(bearer\s+)[^\s,;\"']+"),
        r"\1[REDACTED]",
    ),
    # 3. JWTs — three base64url segments separated by dots.
    (
        re.compile(
            r"eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{10,}"
        ),
        "[REDACTED_JWT]",
    ),
    # 4. Named credentials in JSON bodies, query strings, and request headers.
    #    The lookbehind rejects a preceding letter or digit so that short names
    #    don't match word tails (monkey, sortkey, hotkey …).
    #    The ["']? before the separator matches a JSON key's closing quote so
    #    that {"access_token": "secret"} is handled correctly.
    (
        re.compile(
            r"(?i)(?<![A-Za-z0-9])"
            r"((?:api[_ -]?key|apikey|access[_ -]?token|refresh[_ -]?token"
            r"|id[_ -]?token|client[_ -]?secret|session[_ -]?id|token|key"
            r"|password|passwd|pwd|secret|cookie|auth|private[_ -]?key)"
            r"[\"']?\s*[:=]\s*[\"']?)[^\s,;\"'&]+"
        ),
        r"\1[REDACTED]",
    ),
]


class SecretRedactor:
    """Deterministic, recursive secret-redaction layer.

    Usage::

        from security.redactor import SecretRedactor

        safe = SecretRedactor.redact(raw_data)   # works on str, dict, list, any
    """

    @classmethod
    def redact(cls, data):
        """Recursively redact secrets from any JSON-compatible data structure."""
        if isinstance(data, dict):
            return {k: cls.redact(v) for k, v in data.items()}
        if isinstance(data, list):
            return [cls.redact(item) for item in data]
        if not isinstance(data, str):
            return data

        result = data
        for pattern, replacement in REDACTION_PATTERNS:
            result = pattern.sub(replacement, result)
        return result
