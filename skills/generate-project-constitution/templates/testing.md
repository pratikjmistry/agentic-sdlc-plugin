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
| E2E / Smoke | [Playwright/Cypress] | Critical user flows | Advisory (speed) |
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

Which test types block merge:
- [ ] Unit tests — [threshold]% coverage
- [ ] Integration tests — all mapped IT- IDs pass
- [ ] Linting and type-check
- [ ] E2E tests — [advisory or blocking]
- [ ] Regression suite — no RT- regressions
- [ ] **Traceability check** — an automated script/CI job parses every UT-/IT-/ST- ID out of the test
      plan, confirms each has a matching implemented test (per the Test ID traceability convention
      below), and fails the build on any unmatched ID. This is a required deliverable, not optional —
      a test-plan ID with a correctly written spec but no implemented test is exactly the kind of gap
      that ships silently without this check. See "Traceability Check" below for what the script must do.

### Ralph Agent Testing Responsibilities

This section defines which Ralph agent type writes each category of tests. See `ai-context/ralph-agent-spec.md` for full agent definitions.

| Test Type | Written By | When | What "Done" Means |
|-----------|-----------|------|-------------------|
| Unit (UT-) | Ralph-impl | During implementation, same PR | All UT- IDs from test plan pass; coverage threshold met |
| Integration (IT-) | Ralph-test | After all implementation issues in the feature are merged | All IT- IDs from test plan pass against [test environment] |
| E2E / Smoke (ST-) | Ralph-e2e | After feature deployed to staging | All ST- IDs in test plan pass in [Playwright/Cypress] against staging |
| Regression (RT-) | CI (automated) | On every PR | No RT- regressions introduced |

### Test File Conventions

- **Unit test location:** [e.g. co-located `*.test.ts` / separate `tests/unit/` directory]
- **Integration test location:** [e.g. `tests/integration/`]
- **E2E test location:** [e.g. `tests/e2e/` — Playwright test files]
- **Test naming convention:** [e.g. `describe('[module]') > it('[should do X when Y]')`]
- **Test ID traceability:** each test file includes a comment mapping it to UT-/IT-/ST- IDs from the test plan

### Traceability Check (required CI Gate item, not just a naming convention)

A written test-plan ID with no matching implemented, passing test is a defect that ships silently — the
only reliable way to catch that drift is a machine check, not a reviewer remembering to look. This
project must generate a traceability-check script or CI job that:

1. Parses every `UT-`/`IT-`/`ST-` ID out of `docs/test-plan.md` (or `ai-context/test-plan.md`).
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
| E2E | Playwright | Critical paths: login, checkout, dashboard | Advisory |
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
Merge blocked by: unit (80% coverage) + integration + lint/typecheck
E2E: runs post-merge on staging (advisory)

## Ralph Agent Responsibilities
- Ralph-impl: writes UT- tests in same PR as implementation
- Ralph-test: writes IT- tests after feature wave is implemented; runs against docker-compose
- Ralph-e2e: writes ST- Playwright tests after staging deploy; validates critical paths
```
