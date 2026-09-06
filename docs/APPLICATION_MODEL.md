# Persistent Application Intelligence Model

**Specification Version**: 1.0.0

## Overview
The Application Knowledge Model (`core/schemas/application_model.py`) represents the persistent graph of target web applications discovered by JASUSS.

## Structural Schema

```json
{
  "application_id": "app_qa_lms_001",
  "target_url": "https://example.com",
  "environments": ["production"],
  "technology_hints": ["Next.js", "React", "FastAPI", "PostgreSQL"],
  "discovered_at": "2026-09-06T10:00:00Z",
  "last_updated": "2026-09-06T11:00:00Z",
  "routes": {
    "/login": {
      "requires_auth": false,
      "roles": ["anonymous"],
      "api_dependencies": ["POST /api/v1/auth/login"]
    },
    "/dashboard": {
      "requires_auth": true,
      "roles": ["authenticated", "student"],
      "api_dependencies": ["GET /api/v1/scans"]
    }
  },
  "roles": ["anonymous", "authenticated", "student", "admin"],
  "workflows": [
    {
      "workflow_id": "wf_auth_login",
      "name": "User Authentication Flow",
      "description": "Navigate to login, enter email/password, submit, verify redirect to dashboard",
      "is_business_critical": true,
      "requires_role": "anonymous"
    }
  ],
  "business_critical_paths": ["/login", "/dashboard", "/checkout", "/billing"]
}
```
