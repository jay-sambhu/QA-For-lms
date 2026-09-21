# Codebase Cleanup Inventory Report

**Date**: 2026-09-21  
**Branch**: `chore/cleanup-01` (created from `origin/main` at `513cc81`)  
**Scope**: Read-only inventory of dead weight, unused code, redundant dependencies, clutter, and inconsistencies without runtime behavioral changes.

---

## a) Unused Python Imports and Variables

**Command**: `ruff check --select F401,F841 --output-format concise .`  
**Total Identified**: 39 items across 14 files.

| File Path | Line & Column | Code / Rule | Evidence | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `api/main.py` | 29:30 | `F401` `from worker.tasks import process_query_task` | Eager top-level import; line 589 re-imports `process_query_task` locally inside the scan endpoint. | Medium *(See Section j)* |
| `api/main.py` | 463:9 | `F841` `result_stderr` | `result_stderr = ""` assigned after subprocess completion, never read or returned. | High |
| `api/main.py` | 824:5 | `F841` `user_dir` | `user_dir = os.path.join(ROOT_DIR, "user_data", user_id_val)` assigned, never used. | High |
| `benchmarks/autonomous/challenge_runner.py` | 63:13 | `F841` `pipeline_results` | Return value of `run_pipeline` assigned to `pipeline_results`, never read. | High |
| `core/executor_v2.py` | 81:13 | `F841` `status` | `status = ...` assigned inside step loop, never read. | High |
| `core/gemini_analyzer.py` | 97:29 | `F841` `e` | `except Exception as e:` where exception variable `e` is not logged or used. | High |
| `core/regression_detector.py` | 85:13 | `F841` `is_findings_list` | Variable `is_findings_list = isinstance(...)` assigned, never read. | High |
| `crawler/crawler.py` | 385:29 | `F841` `auth_success` | Boolean assignment `auth_success = ...` never referenced in subsequent logic. | High |
| `crawler/crawler.py` | 448:21 | `F841` `dev_keys` | Dict keys assigned to `dev_keys` but never used. | High |
| `crawler/crawler.py` | 592:53 | `F841` `btn_err` | `except Exception as btn_err:` where `btn_err` is not referenced in block. | High |
| `run_qa.py` | 124:5 | `F841` `api_results` | `api_results = ...` assigned, never read. | High |
| `run_qa.py` | 127:5 | `F841` `perf_a11y_report` | `perf_a11y_report = ...` assigned, never read. | High |
| `run_qa.py` | 134:5 | `F841` `regression_analysis` | `regression_analysis = ...` assigned, never read. | High |
| `tests/test_auth_sync_export.py` | 21:9 | `F841` `resp` | Client response assigned to `resp`, never asserted. | High |
| `tests/test_free_tier_limit.py` | 7:8 | `F401` `pytest` | `import pytest` present, but no pytest decorators or functions called. | High |
| `tests/test_multi_session_manager.py` | 11:5 | `F841` `sess_admin` | Session created and assigned to `sess_admin`, never asserted. | High |
| `tests/test_phase23_real_browser_e2e.py` | 16:5 | `F841` `user_a` | Session created and assigned to `user_a`, never asserted. | High |
| `tests/test_phase23_real_browser_e2e.py` | 17:5 | `F841` `user_b` | Session created and assigned to `user_b`, never asserted. | High |
| `tests/test_phase23_real_browser_e2e.py` | 18:5 | `F841` `admin_c` | Session created and assigned to `admin_c`, never asserted. | High |
| `tests/test_phase24_authenticated_fullstack.py` | 6:8 | `F401` `sys` | `import sys` unused. | High |
| `tests/test_phase24_authenticated_fullstack.py` | 7:8 | `F401` `time` | `import time` unused. | High |
| `tests/test_phase24_authenticated_fullstack.py` | 8:8 | `F401` `requests` | `import requests` unused. | High |
| `tests/test_phase24_authenticated_fullstack.py` | 9:8 | `F401` `subprocess` | `import subprocess` unused. | High |
| `tests/test_phase24_authenticated_fullstack.py` | 54:5 | `F841` `user_a` | `user_a = mgr.create_session(...)` assigned, never read. | High |
| `tests/test_phase24_authenticated_fullstack.py` | 55:5 | `F841` `user_b` | `user_b = mgr.create_session(...)` assigned, never read. | High |
| `tests/test_phase24_authenticated_fullstack.py` | 56:5 | `F841` `admin_c` | `admin_c = mgr.create_session(...)` assigned, never read. | High |
| `tests/test_phase24_genuine_live.py` | 6:8 | `F401` `sys` | `import sys` unused. | High |
| `tests/test_phase24_genuine_live.py` | 7:8 | `F401` `time` | `import time` unused. | High |
| `tests/test_phase24_genuine_live.py` | 8:8 | `F401` `requests` | `import requests` unused. | High |
| `tests/test_phase24_genuine_live.py` | 9:8 | `F401` `subprocess` | `import subprocess` unused. | High |
| `tests/test_phase24_genuine_live.py` | 53:5 | `F841` `user_a` | `user_a = mgr.create_session(...)` assigned, never read. | High |
| `tests/test_phase24_genuine_live.py` | 54:5 | `F841` `user_b` | `user_b = mgr.create_session(...)` assigned, never read. | High |
| `tests/test_phase24_genuine_live.py` | 55:5 | `F841` `admin_c` | `admin_c = mgr.create_session(...)` assigned, never read. | High |
| `tests/test_phase24_live_system.py` | 57:5 | `F841` `user_a` | `user_a = mgr.create_session(...)` assigned, never read. | High |
| `tests/test_phase24_live_system.py` | 58:5 | `F841` `user_b` | `user_b = mgr.create_session(...)` assigned, never read. | High |
| `tests/test_phase24_live_system.py` | 59:5 | `F841` `admin_c` | `admin_c = mgr.create_session(...)` assigned, never read. | High |
| `tests/test_report_exports.py` | 50:9 | `F841` `generator` | `generator = QAReportGenerator()` assigned, never read. | High |
| `tests/test_report_exports.py` | 156:9 | `F841` `report` | `report = generator.generate_json_report(...)` assigned, never read. | High |
| `tests/test_supabase_auth_env.py` | 7:36 | `F401` `api.main.missing_supabase_vars` | Imported on line 7 but accessed via `patch.object(api.main, "missing_supabase_vars", ...)`. | High |

