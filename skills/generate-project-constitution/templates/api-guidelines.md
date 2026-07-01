# Template: api-guidelines.md

## Required Sections

- **API style** — REST, GraphQL, gRPC, or tRPC — one canonical choice; document exceptions
- **URL and naming conventions** — resource naming, casing, nesting depth limits
- **Versioning strategy** — URL versioning, header versioning, or semantic; deprecation timeline
- **Standard error response format** — include a concrete JSON example
- **Authentication** — required for all endpoints by default; document public exceptions explicitly
- **Rate limiting policy** — limits per tier/client, response headers used, retry guidance
- **Deprecation process** — how breaking changes are announced and when old versions are sunset
