# Template: ralph-agent-spec.md

## Purpose
Defines the agentic coding loop used in this project. Each Ralph agent type has a fixed responsibility boundary, a defined input contract, and a clear completion signal. The dependency graph in `ai-context/issues.json` is the handover mechanism — no explicit handoff messages needed.

## Required Sections

### Agent Types

Define the Ralph agent types in use on this project:

| Agent Type | Issue Layers | Responsibility | Completion Signal |
|------------|-------------|---------------|-------------------|
| Ralph-impl | DB, API, UI, INT | Implement the issue; write unit tests (UT-) in same PR | PR merged + issue closed |
| Ralph-test | TEST | Write integration tests (IT-) covering the feature's acceptance criteria; run against test environment | All IT- IDs pass; TEST issue closed |
| Ralph-e2e | E2E | Write Playwright (or equivalent) E2E tests (E2E-) for critical user flows; run against staging | All E2E- IDs pass; E2E issue closed |

### Parallelization Model (Ralph-impl only)

Ralph-impl reads the Bounded Contexts / Domain Map in `ai-context/architecture.md` to decide how to run,
using two nested tiers of parallelism:

- **Tier 1 — across domains:** if 2+ domains have eligible work, Ralph-impl acts as an orchestrator. Each
  wave, it spawns one domain-worker sub-agent per eligible domain (up to the domain concurrency cap
  below), each in its own `git worktree`, so independent bounded contexts are implemented concurrently
  without file conflicts.
- **Tier 2 — within a domain:** a domain worker groups its own issues into layer-ordered stages (DB → API
  → UI → INT). Two or more issues in the same stage were, by construction, all confirmed independent by
  the eligibility scan (co-eligible issues cannot block each other), so the domain worker spawns one
  nested issue-worker sub-agent per issue in the stage (up to the issue concurrency cap below), each in
  its own sibling `git worktree`. A stage with exactly one issue runs directly, no nested spawn. Stages
  still run in fixed layer order — only issues within the *same* stage run concurrently with each other.
- **Single domain declared, or only one domain has eligible work, and that domain's current stage has only
  one issue:** fully sequential — no worktrees, no sub-agents. This is the same behaviour as before
  domain-based parallelism existed.

Occasional PR merge conflicts between sibling issues in the same stage (e.g. two issues both touching a
shared router/schema file) are an accepted, already-handled cost of this model — the losing PR rebases and
retries — not a sign the model is unsafe. See `agents/ralph-impl.md` — FAILURE HANDLING.

