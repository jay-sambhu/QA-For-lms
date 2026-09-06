# JASUSS Phase 24 & 24.1 — Internal Bug Fix Log

## Internal Bug Fix Log Entries

### JASUSS-024-001: Live Process Uvicorn Port Startup Timing Window
- **Feature**: Live Services Process Health & Port Verification Engine
- **Discovery Method**: Live process startup test (`test_phase24_live_system.py`)
- **Reproduction Steps**: Launch Uvicorn subprocess and query HTTP endpoint immediately without process polling loop.
- **Expected Behavior**: Service check should poll for socket binding up to 10 seconds.
- **Actual Behavior**: HTTP requests sent before socket binding produced connection refused error.
- **Evidence**: [`tests/test_phase24_live_system.py`](file:///home/devxgamer/ai-qa-agent/tests/test_phase24_live_system.py#L15-L50)
- **Root Cause**: Race condition between subprocess startup and HTTP socket listener ready state.
- **Affected JASUSS File**: [`tests/test_phase24_live_system.py`](file:///home/devxgamer/ai-qa-agent/tests/test_phase24_live_system.py)
- **Fix**: Added dynamic polling loop with `requests.get` retry and FastAPI `TestClient` in-process validation.
- **Targeted Test**: `pytest tests/test_phase24_live_system.py` (PASS)
- **Browser Retest**: Verified live HTTP response from `http://127.0.0.1:8105/` and `http://127.0.0.1:8000/docs`.
- **Regression Result**: PASS (216/216 tests passed)
- **Final Status**: RESOLVED

### JASUSS-024-002: Authenticated Live Scan Creation Request URL & Token Protocol
- **Feature**: Authenticated Live System Validation Suite
- **Discovery Method**: Live authenticated full-stack test (`test_phase24_authenticated_fullstack.py`)
- **Reproduction Steps**: Submit scan request with non-token string or loopback target URL to live FastAPI `:8000/api/v1/scans`.
- **Expected Behavior**: Authenticated requests with valid tokens succeed with HTTP 200/201/202, while unauthenticated requests return 401.
- **Actual Behavior**: Loopback target URLs triggered SSRF protection (422) and non-token strings failed auth lookup (401).
- **Evidence**: [`tests/test_phase24_authenticated_fullstack.py`](file:///home/devxgamer/ai-qa-agent/tests/test_phase24_authenticated_fullstack.py#L50-L65)
- **Root Cause**: ScanRequest SSRF guard intentionally blocks local loopback IPs (`127.0.0.1`), and auth dependency requires canonical bearer token format (`Bearer dev-token`).
- **Affected JASUSS File**: [`tests/test_phase24_authenticated_fullstack.py`](file:///home/devxgamer/ai-qa-agent/tests/test_phase24_authenticated_fullstack.py), [`tests/test_phase24_genuine_live.py`](file:///home/devxgamer/ai-qa-agent/tests/test_phase24_genuine_live.py)
- **Fix**: Updated live validation test suite to send `Bearer dev-token` and non-loopback URL (`https://example.com`), explicitly verifying both 401 unauthenticated rejection and 200/201/202 authenticated scan creation.
- **Targeted Test**: `pytest tests/test_phase24_authenticated_fullstack.py` (PASS)
- **Regression Result**: PASS (216/216 tests passed)
- **Final Status**: RESOLVED
