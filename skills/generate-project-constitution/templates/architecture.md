# Template: architecture.md

## Required Sections

- **System overview** — 1 paragraph, plain language, no jargon
- **Component/service map** — ASCII diagram or table of services and their responsibilities
- **Data ownership model** — which service owns which data; no service accesses another's store directly
- **Inter-service communication pattern** — REST, events, gRPC, etc. One canonical choice with exceptions noted
- **External integration points** — third-party systems, APIs, or services this system depends on
- **Integration Layer Definition** — one sentence describing what "wiring a feature together" means in this project (e.g. assembling screens into navigation, connecting pipeline stages, composing modules into the application entry point). This definition is used by `/feature-to-issues` to scope INT issues and by Ralph-impl to validate feature completion before signalling the test phase.
- **Key architectural constraints and non-negotiables** — decisions that must not be revisited without constitution amendment