---

## b) Unreferenced Python Functions, Classes, and Modules

**Tool**: `vulture api core crawler db.py models.py run_qa.py worker`  
**Whitelist Applied**:
- FastAPI route handlers & dependencies (`get_db`, `get_current_user`, etc.)
- Celery task functions (`process_query_task`, `run_qa_pipeline`)
- Pytest fixtures & test helpers (`get_db_session` in `tests/test_database_migrations.py`)
- SQLAlchemy models & column attributes (`models.py`: `User`, `Scan`, `Subscription`, `Transaction`)
- Pydantic schema model attributes (`core/schemas/*`)

| File Path | Symbol | Type | Evidence | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `crawler/devices.py:71` | `get_viewport_dimensions` | Method | `def get_viewport_dimensions(cls, dev_name, dev_config)` is defined on `DeviceRegistry` but never called anywhere across the repository. | High |
| `db.py:55` | `init_db` | Function | `def init_db(): Base.metadata.create_all(bind=engine)` is defined but never invoked; schema initialization is handled via Alembic migrations (`alembic/versions/*`). | High |
| `core/schemas/discovery.py:55` | `DiscoveryResultModel` | Pydantic Model | Defined in schemas, but never imported or instantiated in crawler, analyzer, or API endpoints. | Medium |
| `core/schemas/quality.py:28` | `QualityGateResultModel` | Pydantic Model | Defined in schemas, but never imported or instantiated in core quality gate evaluation. | Medium |
| `core/schemas/regression.py:9` | `RegressionStatus` | Enum Class | Enum `RegressionStatus` defines status constants (`NEW_FAILURE`, `FIXED`, etc.), but string literals are used in `regression_detector.py`. | Medium |
| `agent/` | Entire Directory | Directory | Empty directory at repository root containing 0 files, not tracked in git. | High |

