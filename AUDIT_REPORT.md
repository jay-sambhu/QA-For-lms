# AI QA Agent — Codebase Audit and Fix Report

**Date:** 2026-08-26
**Scope requested:** run the project, analyse the whole codebase, find errors, verify every function, fix everything found — including the Next.js web app.
**Files changed:** 14 modified, 2 created (1,912 insertions / 810 deletions).

---

## 1. Read this first: what was and was not actually executed

You asked for a full live run. That is not possible from inside this sandbox, and it would be dishonest to imply otherwise. The environment has no outbound network (the HTTP proxy returns 403), and the project's `.venv` is built for CPython 3.12 with binary wheels that cannot be loaded by the sandbox's system Python 3.10.

**Executed live, on real data:**

Stage 2 (`bug_detector.py`), Stage 3 (`gemini_analyzer.py`), and Stage 4 (`qa_report_generator.py`) were run end to end against the real 30-page `dplms.com` crawl already in `results/`, and again against a synthetic crawl built to exercise the console-error and network-failure paths. All 47 unit tests were run. Every tracked Python file was byte-compiled. The Next.js app was type-checked, linted, and production-built. The FastAPI routing and path-containment logic was verified by AST inspection and by extracting the pure helpers and unit-testing them directly.

**Not executed, and why:**

Stage 1 (the live Playwright crawl) could not run because Chromium cannot reach the network and `playwright`'s `greenlet._greenlet` extension is ABI-locked to CPython 3.12. The real Gemini API call could not run for the same network reason — Stage 3 was exercised through its degraded path, which correctly fell back to `needs_manual_review` rather than crashing. The FastAPI app could not be imported because `pydantic_core` is a 3.12-only binary. `next build` fails in the sandbox only on fetching Geist from Google Fonts; with the fonts stubbed in a throwaway copy, the build compiles and prerenders cleanly, so the failure is environmental, not a code defect.

**To close the loop on your own machine:**

```bash
cd ~/ai-qa-agent
.venv/bin/python run_qa.py https://dplms.com --max-pages 10   # Stages 1-4 live, real Gemini call
.venv/bin/python verify_root_cause_grouping.py                # invariant self-check
.venv/bin/uvicorn api.main:app --reload                       # then `cd web && npm run dev`
```

---

## 2. The three defects that mattered most

### 2.1 The web UI could never display a report — it read the wrong schema

`web/src/app/page.tsx` was written against the *Stage 3* (`gemini_qa_report_*.json`) shape, but `GET /api/scans/{id}` serves the *Stage 4* (`final_qa_report_*.json`) shape. Every field the component read was absent from the payload it actually received: it looked for `results.target` where the API sends `results.report_metadata.target`, for `results.summary.needs_manual_review` where the key is `summary.manual_review`, for `finding.summary` where the field is `finding.description`, and for `finding.candidate.occurrences` where it is `finding.affected_pages_count`. A completed scan therefore rendered a report with a blank target, zeroed counters, and empty finding bodies. The mapping is now corrected and cross-checked field by field against a real generated report.

### 2.2 Two of the three finding types were silently discarded

`bug_detector.group_findings_by_root_cause()` opened with `if finding.get('type') != 'http_error': continue`. Console errors and network failures were detected, classified, given severities, and then thrown away before the candidate list was built — so they never reached Gemini and never appeared in any report. On a site whose only problem is a JavaScript exception, the tool reported nothing wrong.

All three types now group. Proof, from a synthetic crawl containing two console errors and two network failures and zero HTTP errors:

```
page-level types : console_error: 2, network_failure: 1
candidate types  : console_error: 1, network_failure: 1
CANDIDATE-001 [console_error/high]  occ=2 pages=2  JavaScript runtime error detected on 2 page(s)
CANDIDATE-002 [network_failure/med] occ=1 pages=1  Request to .../api/inventory failed to complete
```

Before the fix both candidates were absent and the final report was empty.

### 2.3 `GET /api/scans/{scan_id}` had no authentication at all — IDOR

The endpoint took a scan id, looked it up, and returned it. No token, no ownership check. Since the backend runs with the Supabase **service role key**, Row Level Security is bypassed, so any unauthenticated caller who knew or guessed a scan id received another user's target URL and their complete QA report — including whatever the crawler captured behind an `--auth-token`. This was the most serious defect in the repository.

All `/api/*` routes now require a verified Supabase bearer token through a shared `require_user` dependency, and `get_scan_status` additionally checks `scan["user_id"] == user.id`, returning 404 rather than 403 so the endpoint does not confirm which ids exist. Verified by AST sweep:

