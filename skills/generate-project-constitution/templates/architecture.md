# Template: architecture.md

## Required Sections

- **System overview** — 1 paragraph, plain language, no jargon
- **Component/service map** — ASCII diagram or table of services and their responsibilities
- **Data ownership model** — which service owns which data; no service accesses another's store directly
- **Inter-service communication pattern** — REST, events, gRPC, etc. One canonical choice with exceptions noted
- **Third-party integration contracts** — for every external system, API, or service this system depends
  on: the verified base URL(s) (including any split between hosts, e.g. a trading API vs. a market-data
  API on separate hosts), the auth/tier constraints (what a free/sandbox/paper tier does and does not
  permit), and the confirmed request/response shape for the specific endpoints and parameters actually
  used. Every entry must be sourced from checked documentation or a spike, not assumed from the vendor's
  general product description — record the source (doc URL, spike date) alongside each entry. If a
  contract has not yet been verified, mark it `[DECISION PENDING — contract unverified]` rather than
  guessing at its behavior.
- **Integration Layer Definition** — one sentence describing what "wiring a feature together" means in this project (e.g. assembling screens into navigation, connecting pipeline stages, composing modules into the application entry point). This definition is used by `/feature-to-issues` to scope INT issues and by Ralph-impl to validate feature completion before signalling the test phase.
- **Key architectural constraints and non-negotiables** — decisions that must not be revisited without constitution amendment