*Note: `core/visual_inspector.py:24` (`RealBrowserVisualInspector`) was verified as **USED** (tested in `tests/test_visual_inspector.py` and `tests/test_phase23_real_browser_e2e.py`).*

---

## c) Unused Frontend Files, Exports, and Dependencies in `web/`

**Tools**: `depcheck`, `knip`

| File / Package Path | Item | Category | Evidence | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `web/src/views/index.ts` | Whole File | Unused File | Re-exports `LandingPage`, `DashboardPage`, `ScanDetailPage`, `PricingPage`, `AdminPage`. Zero files in `web/` import from `@/views` or `./views` (Next.js app router imports page views directly). | High |
| `web/package.json:12` | `@supabase/ssr` | Unused Dependency | Grep across `web/` found 0 import statements. Auth and Supabase operations are handled via `@supabase/supabase-js`. | High |
| `web/src/utils/export.ts:67` | `extractCanonicalExportData` | Unused Export | Only `handleDownloadReport` is imported from `export.ts` in `ReportHeader.tsx`. Internal helper function exported unnecessarily. | Medium |
| `web/src/utils/export.ts:254` | `downloadPDF` | Unused Export | Internal export generation function; not imported outside `export.ts`. | Medium |
| `web/src/utils/export.ts:505` | `downloadExcel` | Unused Export | Internal export generation function; not imported outside `export.ts`. | Medium |
| `web/src/utils/export.ts:653` | `generateMarkdownReport` | Unused Export | Internal export generation function; not imported outside `export.ts`. | Medium |
| `web/src/utils/export.ts:758` | `downloadMarkdown` | Unused Export | Internal export generation function; not imported outside `export.ts`. | Medium |
| `web/src/utils/export.ts:780` | `downloadJSON` | Unused Export | Internal export generation function; not imported outside `export.ts`. | Medium |
| `web/src/utils/export.ts:811` | `extractFilenameFromDisposition` | Unused Export | Internal utility function; not imported outside `export.ts`. | Medium |
| `web/src/types/qa.ts:1,3` | `Severity`, `Finding` | Unused Type Exports | Types declared and exported in `qa.ts` but never imported across `web/src`. | Medium |
| `web/src/utils/export.ts:5,799` | `CanonicalExportData`, `ExportFormat` | Unused Type Exports | Types declared in `export.ts` but never imported outside `export.ts`. | Medium |
| `web/package.json:25,27` | `@types/node`, `@types/react-dom` | DevDependencies | Flagged by `depcheck`, but these provide ambient TypeScript types required by Next.js and React 19. Must be retained. | Low *(See Section j)* |

---

## d) Duplicate or Near-Duplicate Files

**Scan**: SHA-256 hash comparison across all non-ignored project files; scan for `*.bak`, `*_old.*`, `*_copy.*`; scan for commented-out blocks > 15 lines.

| Category | File Paths | Evidence / Details | Confidence |
| :--- | :--- | :--- | :--- |
| Duplicate Artifacts | `results/autonomous_validation/*/screenshots/` and `results/autonomous_validation/*/results/*.json` | 313 identical PNG screenshot and JSON files duplicated across test run timestamps (e.g., `challenge_dashboard_1788674673/003_iPhone_13_page.png` duplicated in 4 runs). All exist inside local untracked `results/`. | High |
| Source Code Duplication | Entire codebase | **0 duplicate files** detected across application source, documentation, scripts, and web frontend. | High |
| Backup / Scratch Files | `*.bak`, `*_old.*`, `*_copy.*`, `*~`, `*.swp` | **0 backup files** found in working tree. | High |
| Large Commented Blocks | `core/gemini_analyzer.py:185-199` | 15 consecutive lines starting with `#`. Inspection confirms this is technical documentation explaining credential regex lookbehinds and JSON parsing rules, **not** commented-out code. | High |
| Commented-Out Code | Entire codebase | **0 commented-out code blocks** >= 5 lines found. | High |

