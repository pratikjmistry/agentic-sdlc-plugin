# Template: testing.md

## Purpose
Defines the testing strategy, tooling, coverage requirements, and agent responsibilities for the Ralph coding loop. Every statement must name the actual tool and threshold — no generic advice.

## Required Sections

### Testing Stack
- **Unit test framework:** [tool + version — e.g. Vitest 1.x, pytest 8.x, Jest 29.x]
- **Integration test framework:** [tool — often same as unit; note if different]
- **E2E / browser automation:** [Playwright / Cypress / none — one canonical choice]
- **Code coverage tool:** [tool — e.g. Istanbul/c8, coverage.py, coverlet]
- **Minimum coverage threshold:** [e.g. 80% line coverage — blocks merge / advisory only]

### Testing Pyramid & Targets

| Layer | Tool | Coverage Target | CI Gate |
|-------|------|----------------|---------|
| Unit | [tool] | [threshold]% | Blocks merge |
| Integration | [tool] | Key paths covered | Blocks merge |
| E2E / Smoke | [Playwright/Cypress] | Critical user flows | **Not in the PR/merge pipeline at all — separate manually-triggered workflow. See E2E Test Trigger Model below.** |
| Regression | [tool] | All prior ACs | Blocks merge |

### What Must Be Tested

**Always test:**
- Every business rule and branch condition (unit)
- Every API endpoint happy path + primary error cases (integration)
- Every user-facing critical path flow (E2E)
- Every acceptance criterion from the feature spec (integration/E2E)

**Acceptable to skip:**
- Trivial getters/setters with no logic
- Third-party library internals
- UI rendering details (prefer behaviour tests over snapshot tests)

### Test Environment Strategy

- **Unit tests:** run in-process, no external dependencies — [local / CI identical]
- **Integration tests:** [local docker-compose / ephemeral per-PR / shared dev env]
- **E2E tests:** run against [staging / ephemeral deploy / local full stack]
- **Test data strategy:** [fixtures / seeding / factories / mocking approach]
- **External service mocking:** [tools: MSW / WireMock / VCR / none — actual services used]

### CI Gate

**If this project uses a single base branch** (trunk-based, Gitflow, or environment-branches strategy —
see `ai-context/repo-structure.md`), use one gate list for every PR / push to the default branch:
- [ ] Unit tests — [threshold]% coverage
- [ ] Integration tests — all mapped IT- IDs pass
- [ ] Linting and type-check
- [ ] Regression suite — no RT- regressions
- [ ] Traceability check — see "What the Traceability Check Verifies" below

**E2E tests (E2E-) are explicitly NOT a CI Gate item on a single-base-branch project and must never run on
`push` or `pull_request`.** See E2E Test Trigger Model immediately below.

**If this project uses a tiered branch strategy** (a shared integration branch promoted to `main` — see
`ai-context/repo-structure.md`), replace the single list above with one gate list per tier. Every PR into
the integration branch and the promotion PR from the integration branch into `main` are different events
with potentially different required checks — state both explicitly, don't assume they're the same:

**Integration branch gate** (every PR into `[integration branch name]`):
- [ ] Unit tests — [threshold]% coverage
- [ ] Integration tests — all mapped IT- IDs pass
- [ ] Linting and type-check
- [ ] Regression suite — no RT- regressions
- [ ] Traceability check — see "What the Traceability Check Verifies" below

**Main promotion gate** (the one PR per wave from `[integration branch name]` into `main`):
- [ ] Everything in the integration branch gate, plus:
- [ ] E2E / smoke tests — all applicable E2E- IDs pass against [environment]
- [ ] Any additional pre-release checks: [e.g. changelog updated, version bumped]

This is a deliberate, project-specific exception to the "E2E never blocks a merge" default in E2E Test
Trigger Model below — here E2E blocks exactly one PR per wave (the promotion PR), not every feature PR.

#### What the Traceability Check Verifies

An automated script/CI job parses every UT-/IT-/E2E- ID out of the test plan, confirms each has a matching
implemented test (per the Test ID traceability convention below), and fails the build on any unmatched ID.
This is a required deliverable, not optional — a test-plan ID with a correctly written spec but no
implemented test is exactly the kind of gap that ships silently without this check. See "Traceability
Check" below for what the script must do. (The traceability check itself still runs on every PR — including
every PR into the integration branch, on a tiered project — and still verifies E2E- IDs have matching
*test files*; it does not execute those E2E tests. See E2E Test Trigger Model below for why.)

### E2E Test Trigger Model

E2E/Playwright/Cypress tests are **not** part of the standard PR/merge CI pipeline. They run in a
**separate workflow with a manual trigger only** (e.g. GitHub Actions `workflow_dispatch`, or the
equivalent manual-run mechanism in [CI platform]):

- **Why:** E2E suites are slower and inherently flakier than unit/integration tests, and they validate
  behavior on a *deployed* environment (staging), which is a post-merge concern, not a pre-merge gate.
  Gating every PR on E2E turns a normal merge into a bottleneck and trains engineers to ignore flaky-red
  CI. Unit + integration + lint + traceability are enough to safely merge; E2E validates the result once
  deployed.
