# Template: repo-structure.md

## Required Sections

- **Top-level directory layout** — annotated tree showing purpose of each top-level folder
- **Domain-aligned module layout** — the directory layout must mirror the Bounded Contexts / Domain Map in
  `ai-context/architecture.md`: one top-level module per domain code (e.g. `src/domains/auth/`,
  `src/domains/billing/`), each internally organised by layer (e.g. `data/`, `api/`, `ui/`) rather than one
  global `controllers/`, `models/`, `views/` split across domains. This is what makes a domain a safe,
  self-contained unit of concurrent work for the Ralph implementation loop — a sub-agent assigned to one
  domain never needs to touch files outside its domain's directory.
- **Service/module naming convention** — how services, packages, and modules are named
- **Dependency rules** — what can import what (e.g., "UI cannot import directly from DB layer"). Must also
  state the cross-domain rule: a domain module may only be imported via its public entry point (e.g. its
  `index.ts` / `__init__.py` / package root) — never by reaching into another domain's internal files. Note
  any shared/core domain that is exempt (e.g. a `shared` or `core` module all domains may import from).
- **Shared library strategy** — where shared code lives; how it's versioned and consumed
- **Generated code location** — where generated files (types, clients, migrations) live; whether they're committed
- **Branch naming and PR conventions** — format for branch names, PR title format, required labels
