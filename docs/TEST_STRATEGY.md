# JASUSS — Test Strategy & Multi-Category Testing Matrix

## Test Categories
- **Functional**: Happy path, negative cases, boundary conditions, edge cases.
- **Authentication & Authorization**: Login, session expiry, role isolation, privilege escalation checks.
- **Form Validation**: Special character handling, XSS injection indicator rejection, empty submit handling.
- **Navigation & Routing**: Route availability, dynamic parameter extraction (`/users/:id`), broken links.
- **API Testing**: HTTP status codes, schema contract compliance, latency thresholds.
- **Reliability & Performance**: Interrupted request tolerance, slow endpoint identification.
- **Accessibility**: Image alt attribute audits, semantic HTML role verification.
