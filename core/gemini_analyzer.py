#!/usr/bin/env python3
"""Conservative Gemini analysis of deterministic QA root-cause candidates."""

import asyncio
import json
import os
import re
import time
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from security.redactor import SecretRedactor

MODULE_DIR = Path(__file__).resolve().parent

# Ordered tuples, not sets: iteration order over a set of strings varies with
# PYTHONHASHSEED, which made the JSON key order of the count dictionaries
# change between runs and broke byte-for-byte report comparisons.
CLASSIFICATION_ORDER = (
    "confirmed_bug",
    "high_confidence_candidate",
    "needs_manual_review",
    "expected_behavior",
    "informational",
)
SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
CONFIDENCE_ORDER = ("high", "medium", "low")
REQUIRED_FIELD_ORDER = (
    "classification",
    "severity",
    "confidence",
    "title",
    "summary",
    "reasoning",
    "user_impact",
    "expected_result",
    "actual_result",
    "recommended_action",
    "evidence_used",
)

# Kept as sets for fast membership tests, derived from the ordered tuples above
# so the two can never drift apart.
CLASSIFICATIONS = set(CLASSIFICATION_ORDER)
SEVERITIES = set(SEVERITY_ORDER)
CONFIDENCES = set(CONFIDENCE_ORDER)
REQUIRED_FIELDS = set(REQUIRED_FIELD_ORDER)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

# Google retires Gemini model names regularly (the API answers HTTP 404
# "no longer available"), and a model can be temporarily overloaded (HTTP 503).
# Rather than failing the analysis, walk this chain until one answers.
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_FALLBACK_MODELS = (
    "gemini-3.8-flash",       # Google's current recommendation
    "gemini-3.5-flash",       # stable, rarely overloaded
    "gemini-3-flash-preview",
    "gemini-flash-latest",    # alias: may point at an overloaded release
)
# Names Google has already retired for new API keys; they are swapped for the
# default before the first request so the usual case costs no extra round trip.
RETIRED_GEMINI_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-3-pro-preview",
}

# Seconds to wait before the single retry of a failed model call.
RETRY_DELAY_SECONDS = 4.0
# A flash model answers a triage prompt in well under a minute; a longer wait
# only delays the fallback to the next model when one is overloaded.
REQUEST_TIMEOUT_SECONDS = 40
# Attempts per candidate (each attempt may walk the model chain).
MAX_ATTEMPTS = 2

# Stage-level budget so a slow or overloaded provider cannot consume the
# whole pipeline timeout: at most this many model-backed candidates, at most
# this many concurrent requests, and a hard wall-clock deadline after which
# the remaining candidates get the deterministic fallback.
DEFAULT_MAX_CANDIDATES = 25
DEFAULT_CONCURRENCY = 3
DEFAULT_BUDGET_SECONDS = 480

SEVERITY_RANK = {name: index for index, name in enumerate(SEVERITY_ORDER)}

# Structured output schema sent to Gemini (responseSchema) so the answer is
# JSON with the right enums instead of prose to be regex-scraped.
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "classification": {"type": "STRING", "enum": list(CLASSIFICATION_ORDER)},
        "severity": {"type": "STRING", "enum": list(SEVERITY_ORDER)},
        "confidence": {"type": "STRING", "enum": list(CONFIDENCE_ORDER)},
        "title": {"type": "STRING"},
        "summary": {"type": "STRING"},
        "reasoning": {"type": "STRING"},
        "user_impact": {"type": "STRING"},
        "expected_result": {"type": "STRING"},
        "actual_result": {"type": "STRING"},
        "recommended_action": {"type": "STRING"},
        "evidence_used": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": list(REQUIRED_FIELD_ORDER),
}


def _env_int(name, default):
    try:
        return int((os.environ.get(name) or "").strip() or default)
    except ValueError:
        return default


