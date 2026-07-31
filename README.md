# Agentic SDLC Plugin for Claude Code

End-to-end SDLC workflow for Claude Code — from raw idea to implemented, tested, and shipped code.

Covers the full lifecycle: **grill → PRD → project constitution → features → test plan → UI design → issues → PMS → Ralph implementation loop**.

---

## Installation

### 1. Add the marketplace

```bash
claude plugin marketplace add pratikjmistry/agentic-sdlc-plugin
```

### 2. Install the plugin

```bash
claude plugin install agentic-sdlc@agentic-sdlc-plugin
```

### 3. Reload plugins

```bash
/reload-plugins
```

### 4. (Optional) Connect PMS tools

The `/push-to-pms` skill requires a PMS connector MCP (GitHub Issues, Azure DevOps, Jira, Linear, or GitLab). Install the relevant connector from the Claude Code official marketplace:

```bash
# Examples
claude plugin install github@claude-plugins-official
claude plugin install atlassian@claude-plugins-official
claude plugin install linear@claude-plugins-official
```

---

## Workflows

### Greenfield (new project)

```
/agentic-sdlc:grill                          → Interrogate and clarify the idea
/agentic-sdlc:write-prd                      → Generate structured PRD
/agentic-sdlc:generate-project-constitution  → Interview + generate ai-context/ files
/agentic-sdlc:prd-to-features               → Decompose PRD into Features + User Stories
  ↓ HITL Feature Review
/agentic-sdlc:write-test-plan               → Generate TDD test plan (UT-, IT-, ST-, RT-)
  ↓ HITL Test Plan Review
/agentic-sdlc:design-ui                     → Elicit design preferences, generate UI mockups
  ↓ HITL UI Design Review
/agentic-sdlc:feature-to-issues             → Decompose features into atomic issues
  ↓ HITL Issue Review
/agentic-sdlc:push-to-pms                   → Push issues to GitHub / Jira / Linear / ADO / GitLab
  ↓ Issues in PMS
```

### Brownfield (existing project, adding a feature)

```
/agentic-sdlc:grill                          → Interrogate the feature request
/agentic-sdlc:write-feature                  → Document the feature (no PRD needed)
  ↓ HITL Feature Review
/agentic-sdlc:feature-to-issues             → Decompose into issues
  ↓ HITL Issue Review
/agentic-sdlc:push-to-pms                   → Push to PMS
```

### Brownfield Onboarding (long-lived, undocumented repos)

For repos where code is the source of truth and there's no documentation to speak of — running the
Greenfield flow's spec-first constitution generator on one of these produces an aspirational document the
repo mostly contradicts. This pathway triages first:

```
/agentic-sdlc:assess-repo <git-url-or-path>  → Phase 0: score agent-readiness, verdict + trust level
  ↓ ONBOARD_NOW / ONBOARD_AFTER_REMEDIATION / DEFER / DO_NOT_ONBOARD
Phase 1  → autonomy floor (reproducible build + verifiable test signal)
/agentic-sdlc:map-codebase <git-url-or-path>  → Phase 2: real dependency graph via Graphify,
  ↓                                              module/hub/hidden-coupling synthesis, zone refresh
/agentic-sdlc:discover-constitution <path>   → Phase 2 (cont.): reverse-engineer ai-context/ from
  ↓                                              measured facts, flag legacy risk areas as seam candidates
/agentic-sdlc:generate-zone-context <path>   → Phase 2 (cont.): per-zone drill-down — modules, hubs,
  ↓                                              hidden coupling, cycles touching each candidate pilot zone
Phase 3  → /characterize — characterization test harness
Phase 4  → /baseline-debt — debt baseline + ratchet
Phase 5  → /plan-seams — seam creation, lazy, per-zone
Phase 6  → graduated autonomy per zone (trust levels L0–L4)
Phase 7  → /verify-context — context drift detection in CI
```