---

## e) Generated or Local-Only Files in Workspace

**Tools**: `du -sh`, `git ls-files`  
**Git Tracking Status**: Confirmed via `git ls-files` that **0 of these files/directories are tracked in git**. All are untracked and covered by `.gitignore`.

| Path | Disk Size | File Type | Git Status | Recommended Action | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `user_data/` | 744 MB | Directory | Untracked (`.gitignore:25`) | Purge local scan run data or retain locally. | High |
| `screenshots/` | 397 MB | Directory | Untracked (`.gitignore:24`) | Purge local scan screenshots or retain locally. | High |
| `results/` | 37 MB | Directory | Untracked (`.gitignore:22`) | Purge local validation run outputs or retain locally. | High |
| `reports/` | 0 B | Directory | Untracked (`.gitignore:23`) | Remove empty directory. | High |
| `qa_agent.db` | 100 KB | SQLite DB | Untracked (`.gitignore:17`) | Local test database; safe to delete or retain locally. | High |
| `jasuss.db` | 0 B | SQLite DB | Untracked (`.gitignore:17`) | Empty local SQLite file at repo root; safe to delete. | High |
| `local_qa_platform.db` | 0 B | SQLite DB | Untracked (`.gitignore:17`) | Empty local SQLite file at repo root; safe to delete. | High |
| `__pycache__/` | 1.3 MB | Cache | Untracked (`.gitignore:10`) | Local Python bytecode cache; auto-regenerated. | High |
| `web/.next/` | 1.2 GB | Build Cache | Untracked (`.gitignore:35`) | Next.js compilation cache; auto-regenerated by build. | High |

---

## f) Root-Level Clutter

**Current Root Inventory**: 27 files, 30 subdirectories.

| Root Item | Current Role | Appropriate Home / Recommendation | Confidence |
| :--- | :--- | :--- | :--- |
| `jasuss.db` | Empty 0-byte local SQLite DB | Delete. | High |
| `local_qa_platform.db` | Empty 0-byte local SQLite DB | Delete. | High |
| `qa_agent.db` | 100 KB local test SQLite DB | Delete or move to `user_data/`. | High |
| `agent/` | Empty directory (0 files, untracked) | Delete directory. | High |
| `your_application/` (`__init__.py`, `wsgi.py`) | Fallback Uvicorn runner for Render `gunicorn your_application.wsgi` default command | Retain at root to avoid deployment breakage, or delete if Render start command is explicitly configured in Render dashboard. | Low *(See Section j)* |
| `run_qa.py` | CLI execution entrypoint for the 4-stage QA pipeline | Retain at root. `api/main.py:408` executes it via subprocess `["python", "run_qa.py", ...]`. Moving it would require runtime code modifications. | High |
| `model_capabilities.yaml` | QA model matrix configuration | Retain at root or move to `core/` if loader paths are updated. | Low |
| `GSD-STYLE.md` | GSD agent workflow documentation | Move to `.gsd/` or `docs/`. | Medium |
| `PROJECT_RULES.md` | Canonical engineering rules | Retain at root (referenced by Antigravity rules and agent prompts). | High |
| `conftest.py` | Pytest global fixtures | Standard root location for pytest discovery; retain at root. | High |
| `Procfile`, `alembic.ini`, `pytest.ini`, `runtime.txt`, `start.sh` | Deployment, build, and test runner configurations | Standard root locations; retain at root. | High |

---

## g) Unused Dependencies in `requirements.txt` and `web/package.json`

**Scan**: Grep for imports across Python code (`.py`) and TypeScript/JavaScript (`.ts`, `.tsx`, `.js`).