```
[GUARDED] POST  /api/scans             create_scan
[GUARDED] GET   /api/scans             list_scans
[GUARDED] GET   /api/scans/{scan_id}   get_scan_status
[public ] GET   /                      read_root
RESULT: all /api routes require authentication
```

---

## 3. Every defect found, by file

### `api/main.py`

| Severity | Defect | Fix |
|---|---|---|
| **Critical** | `get_scan_status` unauthenticated → IDOR across all users (§2.3) | `require_user` dependency + `user_id` ownership check |
| **High** | `os.path.join(ROOT_DIR, scan["json_path"])` opened a database-supplied path with no containment check — a tampered row could read any file the process could reach | `_resolve_report_path()` rejects anything resolving outside `ROOT_DIR`, including absolute paths and shared-prefix siblings like `/srv/app-evil` |
| **High** | `subprocess.run(...)` had no `timeout`; a wedged Chromium pinned a background worker forever and the scan stayed `running` indefinitely | `timeout=PIPELINE_TIMEOUT_SECONDS` (default 1800, env-overridable) with the scan marked `failed` on expiry |
| **High** | No `--run-id` passed, so concurrent scans globbed "newest file in `results/`" and could return each other's reports | `--run-id <scan_id>` threaded through; every stage writes id-namespaced filenames |
| Medium | No URL or `max_pages` validation — any string was queued, and `max_pages: 100000` was accepted | Pydantic `field_validator`s enforce absolute http(s) and `1 <= max_pages <= 100` |
| Medium | `scan["json_path"]` raised `KeyError` when the column was null | `scan.get("json_path")`, plus `results: None` when the file is unreadable |
| Medium | Absolute paths stored in the DB broke as soon as the repo moved | `_relative_to_root()` stores repo-relative paths |
| Low | `report_path: str = None` — invalid annotation | `Optional[str]` |
| Low | No way for the UI to list a user's own scans | Added `GET /api/scans` |

Path-containment logic verified against 11 cases including `../../../../etc/passwd`, `/etc/passwd`, `/srv/app-evil/secret.json`, and `results/../results/a.json` — all resolved correctly.

### `bug_detector.py`

| Severity | Defect | Fix |
|---|---|---|
| **High** | Console and network findings dropped from grouping (§2.2) | All types group; new `_build_candidate()` / `_candidate_narrative()` |
| **High** | `should_ignore_network_failure` did `'net::ERR_ABORTED' in failure` on a `None` — the confirmed `TypeError: argument of type 'NoneType' is not iterable` at line 455 | `(failure or '').strip()`, empty reason treated as ignorable |
| **High** | `is_first_party` used substring matching, so `dplms.com.evil.com` and `notdplms.com` were classified as first-party | New `normalize_host()` + exact-or-proper-subdomain match |
| Medium | `find_matching_console_errors` matched on `f'{status}' in error_text`, so any console message containing "404" — including a coordinate or a timestamp — was folded into an unrelated HTTP finding | Four compiled regexes matching status codes in genuine error contexts |
| Medium | `screenshots` and `affected_pages` were de-duplicated independently and drifted out of alignment; anything zipping them paired the wrong screenshot with the wrong page | Single ordered `page_screenshots` map; emits both the list and explicit `{page, screenshot}` pairs |
| Medium | `occurrences` counted pages, not events, so one page failing 30 times reported 1 | `occurrences += deduplicated_count` |
| Medium | Network failures were never de-duplicated per page | Keyed on `(page, url, method, reason)` with `deduplicated_count` |
| Medium | `classify_http_status` crashed on a non-integer status | `isinstance(status, int)` guard |
| Low | `generate_root_cause_key` lowercased the path, so `/Product` and `/product` merged | Path case preserved |
| Low | `'api' in url` matched `/therapist/`, `/rapid/`, `/capital/` | Whole-segment match against `{api, apis, graphql, rest, v1, v2, v3}` |
| Low | `get_page_title`/`get_page_screenshot` read a non-existent key | `page.get('url')` |
| Low | `import re` inside a function; unused `import os` | Moved to module top; removed |

### `gemini_analyzer.py`