- **Trigger:** run manually by a human, or by `claude --agent agentic-sdlc:ralph-e2e` once a feature's
  TEST issues close (see `ai-context/ralph-agent-spec.md` — Handover Model). Typical cadence is once per
  feature-wave completion (a "wave-boundary" trigger) rather than on every commit.
- **What this means for the CI config Ralph-impl writes:** the E2E job/workflow file must have
  `workflow_dispatch` (or platform equivalent) as its *only* trigger — never `on: push` or
  `on: pull_request`, for PRs into the integration branch (or `main`, on a single-base-branch project). If
  a project's CI config runs E2E automatically on every feature PR, that is a constitution violation to be
  fixed, not a feature.
- **Tiered-branch exception:** on a project with a tiered branch strategy whose Main Promotion Gate above
  requires E2E smoke, the promotion PR (integration branch → `main`) *may* have `on: pull_request` scoped
  to `base: main` trigger the E2E job — that is still not "every PR," only the one promotion PR per wave,
  and it is the specific gate this project chose in Q25c, not a silent drift back to per-PR E2E. Ralph-e2e
  itself is still always invoked manually in both cases, never spawned automatically by CI.

### Ralph Agent Testing Responsibilities

This section defines which Ralph agent type writes each category of tests. See `ai-context/ralph-agent-spec.md` for full agent definitions.

| Test Type | Written By | When | What "Done" Means |
|-----------|-----------|------|-------------------|
| Unit (UT-) | Ralph-impl | During implementation, same PR | All UT- IDs from test plan pass; coverage threshold met |
| Integration (IT-) | Ralph-test | After all implementation issues in the feature are merged | All IT- IDs from test plan pass against [test environment] |
| E2E / Smoke (E2E-) | Ralph-e2e | After feature deployed to staging | All E2E- IDs in test plan pass in [Playwright/Cypress] against staging |
| Regression (RT-) | CI (automated) | On every PR | No RT- regressions introduced |

### Test File Conventions

- **Unit test location:** [e.g. co-located `*.test.ts` / separate `tests/unit/` directory]
- **Integration test location:** [e.g. `tests/integration/`]
- **E2E test location:** [e.g. `tests/e2e/` — Playwright test files]
- **Test naming convention:** [e.g. `describe('[module]') > it('[should do X when Y]')`]
- **Test ID traceability:** each test file includes a comment mapping it to UT-/IT-/E2E- IDs from the test plan

### Traceability Check (required CI Gate item, not just a naming convention)

A written test-plan ID with no matching implemented, passing test is a defect that ships silently — the
only reliable way to catch that drift is a machine check, not a reviewer remembering to look. This
project must generate a traceability-check script or CI job that:

1. Parses every `UT-`/`IT-`/`E2E-` ID out of `docs/test-plan.md` (or `ai-context/test-plan.md`).
2. Scans the test suite for a matching ID comment per the Test ID traceability convention above.
3. Fails the build (or produces a clearly flagged report, if advisory-only for this project) when any
   test-plan ID has no matching implemented test, or when a test file references an ID that doesn't
   exist in the test plan (stale reference).

This is a required deliverable of the first `/write-test-plan` → `/feature-to-issues` cycle, generated
alongside the test plan — not an after-the-fact audit built once drift is already suspected.

## Example Structure

```markdown
# Testing — [Project Name]

## Testing Stack
- Unit: Vitest 1.x
- Integration: Vitest 1.x (supertest for HTTP layer)
- E2E: Playwright 1.x
- Coverage: Istanbul (c8) — 80% line coverage blocks merge

## Testing Pyramid
| Layer | Tool | Target | CI Gate |
|-------|------|--------|---------|
| Unit | Vitest | 80% line coverage | Blocks merge |
| Integration | Vitest + Supertest | All API endpoints covered | Blocks merge |
| E2E | Playwright | Critical paths: login, checkout, dashboard | Not in PR/merge pipeline — manual `workflow_dispatch` only |
| Regression | Vitest | All prior ACs | Blocks merge |

## What Must Be Tested
- All service-layer business rules (unit)
- All REST endpoints: happy path + 401/403/404/422 cases (integration)
- Login flow, primary user journey, admin panel access (E2E)

## Test Environment
- Unit: in-process, no I/O
- Integration: docker-compose (postgres + redis)
- E2E: Playwright against staging deploy

## CI Gate
Merge blocked by: unit (80% coverage) + integration + lint/typecheck + traceability check

## E2E Test Trigger Model
E2E is a separate GitHub Actions workflow (`e2e.yml`) triggered only by `workflow_dispatch` — never
`push` or `pull_request`. Run manually, or via `claude --agent agentic-sdlc:ralph-e2e` once a feature's
TEST issues close. Typical cadence: once per feature-wave, against the staging deploy.

## Ralph Agent Responsibilities
- Ralph-impl: writes UT- tests in same PR as implementation
- Ralph-test: writes IT- tests after feature wave is implemented; runs against docker-compose
- Ralph-e2e: writes E2E- Playwright tests after staging deploy; validates critical paths
```