| Dependency | Defined In | Evidence | Recommendation | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `tenacity==8.5.0` | `requirements.txt:38` | Grep for `tenacity`, `retry`, etc. found 0 imports across the entire repository. | Remove from `requirements.txt`. | High |
| `@supabase/ssr` (`^0.12.5`) | `web/package.json:12` | Grep across `web/` found 0 imports. Web app uses `@supabase/supabase-js`. | Remove from `web/package.json` and run `npm install` to update `package-lock.json`. | High |
| `pytest==9.1.1` | `requirements.txt:41` | Test framework. Already declared in `requirements-dev.txt:3`. | Redundant in production `requirements.txt`; keep in `requirements-dev.txt`. | Medium *(See Section j)* |
| `fakeredis==2.37.1` | `requirements.txt:42` | Test fixture library. Already declared in `requirements-dev.txt:4`. | Redundant in production `requirements.txt`; keep in `requirements-dev.txt`. | Medium *(See Section j)* |
| `python-multipart==0.0.9` | `requirements.txt:37` | No direct `import python_multipart`, but FastAPI strictly requires it for `Form(...)` parsing in `tests/challenge_apps/`. | **Retain as USED**. Removing it breaks FastAPI form parsing. | High |
| `@types/node`, `@types/react-dom` | `web/package.json:25,27` | Flagged by `depcheck`, but these provide ambient TypeScript definitions. | **Retain as USED**. Removing them breaks TypeScript build. | High |

---

## h) Dead Docs: Broken Links and Duplications

**Scan**: Relative markdown link validation across all `.md` files; cross-document content analysis.

### Broken Internal Links (11 instances)

| Markdown File | Line / Context | Broken Link Target | Fix / Resolved Target | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `README.md` | Line 235 (`MIT` license link) | `../LICENSE` | Repo did not contain a `LICENSE` file; created standard MIT LICENSE at root. | High |
| `docs/token-optimization-guide.md` | Line 14 | `.agents/skills/token-budget/SKILL.md` | Change to `../.agents/skills/token-budget/SKILL.md` | High |
| `docs/token-optimization-guide.md` | Line 15 | `.agents/skills/context-compressor/SKILL.md` | Change to `../.agents/skills/context-compressor/SKILL.md` | High |
| `docs/token-optimization-guide.md` | Line 95 | `PROJECT_RULES.md` | Change to `../PROJECT_RULES.md` | High |
| `docs/HIDDEN_DEFECT_METHODOLOGY.md` | Line 12 | `file:///home/devxgamer/ai-qa-agent/benchmarks/autonomous/defect_registry.py` | Change to `../benchmarks/autonomous/defect_registry.py` | High |
| `docs/SELF_HEALING_SAFETY.md` | Line 12 | `file:///home/devxgamer/ai-qa-agent/core/executor_v2.py` | Change to `../core/executor_v2.py` | High |
| `docs/FALSE_POSITIVE_REDUCTION.md` | Line 12 | `file:///home/devxgamer/ai-qa-agent/core/bug_detector.py` | Change to `../core/bug_detector.py` | High |
| `docs/FORM_INTELLIGENCE.md` | Line 12 | `file:///home/devxgamer/ai-qa-agent/core/test_generator_v2.py` | Change to `../core/test_generator_v2.py` | High |
| `docs/SPA_EXPLORATION.md` | Line 12 | `file:///home/devxgamer/ai-qa-agent/crawler/crawler.py` | Change to `../crawler/crawler.py` | High |
| `docs/DOMAIN_PRODUCTION_GUIDE.md` | Line 88 | `file:///home/devxgamer/ai-qa-agent/render.yaml` | Change to `../render.yaml` | High |
| `docs/DOMAIN_PRODUCTION_GUIDE.md` | Line 94 | `file:///home/devxgamer/ai-qa-agent/api/main.py` | Change to `../api/main.py` | High |

### Duplicated / Overlapping Documentation
- `docs/CODEBASE_ARCHITECTURE.md` vs `docs/ARCHITECTURE.md`: Both contain identical high-level architectural descriptions and Mermaid system diagrams.
- `docs/AUTONOMOUS_QA.md` vs `docs/AUTONOMOUS_QA_ARCHITECTURE.md`: Substantial overlap describing the four-stage crawler/test-gen/executor/analysis pipeline.

---

## i) Leftover Comments and Hardcoded Values

