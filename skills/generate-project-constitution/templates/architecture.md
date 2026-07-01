# Template: architecture.md

## Required Sections

- **System overview** — 1 paragraph, plain language, no jargon
- **Component/service map** — ASCII diagram or table of services and their responsibilities
- **Data ownership model** — which service owns which data; no service accesses another's store directly
- **Inter-service communication pattern** — REST, events, gRPC, etc. One canonical choice with exceptions noted
- **External integration points** — third-party systems, APIs, or services this system depends on
- **Key architectural constraints and non-negotiables** — decisions that must not be revisited without constitution amendment