| Setting | Value |
|---------|-------|
| Max parallel domain agents | [e.g. 4 — cap on concurrent domain workers per wave; tune to the team's CI/infra capacity, not just core count] |
| Max parallel issue workers per stage | [e.g. 3 — cap on concurrent issue workers *within one domain's current stage*; total worst-case concurrency this wave ≈ (active domains) × (this cap), so size both settings together against real CI/infra capacity, not independently] |
| Worktree path convention | [e.g. domain worker: `../[repo-name]-wt-[domain-lowercase]`; issue worker: `../[repo-name]-wt-[domain-lowercase]-[issue-suffix-lowercase]`, sibling to its parent domain worker's worktree — both cleaned up by their owner after use] |
| Cross-domain / cross-issue merge coordination | Workers at both tiers never hold a local checkout of the base branch — they branch each issue's feature branch directly off `origin/[base branch]` and merge via the PMS/platform API (server-side, safe to run concurrently). Feature-completion checks (INT verification, TEST-unblock signalling) run once centrally in the orchestrator after each wave, never inside a domain or issue worker, to avoid racing to post the same signal. |

### Promotion Model (only if a tiered branch strategy is used — see `ai-context/repo-structure.md`)

Defines how code moves from the shared integration branch into `main`, once Ralph-impl, Ralph-test, and
Ralph-e2e have merged their PRs into the integration branch. This is a **separate step from every Ralph
agent's Output Contract below** — none of Ralph-impl, Ralph-test, or Ralph-e2e ever merge to `main`
directly; their PR target is always the integration branch (see Agent Configuration table below).

| Setting | Value |
|---------|-------|
| Integration branch | [e.g. `dev`] |
| Promotion trigger | [e.g. "Once every issue in a wave is merged to `dev` and Ralph-e2e's E2E issues for that wave are closed" — see Q25b] |
| Promotion owner | [e.g. "Opened as a PR from `dev` to `main` by [a human / a scheduled CI job], reviewed the same as any other PR per `ai-context/repo-structure.md`"] |
| Promotion CI gate | [e.g. "Unit + integration + regression + E2E smoke — see `ai-context/testing.md` Main Promotion Gate"] |
| Promotion failure handling | [e.g. "If the promotion PR's E2E smoke suite fails, promotion is blocked; the regressing commit is identified via `git bisect` (or equivalent) against the wave's merged PRs. The wave is not complete until promotion to `main` succeeds — a merged-to-integration-branch wave with a failed promotion is not 'done'."] |

If this project does **not** use a tiered branch strategy, delete this section — every agent's PR target
is `main` directly and there is no separate promotion step.

### Handover Model

The handover between agent types is **implicit via the dependency graph** in `ai-context/issues.json`. No explicit handoff message is required.

- Ralph-impl closes all DB/API/UI/INT issues → TEST issues become unblocked → Ralph-test picks them up
- Ralph-test closes TEST issues → E2E issues become unblocked → Ralph-e2e picks them up

The platform's issue state (open/closed) is the single source of truth for handover readiness.

### Input Contract

For each agent type, define what it must read before starting work:

**Ralph-impl inputs:**
- The assigned issue (from PMS — GitHub Issues, Jira, Linear, etc.)
- `ai-context/project-constitution.md` — immutable principles
- `ai-context/architecture.md` — service boundaries, no cross-service data access
- `ai-context/coding-standards.md` — language conventions, naming, review checklist
- `ai-context/testing.md` — unit test framework, file conventions, coverage threshold
- `ai-context/repo-structure.md` — branch/PR conventions, PR target (see Promotion Model above if tiered)
- `ai-context/database-guidelines.md` — naming, ID strategy, migration tooling (for DB issues)
- The feature file `docs/features/F-XX-slug.md` — acceptance criteria and entity ownership

**Ralph-test inputs:**
- The assigned TEST issue
- `ai-context/testing.md` — integration test framework, test environment config
- `docs/test-plan.md` — IT- test IDs mapped to this feature's ACs and user stories
- `docs/features/F-XX-slug.md` — acceptance criteria to validate
- Access to the [test environment] — [docker-compose / shared dev / ephemeral]

**Ralph-e2e inputs:**
- The assigned E2E issue
- `ai-context/testing.md` — E2E tool config (Playwright project, base URL, etc.)
- `docs/test-plan.md` — E2E- smoke test IDs for this feature's critical paths
- Access to staging environment at [staging URL]

### Output Contract

What each agent type must produce:

**Ralph-impl:**
- A merged PR containing: implementation code + unit tests (UT-)
- All UT- IDs from `docs/test-plan.md` for this issue covered and passing
- Coverage threshold met (see `ai-context/testing.md`)
- Issue closed in PMS

**Ralph-test:**
- Integration test files at [location per testing.md]
- All IT- IDs from `docs/test-plan.md` for this feature covered and passing against [test environment]
- TEST issue closed in PMS

**Ralph-e2e:**
- E2E test files at [location per testing.md]
- All E2E- IDs from `docs/test-plan.md` for this feature passing against staging
- E2E issue closed in PMS

### Agent Configuration

| Setting | Ralph-impl | Ralph-test | Ralph-e2e |
|---------|-----------|-----------|---------|
| Model | [e.g. claude-sonnet-4-5] | [e.g. claude-sonnet-4-5] | [e.g. claude-sonnet-4-5] |
| Tools allowed | Read, Write, Edit, Bash, Git | Read, Write, Edit, Bash, Git | Read, Write, Edit, Bash, Git, Browser |
| Max turns per issue | [e.g. 50] | [e.g. 30] | [e.g. 40] |
| Branch strategy | `feat/[ISSUE-ID]-[slug]` | `test/[ISSUE-ID]-[slug]` | `e2e/[ISSUE-ID]-[slug]` |
| PR target | [`main`, or the integration branch name if tiered — e.g. `dev`] | [same] | [same] |

If this project uses a tiered branch strategy, all three agents' PR target is the integration branch,
**never** `main` directly — promotion from the integration branch to `main` is a separate step owned
outside any single agent's PR; see Promotion Model above.

### Failure Handling

- If Ralph-impl cannot complete an issue within the max turn limit: open a blocking comment on the issue, label it `needs-human`, halt.
- If Ralph-test cannot reach the test environment: report the connection error in the issue, label `env-issue`, halt.
- If Ralph-e2e finds a failing E2E- test that was previously passing: open a bug issue with reproduction steps, block the E2E issue from closing.
- All agents: never force-push, never merge without CI passing, never skip a failing test.
- Ralph-impl (and any human editing CI config): never wire an E2E/Playwright/Cypress job into the CI
  pipeline's `on: push` / `on: pull_request` triggers for PRs into the integration branch (or `main`, on a
  single-base-branch project). E2E runs only via a separate, manually-triggered workflow
  (`workflow_dispatch` or platform equivalent) by default — see `ai-context/testing.md` — E2E Test Trigger
  Model. **Exception:** on a project with a tiered branch strategy whose Promotion CI gate (above)
  requires E2E smoke, the one promotion PR per wave (integration branch → `main`) may trigger E2E via
  `on: pull_request` scoped to `base: main` — this is the specific gate the project chose, not a drift
  back to per-PR E2E. Ralph-e2e itself is always invoked manually, never spawned by CI, in either case.

## Example Structure

```markdown
# Ralph Agent Specification — [Project Name]

## Agent Types
| Agent | Layers | Tool |
|-------|--------|------|
| Ralph-impl | DB, API, UI, INT | claude-sonnet-4-5 |
| Ralph-test | TEST | claude-sonnet-4-5 |
| Ralph-e2e | E2E | claude-sonnet-4-5 |

## Parallelization Model
Ralph-impl: two-tier orchestrator/worker split. Tier 1 by domain (from architecture.md Domain Map, max 4 parallel domain agents, one git worktree each at ../repo-name-wt-[domain]). Tier 2 by layer-stage within a domain (max 3 parallel issue workers per stage, sibling worktrees). Feature-completion checks run centrally in the orchestrator, never in a domain or issue worker.

## Handover
Implicit via issues.json dependency graph. TEST issues unblock when all implementation siblings are closed. E2E issues unblock when TEST siblings are closed.

## Input Contract
Ralph-impl reads: assigned issue + project-constitution + architecture + coding-standards + testing + database-guidelines + F-XX feature file.
Ralph-test reads: assigned TEST issue + testing.md + test-plan.md + F-XX feature file.
Ralph-e2e reads: assigned E2E issue + testing.md + test-plan.md.

## Output Contract
Ralph-impl: merged PR with implementation + UT- tests passing.
Ralph-test: IT- tests passing against docker-compose.
Ralph-e2e: E2E- Playwright tests passing against staging.

## Branch Convention
feat/[ISSUE-ID]-[slug] → test/[ISSUE-ID]-[slug] → e2e/[ISSUE-ID]-[slug]

## Failure Handling
Max turns exceeded → label `needs-human`, halt.
Test environment unreachable → label `env-issue`, halt.
New E2E regression → open bug issue, block closure.
```
