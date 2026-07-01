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
