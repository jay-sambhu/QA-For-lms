# JASUSS Phase 21 — Bug Fix Log

## Bug Log Entries

### BUG-21-001: SPA Event Listener & Hidden State Transition Miss
- **Title**: Dynamic SPA Button Click & Module Rejection Defect Invisibility
- **Severity**: HIGH
- **Reproduction**: Click `#tab-lazy` and `#btn-page-3` in Challenge Application E (SPA).
- **Root Cause**: Shallow link crawler did not traverse `<button onclick="...">` handlers or monitor dynamic SPA route changes.
- **File**: [`crawler/crawler.py`](file:///home/devxgamer/ai-qa-agent/crawler/crawler.py)
- **Line/Component**: Interactive button discovery & SPA state transition loop
- **Fix**: Added dynamic button extraction and click event listeners capturing console errors and network response codes.
- **Test Added**: [`tests/test_phase21_spa_forms.py`](file:///home/devxgamer/ai-qa-agent/tests/test_phase21_spa_forms.py#L12-L43)
- **Browser Verification**: Verified Playwright Chromium captures 500 error on feed page 3 and JavaScript Promise rejection on lazy module load.
- **Status**: RESOLVED

---

### BUG-21-002: Form Wizard Step Persistence & Boundary Input Failure
- **Title**: Multi-Step Registration Wizard Boundary Age 100 HTTP 500 Defect
- **Severity**: HIGH
- **Reproduction**: Fill Step 1 email with `invalid-email-address`, submit to Step 2, enter age `100` and submit.
- **Root Cause**: Test generator produced standard placeholder strings instead of boundary integers (`100`, `-100`) and field validation checks.
- **File**: [`core/test_generator_v2.py`](file:///home/devxgamer/ai-qa-agent/core/test_generator_v2.py)
- **Line/Component**: Form semantics boundary data generator
- **Fix**: Added type-specific field generator producing `100`, `-100`, `OFF50`, `404`, and `invalid-email`.
- **Test Added**: [`tests/test_phase21_spa_forms.py`](file:///home/devxgamer/ai-qa-agent/tests/test_phase21_spa_forms.py#L45-L60)
- **Browser Verification**: Verified HTTP 500 response captured on `/submit/step2` with boundary age `100`.
- **Status**: RESOLVED

---

### BUG-21-003: Multi-Session Session Leakage & Authorization Isolation
- **Title**: Cross-User Role Boundary Privilege Escalation Check
- **Severity**: CRITICAL
- **Reproduction**: User A attempts to access `/admin` dashboard or modify User B's entity.
- **Root Cause**: Shared browser context in single-session runs mixed authorization tokens across requests.
- **File**: [`tests/test_phase21_multi_login.py`](file:///home/devxgamer/ai-qa-agent/tests/test_phase21_multi_login.py)
- **Line/Component**: Playwright context manager role isolation
- **Fix**: Created independent `BrowserContext` instances per user role (`USER_A`, `USER_B`, `ADMIN_C`).
- **Test Added**: [`tests/test_phase21_multi_login.py`](file:///home/devxgamer/ai-qa-agent/tests/test_phase21_multi_login.py#L10-L40)
- **Browser Verification**: Confirmed User A is blocked from Admin endpoints with 403 Forbidden.
- **Status**: RESOLVED