Phase 0 (`/assess-repo`) and all three of Phase 2's named skills — `/map-codebase`, `/discover-constitution`,
`/generate-zone-context` — are implemented today.
`/assess-repo` is a deterministic scoring pass (no model call computes a score), cheap enough to run across
a 20–40 repo portfolio, and it's the gate that decides whether the rest of this pathway is worth investing
in for a given repo at all — run `/map-codebase` (or anything past it) on a repo it flagged `DEFER`/
`DO_NOT_ONBOARD` and you're spending real time on a repo that likely isn't worth it. `/map-codebase` builds
the real dependency graph via [Graphify](https://pypi.org/project/graphifyy/) (`uv tool install
graphifyy`) — deterministic tree-sitter AST extraction, no LLM calls by default — and synthesizes it into
a human-readable `docs/codebase-map.md` (module/community boundaries, architectural hubs, hidden
cross-module coupling, circular dependencies, candidate entry points), plus refreshes `/assess-repo`'s
`zones.json` with real coupling data now that an actual graph exists. `/discover-constitution` then reads
both skills' output and drafts `ai-context/*.md` from measured facts instead of an interview — the same
file set `/generate-project-constitution` produces for a greenfield project, with anything static analysis
can't confidently determine marked `[DECISION PENDING]` rather than guessed, and god objects/cyclic
dependencies/high-blast-radius zones surfaced in `architecture.md` as seam candidates for the downstream
`/plan-seams` phase. `/generate-zone-context` then drills into each individual zone from `zones.json`,
writing one `ai-context/zones/<zone-id>-<slug>.md` per zone with the specific modules, architectural hubs,
hidden coupling, and cyclic-dependency groups that actually touch that zone — detail `architecture.md`
deliberately keeps flat across the whole repo. Phases 1, 3–7 are the planned next steps of this pathway,
not yet built.

### Ralph implementation loop (after issues are in PMS)

```
claude --agent agentic-sdlc:ralph-impl      → Implement next unblocked DB/API/UI/INT issue
claude --agent agentic-sdlc:ralph-test      → Write integration tests (after impl issues close)
claude --agent agentic-sdlc:ralph-e2e       → Write E2E tests against staging (after tests close)
```

---

## Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| Grill | `/agentic-sdlc:grill` | Interrogates vague ideas into clear, buildable requirements |
| Write PRD | `/agentic-sdlc:write-prd` | Produces an implementation-ready Product Requirements Document |
| Generate Project Constitution | `/agentic-sdlc:generate-project-constitution` | Interviews you and generates `ai-context/` architecture files |
| PRD to Features | `/agentic-sdlc:prd-to-features` | Decomposes PRD into Features with User Stories |
| Write Feature | `/agentic-sdlc:write-feature` | Brownfield path — documents a single feature without a full PRD |
| Write Test Plan | `/agentic-sdlc:write-test-plan` | Generates a TDD test plan from FRs and ACs |
| Design UI | `/agentic-sdlc:design-ui` | Elicits design preferences, generates layout options and HTML mockups |
| Feature to Issues | `/agentic-sdlc:feature-to-issues` | Decomposes features into atomic, dependency-ordered issues |
| Push to PMS | `/agentic-sdlc:push-to-pms` | Creates issues in your chosen project management platform |
| Assess Repo | `/agentic-sdlc:assess-repo` | Brownfield Phase 0 — deterministically scores a repo's agent-readiness (git/build/test/CI/deps/debt/structure), gives a verdict, trust level, and pilot zone |
| Map Codebase | `/agentic-sdlc:map-codebase` | Brownfield Phase 2 — builds a real dependency graph via Graphify, synthesizes modules/hubs/hidden coupling/cycles into `docs/codebase-map.md`, refreshes zone coupling data |
| Discover Constitution | `/agentic-sdlc:discover-constitution` | Brownfield Phase 2 — reverse-engineers `ai-context/` files from `/assess-repo` + `/map-codebase`'s measured facts instead of an interview, flags god objects/cyclic dependencies/wide-blast-radius zones as seam candidates for `/plan-seams` |
| Generate Zone Context | `/agentic-sdlc:generate-zone-context` | Brownfield Phase 2 — writes one `ai-context/zones/<zone-id>-<slug>.md` per candidate pilot zone, drilling into the specific modules/hubs/hidden coupling/cycles touching that zone, forward-referencing `/characterize` and `/plan-seams` |

---

## Ralph Agents

Ralph agents are autonomous coding agents that pick up issues from the PMS and implement them.

| Agent | Command | Picks up | Triggers when |
|-------|---------|----------|---------------|
| Ralph-impl | `claude --agent agentic-sdlc:ralph-impl` | DB, API, UI, INT issues | Any unblocked impl issue exists |
| Ralph-test | `claude --agent agentic-sdlc:ralph-test` | TEST issues | All sibling impl issues are closed |
| Ralph-e2e | `claude --agent agentic-sdlc:ralph-e2e` | E2E issues | All sibling TEST issues are closed — **always run manually, never wired into CI** |

Handover between agents is **implicit via the dependency graph** in `ai-context/issues.json` — no manual handoff needed.

Each agent:
- Reads `ai-context/` for project context before touching code
- Asks for confirmation before starting work
- Creates a branch, implements, writes tests, opens a PR
- Waits for CI before merging
- Labels issues `needs-human` or `env-issue` if it gets stuck

### Ralph-impl parallelization

If `/generate-project-constitution` declared multiple DDD bounded contexts (domains) in
`ai-context/architecture.md`'s Domain Map, Ralph-impl runs as an **orchestrator** with two nested tiers of
parallelism:
- **Across domains:** each wave it spawns one domain-worker sub-agent per domain that currently has
  eligible issues, each in its own `git worktree`, so independent domains implement concurrently instead
  of one issue at a time. Capped by `Max parallel domain agents` (default 4).
- **Within a domain:** a domain worker stages its own issues by layer (DB → API → UI → INT); two or more
  issues in the same stage are, by construction, mutually independent (both were eligible at once, so
  neither blocks the other), so the domain worker spawns one nested issue-worker sub-agent per issue in
  that stage, each in a sibling `git worktree`. Capped by `Max parallel issue workers per stage` (default
  3). Occasional merge conflicts between siblings are expected and handled (rebase and retry), not a sign
  of a bug.

Both settings live in `ai-context/ralph-agent-spec.md`. Projects with a single domain (or no Domain Map,
or only one eligible issue in the current stage) fall back to the original fully-sequential loop
automatically.

### E2E tests are never part of the CI pipeline

`ai-context/testing.md`'s CI Gate covers unit, integration, lint, and traceability only. E2E/Playwright/
Cypress tests run in a separate workflow with a manual (`workflow_dispatch` or platform equivalent)
trigger — never `on: push` or `on: pull_request`. Ralph-e2e is always invoked by a human or manually
run once a feature's TEST issues close, typically once per feature-wave against staging.

> **Prerequisite:** Run `/agentic-sdlc:generate-project-constitution` first. Ralph agents require `ai-context/project-constitution.md` and related files to exist.

---

## Output Files

All planning artifacts are saved to `ai-context/` in your project repository. Greenfield projects get these
from an interview (`/generate-project-constitution`); brownfield repos get the same file set
reverse-engineered from measured facts instead (`/discover-constitution`):

| File | Produced by |
|------|-------------|
| `project-constitution.md` | `/generate-project-constitution` or `/discover-constitution` |
| `architecture.md` | `/generate-project-constitution` or `/discover-constitution` |
| `tech-stack.md` | `/generate-project-constitution` or `/discover-constitution` |
| `coding-standards.md` | `/generate-project-constitution` or `/discover-constitution` |
| `testing.md` | `/generate-project-constitution` or `/discover-constitution` |
| `database-guidelines.md` | `/generate-project-constitution` or `/discover-constitution` |
| `security.md` | `/generate-project-constitution` or `/discover-constitution` |
| `ralph-agent-spec.md` | `/generate-project-constitution` or `/discover-constitution` |
| `issues.json` | `/feature-to-issues` |
| `pms-map.json` | `/push-to-pms` |

Feature specs are saved to `docs/features/`:

| File | Produced by |
|------|-------------|
| `feature-summary.md` | `/prd-to-features` |
| `F-XX-slug.md` | `/prd-to-features` |
| `test-plan.md` | `/write-test-plan` |
| `design/ui-design.md` | `/design-ui` |
| `design/mockups/*.html` | `/design-ui` |

`/assess-repo` writes outside both of those, to a separate output directory (default
`./.assessment/<repo>-<shortsha>/`), never into the analyzed repo itself: `assessment-inputs.json`,
`assessment-scores.json`, `zones.json`, `agent-readiness-report.md`, `remediation-plan.md`, and an
appended row in `portfolio.csv`. `/discover-constitution` writes its own intermediate
`constitution-facts.json`, and `/generate-zone-context` its own `zone-facts.json`, into that same directory
before drafting into the target repo.

`/generate-zone-context` writes `ai-context/zones/<zone-id>-<slug>.md` (one per zone) plus
`ai-context/zones/README.md`, alongside the `ai-context/*.md` files above — same `ai-context/` root, a
`zones/` subdirectory so per-zone drill-down files don't clutter the flat repo-wide file list.

`/map-codebase` writes into the analyzed repo itself (Graphify's own convention): `graphify-out/graph.json`,
`graphify-out/.graphify_analysis.json`, and `docs/codebase-map.md` — the human-readable synthesis
`/discover-constitution` reads directly when drafting `architecture.md`.

---

## HITL Checkpoints

Each major step ends with a Human-in-the-Loop review checkpoint. Do not proceed to the next step until you have explicitly confirmed the output.

---

## Updating the Plugin

To pull the latest version:

```bash
claude plugin marketplace update agentic-sdlc-plugin
/reload-plugins
```