class GeminiQAAnalyzer:
    """Analyze grouped candidates with multi-AI provider support and automatic key failover."""

    def __init__(
        self,
        api_key=None,
        model_client=None,
        model_name=DEFAULT_GEMINI_MODEL,
        provider_id="gemini",
        endpoint=None,
        key_pool=None,
        max_candidates=None,
        concurrency=None,
        budget_seconds=None,
    ):
        self.model_client = model_client
        self.provider_id = (provider_id or "gemini").lower()
        self.model_name = model_name or DEFAULT_GEMINI_MODEL
        self.api_key = api_key
        self.endpoint = endpoint
        self.key_pool = list(key_pool or [])
        self.current_key_idx = 0
        # Models whose daily quota is spent for this key: skipped for the rest of the run
        self._exhausted_models = set()
        self._key_lock = asyncio.Lock()

        self.max_candidates = max(1, max_candidates or _env_int("QA_AI_MAX_CANDIDATES", DEFAULT_MAX_CANDIDATES))
        self.concurrency = max(1, concurrency or _env_int("QA_AI_CONCURRENCY", DEFAULT_CONCURRENCY))
        self.budget_seconds = max(30, budget_seconds or _env_int("QA_AI_BUDGET_SECONDS", DEFAULT_BUDGET_SECONDS))
        self._deadline = None

        # If a multi-key pool is provided, initialize active credentials from the first pool item
        if self.key_pool and len(self.key_pool) > 0:
            first_key = self.key_pool[0]
            self.api_key = first_key.get("api_key")
            self.provider_id = (first_key.get("provider_id") or "gemini").lower()
            self.model_name = first_key.get("model") or self.model_name
            self.endpoint = first_key.get("endpoint") or self.endpoint
        elif self.api_key is None:
            # Strict user isolation: the run uses the key handed to it (the
            # user's own, or the trial key the API placed in the environment
            # of this subprocess). Nothing is pulled from the owner's pool.
            self.api_key = os.environ.get("GEMINI_API_KEY") or None

        self._normalize_model()

    def _normalize_model(self):
        """Swap a retired Gemini model name for the current default."""
        if self.provider_id == "gemini" and (self.model_name or "").strip().lower() in RETIRED_GEMINI_MODELS:
            print(f"[AI_MODEL] '{self.model_name}' has been retired by Google; using {DEFAULT_GEMINI_MODEL} instead.")
            self.model_name = DEFAULT_GEMINI_MODEL

    def _next_fallback_model(self, tried):
        """Return the next untried Gemini model in the fallback chain, or None."""
        if self.provider_id != "gemini":
            return None
        tried.add(self.model_name)
        for candidate in GEMINI_FALLBACK_MODELS:
            if candidate not in tried and candidate not in self._exhausted_models:
                return candidate
        return None

    def _current_pool_entry(self):
        if self.key_pool and 0 <= self.current_key_idx < len(self.key_pool):
            return self.key_pool[self.current_key_idx] or {}
        return {}

    def _is_trial_pool(self):
        """Only a pool the API marked as the server-side trial key may fall
        back to the owner's ApiKey table; a user's own exhausted keys never
        roll over onto the owner's quota."""
        entry = self._current_pool_entry()
        return (entry.get("source") or "").lower() == "trial"

    def _failover_to_next_key(self):
        """Fail over to the next key in the user's pool, if any."""
        if self.key_pool and (self.current_key_idx + 1) < len(self.key_pool):
            old_p = self.provider_id
            old_m = self.model_name
            self.current_key_idx += 1
            next_cfg = self.key_pool[self.current_key_idx]

            self.api_key = next_cfg.get("api_key")
            self.provider_id = (next_cfg.get("provider_id") or "gemini").lower()
            self.model_name = next_cfg.get("model") or (
                DEFAULT_GEMINI_MODEL if self.provider_id == "gemini" else "gpt-4o"
            )
            self.endpoint = next_cfg.get("endpoint")
            self._exhausted_models = set()
            self._normalize_model()

            print(
                f"\n[AI_FAILOVER] Rate limit or quota error on {old_p.upper()} ({old_m}). "
                f"Seamlessly failing over to backup key #{self.current_key_idx + 1} "
                f"({self.provider_id.upper()}, model: {self.model_name}) without scan interruption..."
            )
            return True

        if self._is_trial_pool():
            return self._rotate_key()
        return False

    def _rotate_key(self):
        """Rotate within the owner's server-side key table (trial scans only)."""
        if not self.api_key:
            return False

        try:
            from db import SessionLocal
            from models import ApiKey
            from datetime import timezone, timedelta

            with SessionLocal() as db:
                # Mark current key as rate limited for 1 hour
                current = db.query(ApiKey).filter(ApiKey.key_value == self.api_key).first()
                if current:
                    current.status = "rate_limited"
                    current.rate_limit_reset_at = datetime.now(timezone.utc) + timedelta(hours=1)
                    db.commit()

                # Reset rate_limited keys that have expired
                expired_keys = db.query(ApiKey).filter(
                    ApiKey.status == "rate_limited",
                    ApiKey.rate_limit_reset_at <= datetime.now(timezone.utc)
                ).all()
                for key in expired_keys:
                    key.status = "active"
                    key.rate_limit_reset_at = None
                if expired_keys:
                    db.commit()

                # Fetch next active key
                next_key = db.query(ApiKey).filter(
                    ApiKey.service == "gemini",
                    ApiKey.status == "active"
                ).first()

                if next_key:
                    self.api_key = next_key.key_value
                    self._exhausted_models = set()
                    return True
                return False
        except Exception:
            return False

    @staticmethod
    def find_latest_findings(results_dir="results"):
        results_path = Path(results_dir)
        if not results_path.exists():
            return None
        # By mtime, not name: run ids may be UUIDs (from the API) rather than
        # timestamps, so filename order is not chronological order. The name is
        # the tiebreak because mtime granularity is coarse enough that two files
        # written in the same tick would otherwise order arbitrarily.
        files = sorted(
            results_path.glob("qa_findings_*.json"),
            key=lambda path: (path.stat().st_mtime, path.name),
            reverse=True,
        )
        return files[0] if files else None

    @staticmethod
    def load_findings(path):
        with open(path, encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _redact(value):
        """Redact credentials recursively before prompts or debug output
        (delegates to the one canonical implementation)."""
        return SecretRedactor.redact(value)

    @classmethod
    def compact_evidence(cls, candidate, target=""):
        evidence = candidate.get("evidence") or {}
        affected = candidate.get("affected_pages") or []
        screenshots = candidate.get("screenshots") or []

        # Prefer the explicit page->screenshot pairing produced by the bug
        # detector. Zipping two separately de-duplicated lists silently paired
        # the wrong screenshot with the wrong page whenever a page had none.
        pairs = candidate.get("page_screenshots")
        if pairs:
            paired = [
                (item.get("page", ""), item.get("screenshot", ""))
                for item in pairs
            ]
        else:
            paired = list(zip(affected, screenshots))

        screenshot_evidence = []
        for page, path in paired:
            exists = bool(path) and Path(path).exists()
            screenshot_evidence.append({"page": page, "path": path, "available": exists})

        package = {
            "target": target,
            "candidate_id": candidate.get("id"),
            "type": candidate.get("type"),
            "url": candidate.get("url"),
            "status": candidate.get("status"),
            "method": candidate.get("method"),
            "resource_type": candidate.get("resource_type"),
            "occurrences": candidate.get("occurrences", 0),
            "affected_pages": affected[:10],
            "affected_page_count": candidate.get("affected_page_count", len(affected)),
            "affected_devices": candidate.get("affected_devices") or [],
            "page_titles": candidate.get("page_titles") or [],
            "deterministic_severity": candidate.get("severity"),
            "deterministic_confidence": candidate.get("confidence"),
            "description": candidate.get("description", ""),
            "title": candidate.get("title", ""),
            "first_party": candidate.get("first_party"),
            "http_errors": (evidence.get("http_errors") or [])[:3],
            "console_errors": (evidence.get("console_errors") or [])[:5],
            "network_failures": (evidence.get("network_failures") or [])[:5],
            "responsive_checks": (evidence.get("responsive_checks") or None),
            "screenshot_evidence": screenshot_evidence[:3],
        }
        if not any(item["available"] for item in screenshot_evidence):
            package["screenshot_note"] = "Screenshot analysis unavailable."
        return cls._redact(package)

    @staticmethod
    def _deterministic_context(candidate):
        """One sentence of what the detector already established."""
        bits = [
            f"deterministic severity {candidate.get('severity') or 'unknown'}",
            f"detector confidence {candidate.get('confidence') or 'unknown'}",
        ]
        first_party = candidate.get("first_party")
        if first_party is True:
            bits.append("first-party (the site under test)")
        elif first_party is False:
            bits.append("third-party host (not the site under test)")
        pages = candidate.get("affected_page_count") or len(candidate.get("affected_pages") or [])
        devices = candidate.get("affected_devices") or []
        occurrences = candidate.get("occurrences") or 0
        bits.append(f"seen {occurrences} time(s) on {pages} page(s)")
        if devices:
            bits.append("on " + ", ".join(str(d) for d in devices))
        return "The detector recorded: " + "; ".join(bits) + "."

    @classmethod
    def build_prompt(cls, candidate, target=""):
        evidence = cls.compact_evidence(candidate, target)
        return (
            "Act as a conservative senior QA engineer writing for a product owner. "
            "Analyze only the supplied evidence; do not invent backend behavior, credentials, "
            "responses, screenshots, or user impact. "
            + cls._deterministic_context(candidate)
            + " Return exactly one JSON object and no prose. "
            "Classification must be exactly one of: " + ", ".join(CLASSIFICATION_ORDER)
            + ". Severity must be one of: " + ", ".join(SEVERITY_ORDER)
            + "; confidence must be one of: " + ", ".join(CONFIDENCE_ORDER) + ". "
            "Style rules: 'title' is at most 12 words, plain English, and never contains a URL, "
            "hostname or path; 'summary' is two sentences at most; 'recommended_action' is one "
            "concrete step the site's developers can take; 'user_impact' describes what a visitor "
            "experiences; 'evidence_used' lists the evidence fields you relied on. "
            "A third-party host failing, a redirect, or an informational console message is usually "
            "expected_behavior or informational, not a bug of the site under test. "
            "Required fields: " + json.dumps(list(REQUIRED_FIELD_ORDER)) + "."
            + "\nEvidence:\n"
            + json.dumps(evidence, indent=2, ensure_ascii=False)
        )

    def _time_left(self):
        if self._deadline is None:
            return float("inf")
        return self._deadline - time.monotonic()

    async def _call_model(self, prompt, retries=0, tried=None):
        if self.model_client is not None:
            if hasattr(self.model_client, "ainvoke"):
                response = await self.model_client.ainvoke(prompt)
            elif hasattr(self.model_client, "invoke"):
                response = self.model_client.invoke(prompt)
            elif callable(self.model_client):
                response = self.model_client(prompt)
                if hasattr(response, "__await__"):
                    response = await response
            else:
                raise TypeError("Unsupported Gemini mock client")
            return getattr(response, "content", response)

        if not self.api_key:
            raise RuntimeError(f"{self.provider_id.upper()} API key unavailable")

        tried = tried if tried is not None else set()
        p = (self.provider_id or "gemini").lower()
        model_name = self.model_name
        if p == "gemini":
            url = f"{GEMINI_ENDPOINT}/{model_name}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            }
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json",
                    "responseSchema": RESPONSE_SCHEMA,
                },
            }
        elif p == "anthropic":
            url = self.endpoint or "https://api.anthropic.com/v1/messages"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }
            data = {
                "model": model_name or "claude-3-5-sonnet-20241022",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
            }
        else:
            # openai, deepseek, local_llm (OpenAI compatible chat completions)
            if p == "deepseek":
                url = self.endpoint or "https://api.deepseek.com/chat/completions"
            elif p == "local_llm":
                url = self.endpoint or "http://localhost:11434/v1/chat/completions"
            else:
                url = self.endpoint or "https://api.openai.com/v1/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            data = {
                "model": model_name or ("deepseek-chat" if p == "deepseek" else "gpt-4o"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            }

        request = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        timeout = REQUEST_TIMEOUT_SECONDS
        if self._deadline is not None:
            timeout = max(5, min(REQUEST_TIMEOUT_SECONDS, int(self._time_left())))

        def fetch():
            try:
                with urllib.request.urlopen(
                    request, timeout=timeout
                ) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                detail = ""
                try:
                    # Keep enough of the body to see Google's quota id
                    # (e.g. "...PerDayPerProjectPerModel") and retryDelay.
                    detail = error.read().decode("utf-8", "replace")[:2000]
                except Exception:
                    pass

                is_quota_or_rate = error.code == 429 or any(
                    kw in detail.lower()
                    for kw in ["quota", "rate_limit", "resource_exhausted", "tokens_exceeded"]
                )
                if is_quota_or_rate:
                    raise RuntimeError(f"HTTP_RATE_LIMIT_{error.code}: {detail}") from None

                raise RuntimeError(
                    f"{self.provider_id.upper()} API returned HTTP {error.code}: {detail}"
                ) from None
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                # No HTTP answer at all (read timeout, reset connection): the
                # model is effectively unavailable, so the caller can move on
                # to the next one instead of waiting out another timeout.
                raise RuntimeError(f"MODEL_UNAVAILABLE: {error}") from None

        try:
            response_data = await asyncio.to_thread(fetch)
        except RuntimeError as e:
            if self._time_left() <= 0:
                raise RuntimeError("AI_BUDGET_EXHAUSTED: triage time budget exhausted") from None
            if "HTTP_RATE_LIMIT" in str(e) or "HTTP_429" in str(e):
                async with self._key_lock:
                    rotated = await asyncio.to_thread(self._failover_to_next_key)
                max_retries = max(len(self.key_pool or []) + 2, 3)
                if rotated and retries < max_retries:
                    return await self._call_model(prompt, retries=retries + 1, tried=set())
                # Gemini quotas are per model: the same key usually still has
                # headroom on the next model in the chain.
                if "PerDay" in str(e):
                    self._exhausted_models.add(model_name)
                next_model = self._next_fallback_model(tried)
                if next_model and retries < max_retries + len(GEMINI_FALLBACK_MODELS):
                    print(f"[AI_MODEL_FALLBACK] {model_name} quota exhausted for this key; retrying with {next_model}...")
                    self.model_name = next_model
                    return await self._call_model(prompt, retries=retries + 1, tried=tried)
                raise RuntimeError(
                    f"{self.provider_id.upper()} quota or rate limit reached across all available keys and models: {str(e)[:400]}"
                ) from None
            # A retired model (404) or an overloaded one (503): try the next
            # model in the chain with the same key instead of giving up.
            message = str(e)
            unavailable = "HTTP 404" in message or "HTTP 503" in message or "MODEL_UNAVAILABLE" in message
            if p == "gemini" and unavailable:
                next_model = self._next_fallback_model(tried)
                if next_model and retries < len(GEMINI_FALLBACK_MODELS) + 2:
                    why = "retired" if "HTTP 404" in message else ("not responding" if "MODEL_UNAVAILABLE" in message else "overloaded")
                    print(f"[AI_MODEL_FALLBACK] {model_name} is {why}; retrying with {next_model}...")
                    self.model_name = next_model
                    return await self._call_model(prompt, retries=retries + 1, tried=tried)
            raise
        except Exception as error:
            # Redact before re-raising: the message ends up in the report.
            raise RuntimeError(
                f"{self.provider_id.upper()} API request failed: {self._redact(str(error))}"
            ) from None

        try:
            if p == "gemini":
                candidates = response_data.get("candidates", [])
                if not candidates:
                    feedback = response_data.get("promptFeedback", {})
                    raise RuntimeError(f"Gemini returned no candidates: {feedback}")
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(part.get("text", "") for part in parts)
            elif p == "anthropic":
                content = response_data.get("content", [])
                if not content:
                    raise RuntimeError(f"Anthropic returned no content: {response_data}")
                return "".join(
                    block.get("text", "") for block in content if block.get("type") == "text"
                )
            else:
                choices = response_data.get("choices", [])
                if not choices:
                    raise RuntimeError(f"{self.provider_id.upper()} returned no choices: {response_data}")
                msg = choices[0].get("message", {})
                return msg.get("content", "")
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(
                f"Unexpected {self.provider_id.upper()} response shape: {error}"
            ) from None

    @staticmethod
    def parse_response(response):
        if isinstance(response, dict):
            return response
        text = str(response or "").strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
        if fenced:
            text = fenced.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start:end + 1])
            raise

    @staticmethod
    def _normalize_enum(value):
        return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

    @classmethod
    def validate_response(cls, response):
        parsed = cls.parse_response(response)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response is not an object")
        missing = REQUIRED_FIELDS - parsed.keys()
        if missing:
            raise ValueError("Missing fields: " + ", ".join(sorted(missing)))
        # Models return "Confirmed_Bug" / "High" often enough that a strict
        # compare threw away a perfectly good verdict.
        for field in ("classification", "severity", "confidence"):
            parsed[field] = cls._normalize_enum(parsed[field])
        if parsed["classification"] not in CLASSIFICATIONS:
            raise ValueError(f"Invalid classification: {parsed['classification']!r}")
        if parsed["severity"] not in SEVERITIES:
            raise ValueError(f"Invalid severity: {parsed['severity']!r}")
        if parsed["confidence"] not in CONFIDENCES:
            raise ValueError(f"Invalid confidence: {parsed['confidence']!r}")
        if not isinstance(parsed.get("evidence_used"), list):
            parsed["evidence_used"] = (
                [str(parsed.get("evidence_used", ""))] if parsed.get("evidence_used") else []
            )
        title = str(parsed.get("title") or "").strip()
        title = re.sub(r"https?://\S+", "", title).strip(" -:")
        parsed["title"] = title or "Untitled finding"
        # Fixed field order so the emitted JSON is byte-stable across runs.
        return {field: cls._redact(parsed[field]) for field in REQUIRED_FIELD_ORDER}

    @classmethod
    def fallback(cls, reason, raw_response=None, candidate=None):
        candidate = candidate or {}
        result = {
            "classification": "needs_manual_review",
            "severity": candidate.get("severity", "medium"),
            "confidence": candidate.get("confidence", "low"),
            "title": candidate.get("title", "AI analysis unavailable"),
            "summary": candidate.get("description") or "Manual review is required because the AI model did not provide a valid analysis.",
            "reasoning": reason,
            "user_impact": "User impact cannot be determined from the available crawl evidence.",
            "expected_result": candidate.get("expected_result", "AI analysis unavailable; expected result cannot be determined."),
            "actual_result": candidate.get("actual_result", candidate.get("description") or "AI analysis unavailable; actual result cannot be determined."),
            "recommended_action": "Review the deterministic evidence for this finding manually.",
            "evidence_used": [],
            "analysis_failed": True,
        }
        if raw_response:
            result["raw_response"] = cls._redact(str(raw_response))
        return result

    @classmethod
    def deterministic_verdict(cls, candidate):
        """Verdict for candidates that never need a model call: informational
        console messages and non-5xx failures on hosts outside the site."""
        severity = candidate.get("severity") or "info"
        first_party = candidate.get("first_party")
        status = candidate.get("status")
        ctype = candidate.get("type")
        numeric_status = status if isinstance(status, int) else None

        if ctype == "auth_wall":
            classification = "expected_behavior" if severity == "info" else "needs_manual_review"
            if classification == "needs_manual_review":
                return None
            reason = "Pages redirected to a login page; without credentials this is expected."
        elif first_party is False and (numeric_status is None or numeric_status < 500):
            classification = "expected_behavior"
            reason = "The failing host is not part of the site under test, and the status is not a server error."
        elif severity == "info":
            classification = "informational"
            reason = "The detector rated this informational; it does not affect the site's users."
        else:
            return None

        return {
            "classification": classification,
            "severity": "info" if classification != "needs_manual_review" else severity,
            "confidence": candidate.get("confidence") or "medium",
            "title": candidate.get("title") or "Informational finding",
            "summary": candidate.get("description") or "",
            "reasoning": reason,
            "user_impact": "No visible impact on the site's users is expected.",
            "expected_result": "No action required.",
            "actual_result": candidate.get("description") or "",
            "recommended_action": "No action required; verify only if the behaviour is unexpected for your site.",
            "evidence_used": ["deterministic_detector"],
            "deterministic": True,
        }

    async def analyze_candidate(self, candidate, target=""):
        verdict = self.deterministic_verdict(candidate)
        if verdict is not None:
            return verdict

        prompt = self.build_prompt(candidate, target)
        if self.model_client is None and not self.api_key:
            return self.fallback("Gemini API key unavailable; manual review required.", candidate=candidate)
        last_error = None
        # Each candidate gets the full model chain; an "overloaded" answer from
        # every model is transient, so back off and walk the chain again.
        for attempt in range(MAX_ATTEMPTS):
            if self._time_left() <= 0:
                return self.fallback("AI triage time budget exhausted; manual review required.", candidate=candidate)
            try:
                raw = await self._call_model(prompt, tried=set())
                return self.validate_response(raw)
            except Exception as error:
                last_error = error
                message = str(error)
                if "AI_BUDGET_EXHAUSTED" in message:
                    return self.fallback("AI triage time budget exhausted; manual review required.", candidate=candidate)
                if "429" in message or "quota" in message.lower():
                    # A daily quota will not clear during this run, so only
                    # give up when every model in the chain has hit it;
                    # otherwise the others merely answered "overloaded" or a
                    # per-minute limit, which a short wait fixes.
                    usable = [m for m in GEMINI_FALLBACK_MODELS if m not in self._exhausted_models]
                    if not usable or self.provider_id != "gemini":
                        return self.fallback("AI quota limit reached; manual review required.", candidate=candidate)
                    delay = re.search(r"retryDelay\W+(\d+)s", message)
                    wait_s = int(delay.group(1)) if delay else 0
                    sleep_for = min(wait_s, 30) + 1 if 0 < wait_s <= 30 else RETRY_DELAY_SECONDS * (attempt + 1)
                    await asyncio.sleep(min(sleep_for, max(0.0, self._time_left())))
                    continue
                if attempt + 1 < MAX_ATTEMPTS:
                    await asyncio.sleep(min(RETRY_DELAY_SECONDS * (attempt + 1), max(0.0, self._time_left())))
        return self.fallback(
            "AI analysis failed; manual review required.", str(last_error), candidate=candidate
        )

    @staticmethod
    def _candidate_order(candidate):
        """Most important first: severity, then first-party, then occurrences."""
        return (
            SEVERITY_RANK.get(candidate.get("severity") or "info", len(SEVERITY_ORDER)),
            0 if candidate.get("first_party") is not False else 1,
            -(candidate.get("occurrences") or 0),
        )

    async def analyze(self, findings_data):
        candidates = findings_data.get("root_cause_candidates") or []
        target = findings_data.get("target", "")
        self._deadline = time.monotonic() + self.budget_seconds

        # Decide which candidates get a model call: the most severe ones up to
        # the cap; everything else is answered deterministically.
        model_slots = set()
        ranked = sorted(range(len(candidates)), key=lambda i: self._candidate_order(candidates[i]))
        for index in ranked:
            if self.deterministic_verdict(candidates[index]) is not None:
                continue
            if len(model_slots) >= self.max_candidates:
                break
            model_slots.add(index)

        semaphore = asyncio.Semaphore(self.concurrency)

        async def run_one(index, candidate):
            if index not in model_slots and self.deterministic_verdict(candidate) is None:
                return self.fallback(
                    f"Candidate limit reached ({self.max_candidates} AI analyses per scan); manual review required.",
                    candidate=candidate,
                )
            async with semaphore:
                return await self.analyze_candidate(candidate, target)

        analyses = await asyncio.gather(
            *(run_one(index, candidate) for index, candidate in enumerate(candidates)),
            return_exceptions=True,
        )

        findings, errors = [], []
        for index, (candidate, analysis) in enumerate(zip(candidates, analyses), 1):
            if isinstance(analysis, BaseException):
                analysis = self.fallback(
                    "AI analysis failed; manual review required.", str(analysis), candidate=candidate
                )

            # Only genuine failures belong in `errors`. A model that returns a
            # well-formed `needs_manual_review` verdict is working correctly.
            if analysis.pop("analysis_failed", False):
                errors.append(
                    {"candidate_id": candidate.get("id"), "error": analysis["reasoning"]}
                )

            finding = {
                "id": f"AI-BUG-{index:03d}",
                "candidate_id": candidate.get("id"),
                **analysis,
                "first_party": candidate.get("first_party"),
                "candidate": deepcopy(candidate),
            }
            findings.append(finding)

        classification_counts = {key: 0 for key in CLASSIFICATION_ORDER}
        severity_counts = {key: 0 for key in SEVERITY_ORDER}
        confidence_counts = {key: 0 for key in CONFIDENCE_ORDER}
        for finding in findings:
            # `.get` guards against a future classification/severity being
            # added to the prompt but not to the ordered tuples.
            if finding["classification"] in classification_counts:
                classification_counts[finding["classification"]] += 1
            if finding["severity"] in severity_counts:
                severity_counts[finding["severity"]] += 1
            if finding["confidence"] in confidence_counts:
                confidence_counts[finding["confidence"]] += 1
        return {
            "target": target,
            "source": {
                "crawl_result": findings_data.get("crawl_source", ""),
                "qa_findings": findings_data.get("source_file", ""),
            },
            "summary": {
                "total_candidates": len(findings),
                "confirmed_bugs": classification_counts["confirmed_bug"],
                "high_confidence_candidates": classification_counts["high_confidence_candidate"],
                "needs_manual_review": classification_counts["needs_manual_review"],
                "expected_behavior": classification_counts["expected_behavior"],
                "informational": classification_counts["informational"],
                "analysis_failures": len(errors),
                "ai_analyzed": len(model_slots),
                "deterministic_verdicts": sum(1 for f in findings if f.get("deterministic")),
                "classification_counts": classification_counts,
                "severity_counts": severity_counts,
                "confidence_counts": confidence_counts,
                "triage_metrics": findings_data.get("triage_metrics", {}),
            },
            "findings": findings,
            "errors": errors,
        }

    @staticmethod
    def render_markdown(result):
        summary = result["summary"]
        lines = [
            "# AI QA Analysis Report", "", f"Target: {result.get('target', '')}", "",
            "## Executive Summary", "",
            f"Total Candidates: {summary['total_candidates']}",
            f"Confirmed Bugs: {summary['confirmed_bugs']}",
            f"High-Confidence Candidates: {summary['high_confidence_candidates']}",
            f"Needs Manual Review: {summary['needs_manual_review']}",
            f"Expected Behavior: {summary['expected_behavior']}",
            f"Informational: {summary['informational']}", "",
        ]
        sections = [("confirmed_bug", "Confirmed Bugs"), ("high_confidence_candidate", "Critical / High-Confidence Findings"), ("needs_manual_review", "Manual Review Required"), ("expected_behavior", "Expected Behavior"), ("informational", "Informational")]
        for classification, heading in sections:
            lines.extend([f"## {heading}", ""])
            selected = [f for f in result["findings"] if f["classification"] == classification]
            if not selected:
                lines.append("None.")
            for finding in selected:
                candidate = finding.get("candidate", {})
                lines.extend([
                    f"### {finding['candidate_id']}", "",
                    f"Classification: {finding['classification']}",
                    f"Severity: {finding['severity']}", f"Confidence: {finding['confidence']}",
                    f"Endpoint: {candidate.get('method', '')} {candidate.get('url', '')}",
                    f"Occurrences: {candidate.get('occurrences', 0)}", "",
                    f"**Title:** {finding.get('title', '')}", "",
                    f"**Summary:** {finding.get('summary', '')}", "",
                    f"**Reasoning:** {finding.get('reasoning', '')}", "",
                    f"**Expected Result:** {finding.get('expected_result', '')}", "",
                    f"**Actual Result:** {finding.get('actual_result', '')}", "",
                    f"**User impact:** {finding.get('user_impact', '')}", "",
                    f"**Recommended action:** {finding.get('recommended_action', '')}", "",
                ])
        lines.extend(["## Evidence", "", "Deterministic candidate evidence is preserved in the JSON report.", "", "## Recommended QA Actions", ""])
        for finding in result["findings"]:
            lines.append(f"- {finding['candidate_id']}: {finding.get('recommended_action', '')}")
        return "\n".join(lines) + "\n"