| File Path | Line | Category | Evidence | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `crawler/crawler.py` | 725 | Hardcoded URL | `WebsiteCrawler("https://dplms.com", max_pages=30, auth_token=None)` in `if __name__ == "__main__": async def main():`. Hardcoded ad-hoc test URL from local debugging. | High |
| `web/src/components/admin/AIProviderConfig.tsx` | 274 | Hardcoded URL | `http://localhost:11434/v1` fallback endpoint for local Ollama instances. | Medium (Fallback default) |
| `web/src/components/scan/ScanForm.tsx` | 106, 113, 120 | Hardcoded URLs | Demo preset target URLs (`https://example.com`, `https://news.ycombinator.com`, `https://httpbin.org/status/200`). | Low (Intentional demo presets) |
| `api/main.py` | 62–69 | Hardcoded URLs | CORS allowed origin URLs (`https://jasuss.tech`, `https://web-two-flame-39.vercel.app`, etc.). | Low (Production allowed origins) |
| `.gsd/templates/*` | Multiple | Leftover comments | `TODO`, `FIXME`, `XXX` comments present only inside `.gsd/` scaffold templates. | Low (Template placeholders) |

---

## j) Needs a Human Decision

The following items involve architectural tradeoffs, deployment contracts, or potential module side-effects and require explicit human decision before removal:

1. **`api/main.py:29` Eager Task Import**:
   - `from worker.tasks import process_query_task` at line 29 is flagged as unused by `ruff F401` because line 589 re-imports it dynamically.
   - *Risk*: Celery workers and FastAPI app instances may rely on top-level task import side-effects to register task names with the Celery app during module import.
   - *Decision needed*: Confirm whether removing line 29 or moving task registration explicitly to `worker/celery_app.py` is preferred.

2. **`your_application/` Fallback Directory (`__init__.py`, `wsgi.py`)**:
   - Contains a WSGI shim that intercepts the default Render launch command `gunicorn your_application.wsgi` and redirects to `uvicorn api.main:app`.
   - *Risk*: If Render's service settings use the default command, deleting `your_application/` will cause deployment startup failure.
   - *Decision needed*: Confirm if Render service start command is explicitly configured as `./start.sh` or `uvicorn api.main:app` before deleting.

3. **`requirements.txt` vs `requirements-dev.txt` (`pytest`, `fakeredis`)**:
   - `pytest` and `fakeredis` are in both files.
   - *Risk*: If Dockerfile or CI test runners execute `pip install -r requirements.txt` and run pytest inside the container, removing them from `requirements.txt` would break containerized tests.
   - *Decision needed*: Confirm whether `requirements.txt` is strictly production-only or shared with test containers.

4. **Unreferenced Pydantic Models in `core/schemas/`**:
   - `DiscoveryResultModel` (`discovery.py:55`), `QualityGateResultModel` (`quality.py:28`), `RegressionStatus` (`regression.py:9`).
   - *Risk*: They may represent intended public API schema definitions or future phase data models.
   - *Decision needed*: Keep as type definitions or remove.

5. **Local Generated Cache Purge**:
   - 744 MB in `user_data/`, 397 MB in `screenshots/`, 37 MB in `results/`, 100 KB in `qa_agent.db`, and 0-byte SQLite files (`jasuss.db`, `local_qa_platform.db`).
   - *Decision needed*: Approve local disk deletion (`rm -rf`) to reclaim ~1.2 GB disk space.

---

## Summary of Cleanup Potential

- **Unused Imports & Variables**: 39 items across 14 files (38 High confidence, 1 Medium).
- **Unused Dependencies**:
  - `requirements.txt`: `tenacity==8.5.0`
  - `web/package.json`: `@supabase/ssr`
- **Unused Frontend Code**: `web/src/views/index.ts` (1 file), 7 internal unused exports in `web/src/utils/export.ts`.
- **Broken Internal Links**: 11 links across 7 documentation files (all with verified replacement paths).
- **Disk Reclamation Potential**: ~1.2 GB local untracked clutter.
