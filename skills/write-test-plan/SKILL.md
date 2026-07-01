---
name: write-test-plan
description: >
  Use this skill when the user types /write-test-plan or wants a requirements-driven,
  implementation-independent test plan before development begins (TDD approach).
  Produces unit test specs, integration test plan, smoke test suite, and regression test plan —
  all derived from FRs, ACs, and User Stories, never from code or implementation details.
  Trigger on: "/write-test-plan", "write test plan", "generate test cases", "create test specs",
  "TDD test plan", "write test specifications", "unit test plan", "integration test plan",
  "smoke test plan", "regression test plan", "generate tests from requirements",
  "test cases from acceptance criteria", "define tests before coding",
  or any request to define test cases based on functionality rather than implementation.
  Step 3.5 of the Greenfield workflow: /prd-to-features → HITL Feature Review
  → [/write-test-plan] → HITL Test Plan Review → /feature-to-issues → Ready to Develop.
---

# /write-test-plan — Requirements-Driven Test Plan Generator

## Workflow Role

`/write-test-plan` is **Step 3.5 of the Greenfield workflow** — inserted after HITL Feature Review and before `/feature-to-issues`.

```
GREENFIELD:
  /grill → /write-prd → /generate-project-constitution → /prd-to-features
    → HITL Feature Review → [/write-test-plan] → HITL Test Plan Review
    → /feature-to-issues → HITL Issue Review → Ready to Develop
```

**Input:** Approved PRD (FRs, ACs, Playwright scenarios) + Approved Feature Breakdown (User Stories, Acceptance/Behavioral Expectations) + `/ai-context/testing.md` (strategy, tooling, coverage thresholds).

**Output:** A structured test plan saved to `/ai-context/test-plan.md`, covering four test types — unit, integration, smoke, and regression.

**Why here:** Test cases must exist before development begins. Placing this step after feature review (so the full requirement picture is clear) but before issue creation (so issues can reference test IDs) ensures engineers and AI agents know exactly what to verify before a feature is considered done.

---

## Core Principle: Tests Derive from Requirements, Not Code

Every test case in this plan is derived exclusively from:
- Functional Requirements (FR-n) in the PRD
- Acceptance Criteria (AC-n) in the PRD
- User Stories and their Acceptance/Behavioral Expectations in the Feature Breakdown
- Playwright scenarios (PT-n) in the PRD

**A test case must never reference:**
- Class names, function names, method signatures, or module paths
- Database table names, column names, or ORM models
- API endpoint paths, HTTP verbs, or request/response schemas
- Framework internals, component names, or implementation patterns

If a test case cannot be written without knowing the implementation, it is being written at the wrong layer. Rewrite it from the requirement's perspective.

This discipline is what makes tests durable — they survive refactors, tech migrations, and architectural changes because they verify behavior, not mechanics.

---

## Test Plan Structure

The plan produces four sections. Not all sections apply to every project — determine applicability based on the PRD and constitution.

| Section | Always? | Applicability |
|---------|---------|--------------|
| Unit Test Specifications | Yes | Always — every project with functional logic has unit-testable behaviors |
| Integration Test Plan | If applicable | Multi-service, external integrations, or complex data flows |
| Smoke Test Suite | Yes | Any system that is deployed — confirms it's alive after release |
| Regression Test Plan | Yes | Always — the cumulative set of behaviors that must never break |

---

## Execution Protocol

### Step 0 — Load Source Artifacts

Before writing any test cases, load and silently parse:

1. The approved **PRD** — extract all FR-n, AC-n, and PT-n entries
2. The approved **Feature Breakdown** — extract all User Stories (US-XX.N) with their Acceptance Expectations and Behavioral Expectations
3. `/ai-context/testing.md` — extract: test tooling per layer, coverage thresholds, CI gate, test data strategy
4. `/ai-context/architecture.md` — extract: service boundaries, integration points, external dependencies