async def generate_report(
    findings_file=None,
    results_dir="results",
    run_id=None,
    api_key=None,
    ai_keys_pool=None,
    provider_id="gemini",
    model_name=None,
    endpoint=None,
    budget_seconds=None,
):
    """
    Run the AI analysis stage using Gemini, OpenAI, Claude, DeepSeek, or Local LLM.

    Args:
        findings_file: Explicit path to a qa_findings_*.json file. When omitted
            the newest file in `results_dir` is used, which is only safe for
            single-run/CLI usage.
        results_dir: Directory to read from and write to.
        run_id: Suffix for output filenames. Defaults to a timestamp.
        api_key: User's primary personal API key.
        ai_keys_pool: Optional list of backup key dictionaries for automatic failover.
        provider_id: AI provider ("gemini", "openai", "anthropic", "deepseek", "local_llm").
        model_name: Model name.
        endpoint: Custom endpoint URL.
        budget_seconds: Wall-clock budget for the whole stage (default
            QA_AI_BUDGET_SECONDS or 480s).
    """
    path = (
        Path(findings_file)
        if findings_file
        else GeminiQAAnalyzer.find_latest_findings(results_dir)
    )
    if path is None:
        print(f"No QA findings file found under {results_dir}/qa_findings_*.json")
        return None

    data = GeminiQAAnalyzer.load_findings(path)
    data["source_file"] = str(path)
    analyzer = GeminiQAAnalyzer(
        api_key=api_key,
        provider_id=provider_id,
        model_name=model_name,
        endpoint=endpoint,
        key_pool=ai_keys_pool,
        budget_seconds=budget_seconds,
    )
    result = await analyzer.analyze(data)

    results_path = Path(results_dir)
    results_path.mkdir(parents=True, exist_ok=True)

    suffix = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = results_path / f"gemini_qa_report_{suffix}.json"
    md_path = results_path / f"gemini_qa_report_{suffix}.md"

    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(analyzer.render_markdown(result), encoding="utf-8")

    summary = result["summary"]
    print("\n" + "=" * 60 + "\nGEMINI QA ANALYZER VERIFICATION\n" + "=" * 60)
    print(f"\nRAW CANDIDATES: {summary['total_candidates']}")
    print(f"\nAI-ANALYZED: {summary['ai_analyzed']} (deterministic verdicts: {summary['deterministic_verdicts']})")
    print(f"\nCONFIRMED BUGS: {summary['confirmed_bugs']}")
    print(f"\nHIGH-CONFIDENCE CANDIDATES: {summary['high_confidence_candidates']}")
    print(f"\nNEEDS MANUAL REVIEW: {summary['needs_manual_review']}")
    print(f"\nEXPECTED BEHAVIOR: {summary['expected_behavior']}")
    print(f"\nINFORMATIONAL: {summary['informational']}")
    print(f"\nANALYSIS FAILURES: {summary['analysis_failures']}")
    print("\nSEVERITY:")
    for key, value in summary["severity_counts"].items():
        print(f"  {key.upper()}: {value}")
    print("\nSECURITY:\n  Secrets redacted: YES\n\nEVIDENCE:\n  Evidence preserved: YES")
    print(
        f"\nREPORT:\n  JSON generated: YES\n  Markdown generated: YES"
        f"\n  JSON: {json_path}\n  Markdown: {md_path}"
    )
    for finding in result["findings"]:
        print(f"\n{finding['candidate_id']}: {finding['classification']}")

    # Surface the paths so callers do not have to re-glob the directory.
    result["json_path"] = str(json_path)
    result["md_path"] = str(md_path)

    return result


if __name__ == "__main__":
    asyncio.run(generate_report())
