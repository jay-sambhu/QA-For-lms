# JASUSS — Autonomous Agent Architecture

## Modular Agent System (`core/agent/agent_orchestrator.py`)

JASUSS coordinates specialized sub-agents across the quality engineering lifecycle:

1. **Discovery Agent**: Inspects DOM topology, dynamic routes, hidden modals, and network traffic.
2. **Planning Agent**: Computes risk scores and creates risk-weighted test strategies.
3. **Test Generation Agent**: Generates observable, multi-category test cases.
4. **Execution Agent**: Drives Playwright browser execution with self-healing locator strategies.
5. **Oracle Agent**: Verifies multi-source assertions (DOM, HTTP status, console logs, visual diffs).
6. **Defect Verification Agent**: Reproduces defects and computes SHA256 fingerprints.
7. **Triage Agent**: Classifies severity and root cause hypotheses.
8. **Regression Agent**: Compares outcomes against historical baseline runs.
9. **Reporting Agent**: Formats executive markdown, JSON, PDF, and Excel reports.
10. **Learning Agent**: Extracts failure patterns and updates future test prioritization weights.

## Safety & Security Layer
- **Prompt Injection Defense**: All target web page content, DOM attributes, and HTTP headers are treated as untrusted input and sanitized via `AgentOrchestrator.sanitize_untrusted_web_input()` before processing.
- **Strict Control Boundaries**: AI outputs pass schema validation (`Pydantic v2`) before affecting execution or state persistence.