| Severity | Defect | Fix |
|---|---|---|
| **High** | The API key was placed in the URL query string, where it lands in proxy logs, server access logs, and any error message echoing the URL | Sent as the `x-goog-api-key` header. Verified: `URL: .../gemini-3-flash-preview:generateContent` with no key present |
| **High** | No request timeout — a hung connection blocked the pipeline indefinitely | `timeout=120` |
| **High** | `load_dotenv(dotenv_path=".env")` resolved against the CWD, so the key silently went missing whenever the pipeline was launched from anywhere but the repo root (which is exactly what the API's `cwd=ROOT_DIR` masked) | Anchored to `Path(__file__).resolve().parent` |
| **High** | `severity_counts` had no `critical` bucket, so a critical verdict from Gemini was counted as `info` and the UI's critical+high sum could never be right | `SEVERITY_ORDER` includes `critical` |
| Medium | A legitimate `needs_manual_review` verdict was counted as an analysis failure, inflating the error count | `analysis_failed` sentinel set only by the real fallback path |
| Medium | Raw API error text was re-raised unredacted, and `REDACTION_PATTERNS` missed bare `key=`, `access_token`, `refresh_token`, `id_token`, `client_secret`, `session_id` | Patterns compiled once at class level and extended; `self._redact()` applied before re-raise. All six probe strings redacted correctly |
| Medium | Empty `candidates` array and multi-part responses were mishandled | Explicit empty handling; parts joined |
| Medium | Sets used for ordered output → JSON key order changed run to run under different `PYTHONHASHSEED` | Ordered tuples with sets derived from them |
| Low | Retry fired with no back-off; shadowing inner `import json` / `import asyncio` | 2.0 s delay; shadowing imports removed |

### `crawler/crawler.py` and `crawler/network.py`

| Severity | Defect | Fix |
|---|---|---|
| **High** | `record_request_failure` passed `request.failure` (often `None`) straight through, which is the direct cause of the `TypeError` in Stage 2 | Normalised to `""` at the source. Verified against `None`, `""`, `ERR_ABORTED`, `ERR_CONNECTION_REFUSED` |
| **High** | `monitor` was created inside `async with async_playwright()`, so a browser launch failure left it undefined when the summary was built, turning a clear launch error into a confusing `NameError` | Created before the browser |
| **High** | No `try/finally` around the crawl loop — an exception leaked the Chromium process | `finally: await browser.close()` |
| **High** | Screenshots were written to a shared directory, so a rerun overwrote them and older reports pointed at images from a different crawl | Per-run `screenshots/<run_id>/` |
| Medium | A garbage start URL produced a confusing Playwright error deep in the crawl | `ValueError` at construction with a usable message. Verified against 7 bad inputs |
| Medium | `netloc.lower()` corrupted userinfo credentials; `:443`/`:80` produced duplicate URLs; `mailto:`/`javascript:` were mangled into nonsense; duplicate slashes created distinct URLs for the same page | Full rewrite of `normalize_url`; 14 cases verified |
| Medium | Substring host matching let `dplms.com.evil.com` be crawled as internal | `_base_host()` with apex/www equivalence; 7 cases verified |
| Medium | A page that failed to load was counted as crawled | `pages_crawled` counts successes; `pages_attempted` added |
| Low | Absolute screenshot paths broke report portability; `location` and `page` were not captured on console/network events | Repo-relative paths; `page` and `location` recorded |

### `qa_report_generator.py`

| Severity | Defect | Fix |
|---|---|---|
| **High** | `len(f['page'])` and `len(f['url'])` raised `TypeError` whenever either was `None` — which is always the case for console-error findings, so the generator crashed on exactly the findings §2.2 had just started letting through | `_truncate()` tolerates `None` |
| Medium | Every label in the detailed findings collapsed into one run-on paragraph, because consecutive plain lines are merged by every Markdown renderer | Bullet lines, with the exact substrings the tests assert preserved |
| Medium | Screenshot existence was checked against the CWD, so every screenshot showed as "Not available" when run from elsewhere | `base_dir`-anchored `_screenshot_exists()` |
| Medium | `pages_crawled` lookup crashed on a malformed crawl file | `(OSError, json.JSONDecodeError)` caught; both path candidates tried |
| Low | Returned `Path` objects that were not JSON-serializable for API callers | Returns `str` |

### `run_qa.py`

Rewritten. Every stage previously re-globbed for the newest file in `results/`, which is not a per-scan identity — two overlapping API scans read each other's output. A shared `run_id` and explicit file paths are now threaded through all four stages. Added `--run-id` and `--output-dir`, `--max-pages` validation, per-stage failure detection (the script previously reported success even when a stage produced nothing), exit 2 for an invalid URL, exit 1 for a failed stage, and `sys.exit(asyncio.run(main()))` so the exit code actually reaches the API. The `Final JSON:` / `Final Markdown:` stdout prefixes were deliberately kept byte-stable because `api/main.py` parses them.

### `web/` (Next.js)

Beyond the schema fix in §2.1: added `Severity` / `Finding` / `QAReport` / `ScanStatus` types, removing all three `any` uses; the polling fetch now sends `Authorization: Bearer` (matching the newly-authenticated endpoint); the poll effect has a `cancelled` guard against setting state after unmount; a config-error screen replaces the crash when Supabase env vars are missing; a `sessionLoaded` gate stops the sign-in form flashing on reload; the auth inputs are wrapped in a `<form onSubmit>` so Enter submits; server `detail` messages surface instead of a generic failure; sign-out clears scan state so the next user cannot see the previous report; unused `LogIn` import removed; and `layout.tsx` metadata changed from the `create-next-app` placeholder to real title and description.

One lint error was introduced during this work and then fixed: `setSessionLoaded(true)` called synchronously in an effect body (`react-hooks/set-state-in-effect`). Resolved by deriving the initial value — `useState(!supabase)` — since `supabase` is a module constant.

### Housekeeping

`verify_root_cause_grouping.py` hardcoded `cart_candidate['occurrences'] == 30` and `total_candidates == 2` from one historical `dplms.com` crawl, so it printed "✗ INCOMPLETE" on every other input — a permanently red check that trains you to ignore it. It also raised `NameError` on `dedup_ratio` when there were zero candidates. Rewritten as 14 structural invariants (evidence preserved, IDs unique, `page_screenshots` aligned with `affected_pages`, occurrences never below page count, counts internally consistent) that hold for any crawl. Both the real and synthetic datasets now pass all 14 and exit 0.

`explorer.py` printed `Target: https://example.com` while the prompt hardcoded `https://dplms.com` — it explored a different site than it reported. The URL is now interpolated and accepted as a CLI argument. `test_url_normalization.py` created empty `results/` and `screenshots/<timestamp>/` directories in the repo on every run; it now uses a temp directory. `test_normalization_standalone.py` and `verify_fix.py` each carry their own stale copy of `normalize_url` and so would pass even if the crawler broke — both now carry a prominent warning saying so. Created `crawler/__init__.py` (the package had only the typo'd `_init_.py`) and `requirements.txt` pinned to your installed versions.

---

## 4. Verification results

```
Byte-compile, all tracked .py files ........................ OK
Unit tests (3 suites) ...................................... 47 passed, 0 failed
test_url_normalization.py (real implementation) ............ all passed
test_normalization_standalone.py / verify_fix.py ............ all passed
verify_root_cause_grouping.py, real dplms.com crawl ........ 14/14 invariants, exit 0
verify_root_cause_grouping.py, synthetic console+network ... 14/14 invariants, exit 0
Stages 2->3->4 on real 30-page crawl ....................... completed, 2 candidates,
                                                             occurrences=30 on the grouped one
Stages 2->3->4 on synthetic crawl .......................... completed, console + network
                                                             candidates present in final report
Determinism across PYTHONHASHSEED 0 / 1 / 12345 ............ byte-identical incl. key order
                                                             (only `generated_at` differs)
API route auth sweep (AST) ................................. all /api routes guarded
API path containment (11 cases) ............................ all correct
Gemini key placement + timeout + redaction ................. key absent from URL, header set,
                                                             timeout 120s, 6/6 secrets redacted
NetworkMonitor failure=None ................................ no exception
crawler URL logic (14 + 7 + 7 cases) ....................... all correct
web: tsc --noEmit .......................................... 0 errors
web: eslint --max-warnings=0 ............................... clean
web: next build ............................................ compiles and prerenders 4/4 routes
                                                             (fonts stubbed; offline only)
```

---

## 5. Two things left for you

**The typo'd package file.** `crawler/_init_.py` (single underscores) is still on disk — you declined its deletion, so I created the correct `crawler/__init__.py` alongside it rather than removing anything. The typo file is an empty, harmless no-op, but it is tracked in git and will confuse the next reader. If you want it gone: `git rm crawler/_init_.py`.

**Dead code.** `old_crawler.py` is superseded by `crawler/crawler.py`, and `test_agent.py` is a one-off browser-use smoke script rather than a test. Both still import cleanly and neither is referenced by the pipeline, so I left them untouched.