If any source artifact is missing, note it and proceed with what's available. Do not block plan generation for a missing file — flag the gap and continue.

Build a silent working map:

```
FR-n → AC-n(s) → PT-n(s) → US-XX.N(s) → [planned test cases]
```

This traceability chain ensures no requirement is left untested.

---

### Step 1 — Determine Applicability

Before writing, assess:

- **Integration tests applicable?** Yes if: multiple services interact, external APIs are consumed, async messaging is used, or data crosses a service boundary.
- **Smoke tests applicable?** Yes for any deployed system. Scope = the 5–15 most critical user-visible behaviors.
- **Regression tests applicable?** Always yes — this is the full AC-derived test register.

State your applicability decisions at the top of the output before the test cases.

---

### Step 2 — Write Unit Test Specifications

Unit tests verify that **individual behaviors** work correctly in isolation. They test one thing at a time, with all external dependencies removed.

**Source:** FR-n entries from the PRD and Acceptance Expectations from User Stories.

**For each testable behavior, write a test specification in this format:**

```
UT-[n]: [Test Name — what behavior is being verified]
Requirement : FR-n / AC-n / US-XX.N
Category    : [Happy Path | Boundary | Negative | Error Handling]
Precondition: [The state that must be true before this test runs — no implementation detail]
Input       : [The stimulus or input that triggers the behavior]
Expected    : [The observable outcome — what the system does, not how]
Priority    : [P1 Critical | P2 High | P3 Medium | P4 Low]
```

**Category definitions:**
- **Happy Path** — valid input, expected conditions, system works as intended
- **Boundary** — input at the edge of valid ranges (min, max, exactly-at-limit)
- **Negative** — invalid input, missing required data, wrong type
- **Error Handling** — downstream failure, timeout, unavailable dependency

**Coverage rules:**
- Every Must Have FR must have at least 1 Happy Path and 1 Negative unit spec
- Every AC must map to at least one unit spec
- Boundary specs are required wherever the FR specifies a limit (size, count, length, date, amount)
- Error Handling specs are required for every external dependency interaction

**Example (correctly written — no implementation detail):**

```
UT-04: Export rejected when row count exceeds limit
Requirement : FR-4 / AC-3
Category    : Boundary — Negative
Precondition: A user account exists with more than 50,000 exportable rows
Input       : User initiates an account data export
Expected    : The system rejects the request and communicates that the export
              exceeds the maximum allowed size of 50,000 rows. No export job
              is created. No email is sent.
Priority    : P1 Critical
```

**Example (incorrectly written — do NOT do this):**

```
UT-04: Test ExportService.validateRowCount() throws ExportLimitException
```
That's testing implementation, not behavior.

---

### Step 3 — Write Integration Test Plan

Integration tests verify that **components work correctly together** — data flows across boundaries, contracts between services are honoured, and the system behaves correctly as a whole.

**Source:** Architecture.md (service boundaries, external integrations), FR-n entries that span multiple components, Behavioral Expectations from User Stories.

**Only include integration tests where a real boundary exists** — don't write integration tests for things that could and should be unit-tested.

**For each integration point, write a specification in this format:**

```
IT-[n]: [Test Name — what cross-boundary behavior is being verified]
Requirement   : FR-n / AC-n / US-XX.N
Boundary      : [Service A ↔ Service B, or System ↔ External Dependency]
Dependency    : [Real | Stubbed | Contract] — specify which dependencies are real vs. stubbed
Precondition  : [System state before the test — data, service availability, etc.]
Trigger       : [What initiates the cross-boundary interaction]
Expected Flow : [What should happen at each boundary — observable outcomes only]
Expected End  : [Final observable state confirming the integration succeeded]
Failure Mode  : [What happens if the dependency is unavailable or returns an error]
Priority      : [P1 Critical | P2 High | P3 Medium]
```

