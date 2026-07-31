# The Human Residue: 3-Call Mini-Interview

`extract_facts.py` and the Step 3 generation agents can produce every constitution file except for one
irreducible category: governance/social facts no static analysis can recover. `/generate-project-constitution`
asks these as free-standing interview questions (Q27 Immutable Principles, Q28-29 Decision Authority)
because it has no code to condition on yet. `/discover-constitution` has code — so it asks fewer, narrower
questions, grounded in what was just drafted, and runs this step **after** Step 3 (file drafting) and
**before** Step 5 (`project-constitution.md` synthesis) so the user sees what got auto-filled before being
asked to weigh in on governance.

## Call 1 — Immutable Principles

`AskUserQuestion`, `multiSelect: true`, ≤4 options per call (batch into 2 calls if more than 4 candidates
apply). Options are **generated dynamically from `constitution-facts.json`**, not static text — only offer a
candidate when its backing signal is actually present:

| Candidate option | Offer only if |
|---|---|
| "Maintain current test coverage floor (~`{test.coverage_pct}`%)" | `test.coverage_pct` confidence is `measured` |
| "No new dependency-version drift beyond what's already flagged" | `deps.duplicate_framework_versions` is non-empty |
| "No direct cross-zone database/module access" | `zones.json` has at least one entry |
| "Keep god-object hubs from growing further" | `architecture.risk_areas` has at least one `god_node` entry |

Always include a final option: **"Other — I'll describe additional or different principles"** (free-text
follow-up). If fewer than 3 conditional candidates apply, ask the remaining slots as plain free text instead
of padding the menu with irrelevant options — a 2-option `AskUserQuestion` call plus one free-text question
is fine.

## Call 2 — Decision Authority

**Free text, not `AskUserQuestion`** — same choice `/generate-project-constitution` makes for its own
Q28-29; forcing "who decides architectural changes" into a 4-option menu is worse UX, not better. One
brownfield-specific addition: `detect_codeowners()`'s output grounds the question when a `CODEOWNERS` file
was found —

> "We found a CODEOWNERS file listing `{codeowners.owners_sample}` — does decision authority for this
> project follow this file, or is it different?"

When no `CODEOWNERS` file is found, ask the same open question `/generate-project-constitution` does,
unprompted by any detected file.

## Call 3 — Residual Gaps

`AskUserQuestion`, `multiSelect: true`, ≤4 options (batch if more than 4). Explicitly names which files
`file_recommendations` or the per-file generation agents flagged as low-confidence — `security.md` is
**always** in this list (see `fact-mapping.md`'s "always low-confidence" section), since `/assess-repo`
collects no auth/authz signal at all. Options are the flagged file names; selecting one means "ask me a
couple of targeted questions about this now," leaving one unselected means "leave its
`[DECISION PENDING]` markers for a later amendment pass."

## Where answers land

All three calls' answers feed `project-constitution.md`'s **Immutable Principles** and **Decision Authority**
sections in Step 5 (parent context, generated last — same ordering rule `/generate-project-constitution`
uses). Each principle is tagged with its provenance:

- `(derived from measured baseline)` — came from a Call 1 dynamic candidate grounded in a real metric.
- `(team-declared)` — came from free text (the "Other" option, or any Call 3 follow-up answer).

This distinction is unique to the reverse-engineered case and is worth keeping: a principle grounded in a
measured baseline can be re-verified by a future `/discover-constitution` run; a team-declared one can't.
