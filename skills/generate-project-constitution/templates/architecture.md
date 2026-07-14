# Template: architecture.md

## Required Sections

- **System overview** — 1 paragraph, plain language, no jargon
- **Component/service map** — ASCII diagram or table of services and their responsibilities
- **Data ownership model** — which service owns which data; no service accesses another's store directly
- **Bounded Contexts / Domain Map** — this project is decomposed as a set of DDD bounded contexts, each
  identified by a short domain code (the same code used as the `DOMAIN` prefix in issue IDs, e.g. `AUTH`,
  `BILLING`). For each domain, record:
  | Domain Code | Bounded Context Name | Owned Entities / Tables | Owned Module / Directory Path(s) | Cross-Domain Access |
  |---|---|---|---|---|
  | e.g. `AUTH` | Authentication & Identity | users, sessions, refresh_tokens | `src/domains/auth/**` | Other domains call `auth`'s public API only — never its DB directly |

  Rules that must hold for every domain listed:
  - A domain owns its entities/tables exclusively — no other domain reads or writes them directly (this
    is the same non-negotiable as the Data ownership model above, applied at sub-service granularity when
    the system is a single service/monolith rather than separate deployable services).
  - Cross-domain interaction happens only through the domain's declared public interface (a service
    method, an API endpoint, or an event) — never through shared tables, shared mutable state, or reaching
    into another domain's internal modules/files.
  - **This map is the parallel-safety boundary for the Ralph implementation loop, at two nested levels.**
    Two issues whose IDs carry different domain codes are assumed to touch disjoint files/tables and are
    safe to implement concurrently by separate domain sub-agents. Two issues that share a domain code but
    are both independently eligible at the same time (neither blocks the other) are *also* implemented
    concurrently, by nested issue-level sub-agents within that domain's worker — layer-ordered (DB before
    API before UI before INT) so the natural build sequence is preserved even without an explicit
    dependency edge between them. See `ai-context/ralph-agent-spec.md` — Parallelization Model.
  - If the project is a true monolith with no meaningful domain separation, state that explicitly here
    (e.g. "Single domain — CORE. No cross-domain boundaries; Ralph-impl runs fully sequential.") rather
    than inventing artificial domains.
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
