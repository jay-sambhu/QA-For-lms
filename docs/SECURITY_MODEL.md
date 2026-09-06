# JASUSS — Security Model & Data Redaction

## Security Guarantees
1. **SSRF Protection**: `ScanRequest` validation blocks private IPs (10.0.0.0/8, 127.0.0.0/8, 192.168.0.0/16, loopbacks) and cloud IMDS endpoints (`169.254.169.254`, `metadata.google.internal`).
2. **Credential Redaction**: `security/redactor.py` redacts passwords, tokens, API keys, and authorization headers from logs, reports, AI prompts, and screenshots.
3. **Safe Security Testing**: Performs only non-destructive security checks (XSS payload sanitization checks, auth boundary verification). No destructive exploits.
