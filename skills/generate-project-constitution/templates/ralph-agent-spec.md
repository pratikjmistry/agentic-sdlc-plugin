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

Ralph-impl reads the Bounded Contexts / Domain Map in `ai-context/architecture.md` to decide how to run:

- **Multiple domains declared, multiple domains eligible:** Ralph-impl acts as an orchestrator. Each wave,
  it spawns one domain-worker sub-agent per eligible domain (up to the concurrency cap below), each in its
  own `git worktree`, so independent bounded contexts are implemented concurrently without file conflicts.
  Issues within the same domain are still processed sequentially by that domain's one worker.
- **Single domain declared, or only one domain has eligible work:** fully sequential — no worktrees, no
  sub-agents. This is the same behaviour as before domain-based parallelism existed.

| Setting | Value |
|---------|-------|
| Max parallel domain agents | [e.g. 4 — cap on concurrent domain workers per wave; tune to the team's CI/infra capacity, not just core count] |
| Worktree path convention | [e.g. `../[repo-name]-wt-[domain-lowercase]`, cleaned up by the worker after each wave] |
| Cross-domain merge coordination | Domain workers never hold a local checkout of the base branch — they branch each issue's feature branch directly off `origin/[base branch]` and merge via the PMS/platform API (server-side, safe to run concurrently). Feature-completion checks (INT verification, TEST-unblock signalling) run once centrally in the orchestrator after each wave, never inside a worker, to avoid two domains racing to post the same signal. |

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
| PR target | `main` / `develop` | `main` / `develop` | `main` / `develop` |

### Failure Handling

- If Ralph-impl cannot complete an issue within the max turn limit: open a blocking comment on the issue, label it `needs-human`, halt.
- If Ralph-test cannot reach the test environment: report the connection error in the issue, label `env-issue`, halt.
- If Ralph-e2e finds a failing E2E- test that was previously passing: open a bug issue with reproduction steps, block the E2E issue from closing.
- All agents: never force-push, never merge without CI passing, never skip a failing test.
- Ralph-impl (and any human editing CI config): never wire an E2E/Playwright/Cypress job into the CI
  pipeline's `on: push` / `on: pull_request` triggers. E2E runs only via a separate, manually-triggered
  workflow (`workflow_dispatch` or platform equivalent) — see `ai-context/testing.md` — E2E Test Trigger
  Model. Ralph-e2e itself is always invoked manually, never spawned by CI.

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
Ralph-impl: orchestrator/worker split by domain (from architecture.md Domain Map). Max 4 parallel domain agents, one git worktree each at ../repo-name-wt-[domain]. Feature-completion checks run centrally in the orchestrator, never in a worker.

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