**Dependency classification:**
- **Real** — the actual dependency is used (database, external service). Use sparingly; only when a stub would not accurately represent the behavior.
- **Stubbed** — a controlled fake replaces the dependency. Use for external APIs, email services, payment gateways.
- **Contract** — a contract test verifies the boundary's interface without running the full dependency. Use for inter-service APIs.

---

### Step 4 — Write Smoke Test Suite

The smoke test suite is the minimum set of tests that confirm the system is functional after a deployment. It must run fast (target: under 5 minutes) and cover the critical path a real user would take.

**Source:** Highest-priority User Stories (P1 Critical features), core happy path Playwright scenarios (PT-n).

**Rules:**
- Maximum 15 tests in the smoke suite. If you have more, you've included too much — smoke tests are not regression tests.
- Each smoke test must be executable in a deployed environment (not just locally)
- Every smoke test must verify something a user would notice if broken
- Do not include tests that require complex test data setup — smoke tests must be runnable against a fresh deployment

**Format:**

```
ST-[n]: [Test Name — the critical behavior being verified]
Requirement   : FR-n / PT-n / US-XX.N
User Journey  : [The user-visible action being confirmed]
Precondition  : [Minimal state required — should be achievable on a fresh deployment]
Steps         : [Numbered observable steps — no code, no implementation]
Expected      : [What a passing deployment looks like for this test]
Blocking      : [Yes — deployment must not proceed if this fails | No]
```

Mark all P1 smoke tests as `Blocking: Yes`. A failed blocking smoke test means the deployment must be rolled back.

---

### Step 5 — Write Regression Test Plan

The regression test plan is the **complete, cumulative catalog of behaviors** the system must continue to exhibit as new features are added. It is derived directly from all ACs across all features — if an AC exists, there must be a corresponding regression test.

The regression plan does not add new tests — it organises the full set of unit and integration tests into a structure that makes it clear what must be re-verified after any change.

**Format:**

