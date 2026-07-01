# Template: security.md

## Required Sections

- **Authentication model** — session, JWT, OAuth 2.0, mTLS, API keys — one canonical choice
- **Authorisation approach** — RBAC, ABAC, ownership-based, or none
- **Data classification** — categories (PII, PHI, PCI, sensitive, internal, public) and which entities fall under each
- **Secrets management** — where secrets live, how they're injected at runtime, what is forbidden (e.g., no secrets in source)
- **Input validation and output encoding standards** — library/framework used, where validation occurs
- **Audit logging requirements** — which events must be logged, retention period, storage location
- **Compliance obligations** — mapped to specific controls (e.g., GDPR Article 17 → deletion endpoint + retention job)