Organise by Feature (F-XX from the Feature Breakdown):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE F-XX: [Feature Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RT-[n]: [Behavior that must not regress]
Traces To : AC-n / FR-n / UT-n or IT-n
Trigger   : [What to do to verify this behavior still works]
Expected  : [The observable outcome that confirms no regression]
Risk      : [High — change in this area is likely to break this |
             Medium — tangential changes may affect this |
             Low — isolated behavior, unlikely to be affected by other changes]
```

After listing all regression tests, produce a **regression impact map** — a table showing which features are most likely to be affected by changes in each other:

```
Impact Map: If you change... these features need regression testing:
F-01 (Auth)       → F-02, F-03, F-04, F-05 (all features that require auth)
F-03 (Export)     → F-05 (notification), F-02 (audit log)
```

This tells engineers which regression tests to run when they touch a given area, without running the entire suite every time.

---

### Step 6 — Output the Test Plan

Save the complete test plan to `/ai-context/test-plan.md`.

### Save Test Plan

Before outputting the summary, save the test plan to the project folder:

1. Write to `docs/test-plan.md` (human-readable, version-controlled with project docs)
2. Write an identical copy to `ai-context/test-plan.md` (so `/feature-to-issues` can read it at its expected path)

If no project folder is connected, call `mcp__cowork__request_cowork_directory` first.

Output a summary after saving:

```
✅ Test Plan Generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Saved to: docs/test-plan.md  |  ai-context/test-plan.md

Coverage Summary:
  Unit Test Specs     : [N] (covering [N] FRs, [N] ACs)
  Integration Tests   : [N] (covering [N] service boundaries)
  Smoke Tests         : [N] ([N] blocking)
  Regression Tests    : [N] (spanning [N] features)

Traceability:
  FRs covered         : [N/total]
  ACs covered         : [N/total]
  User Stories covered: [N/total]
  Uncovered FRs       : [list any FR-n with no test case — these are gaps]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HITL CHECKPOINT — Test Plan Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use the `AskUserQuestion` tool to interactively collect confirmation before proceeding. Present a **multi-select** question so the user confirms all items in a single interaction.

**Call `AskUserQuestion` with:**
- question: "Please confirm the Test Plan review items that are complete. Select all that apply:"
- multiSelect: true
- options:
  1. Every Must Have FR has at least one unit test spec
  2. Every AC maps to at least one test (unit or integration)
  3. Smoke suite covers the critical deployment path
  4. No test case references implementation details
  5. Regression impact map accurately reflects feature dependencies
  6. Integration tests correctly identify real vs. stubbed dependencies

**If all 6 items are selected:** State "✅ Test Plan Approved." Then instruct the user to run `/feature-to-issues`.

**If any items are NOT selected:** List each unconfirmed item, state "⛔ Test Plan requires revision — do not proceed until all items are confirmed.", and halt.
        ☐ Requires Revision — do not proceed until gaps are addressed

Next step: /feature-to-issues
(When running /feature-to-issues, reference test IDs from this plan
 so that each issue includes the specific test cases it must satisfy.)
```

---

## Test ID Convention

| Prefix | Type | Format |
|--------|------|--------|
| `UT-` | Unit test specification | `UT-01`, `UT-02`… |
| `IT-` | Integration test | `IT-01`, `IT-02`… |
| `ST-` | Smoke test | `ST-01`, `ST-02`… |
| `RT-` | Regression test | `RT-01`, `RT-02`… |

IDs are sequential and globally unique within this test plan. Downstream artifacts (`/feature-to-issues`, PR descriptions, code comments) must reference these IDs verbatim to maintain traceability.

---

## Traceability Model

```
PRD
 └── FR-n ──────────────────────────────── UT-n (unit specs)
      └── AC-n ──────────────────────────── RT-n (regression)
           └── PT-n ──────────────────── ST-n (smoke, if critical path)

Feature Breakdown
 └── F-XX
      └── US-XX.N ──────────────────────── UT-n / IT-n
           ├── Acceptance Expectations ─── RT-n
           └── Behavioral Expectations ─── IT-n (cross-boundary behaviors)
```

Every test ID must trace back to at least one FR, AC, or User Story. A test with no traceability is a test for implementation, not requirements — remove it.

---

## Quality Guardrails

### NEVER write a test that:
- Names a class, function, method, endpoint path, or module
- Is only meaningful if you know how the code is structured
- Duplicates another test case (same precondition, trigger, and expected — consolidate)
- Has a vague expected outcome ("system behaves correctly", "no errors occur")
- Cannot be independently understood by someone who hasn't read the code

### ALWAYS:
- Trace every test to FR-n, AC-n, or US-XX.N
- Write expected outcomes in observable, user-visible or system-visible terms
- Flag any FR or AC with no corresponding test as a coverage gap
- Mark P1 smoke tests as blocking
- Keep the smoke suite under 15 tests — if it grows beyond that, move excess tests to regression

---

## Example: Same Requirement, Right vs. Wrong Test Case

**Requirement (AC-1):** When an authenticated user clicks Export My Data, the system shall return a confirmation within 500ms and display "Your export is being prepared."

**Wrong (implementation-aware):**
```
Test ExportController.initiateExport() returns 202 with confirmationMessage field set
```

**Right (behavior-driven):**
```
UT-01: Authenticated user receives immediate confirmation when export is initiated
Requirement : FR-1 / AC-1
Category    : Happy Path
Precondition: A user is authenticated and has at least 1 row of exportable data
Input       : User initiates an account data export
Expected    : The user receives confirmation within 500ms that their export is being
              prepared. The confirmation message reads "Your export is being prepared.
              You'll receive an email when it's ready." No export data is returned
              immediately.
Priority    : P1 Critical
```

The right version survives a complete rewrite of the export service. The wrong version breaks the moment someone renames the controller.
