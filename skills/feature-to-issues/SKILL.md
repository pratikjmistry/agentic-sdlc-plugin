---
name: feature-to-issues
description: "Use this skill when the user types /feature-to-issues followed by an approved Feature document or Feature Breakdown. Decomposes Features into atomic, platform-agnostic Epics, User Stories, and Tasks/Issues grouped by layer (Backend, Frontend, Database, Integration) with a full dependency graph and execution order. Saves a machine-readable issue manifest to /ai-context/issues.json for downstream platform creation via /push-to-pms. Trigger on: /feature-to-issues, break features into issues, decompose features into tasks, generate issue breakdown from features, turn features into tickets, create issue manifest from feature breakdown. Requires confirmed HITL Feature Review before running."
---

# /feature-to-issues — Feature Decomposer and Issue Planner

## Workflow Role

`/feature-to-issues` is the **final planning step** before platform-specific issue creation.

It converts an approved Feature Breakdown into a structured, platform-agnostic issue manifest — Epics, child issues grouped by layer, dependencies, and execution order. The output is saved to `/ai-context/issues.json` and consumed by `/push-to-pms` to create items in the chosen project management platform.

**Prerequisite:** HITL Feature Review must be confirmed before this skill runs.

**Output feeds into:** `/push-to-pms` → platform issue creation → Ready to Develop

```
GREENFIELD:
  /grill → /write-prd → /generate-project-constitution → /prd-to-features
    → HITL Feature Review → /write-test-plan → HITL Test Plan Review
    → [/feature-to-issues] → HITL Issue Review → /push-to-pms → Ready to Develop
```

---

## Input Format

```
/feature-to-issues
```

**Accepted input sources:**

| Source | Format Signals | Path |
|--------|---------------|------|
| `/prd-to-features` output | Contains `F-XX` Feature IDs, `US-XX.N` User Story IDs, Dependency Map | Greenfield |
| `/write-feature` output | Contains `FEAT-XXX` Feature ID, `US-XXX.N` User Story IDs, HITL confirmed | Brownfield |

**Minimum acceptable Feature input:**
- At least one Feature with valid ID (`F-XX` or `FEAT-XXX` format)
- At least one User Story with valid ID (`US-XX.N` or `US-XXX.N` format)
- Acceptance Expectations present on each User Story
- HITL Feature Review confirmed

---

## Issue ID Convention

**Child Issue Format:** `[DOMAIN]-[LAYER]-[NNN]`

| Segment | Rule | Examples |
|---------|------|---------|
| DOMAIN | 2-6 char uppercase abbreviation of the feature | `AUTH`, `INSTR`, `SYNC`, `BKTEST` |
| LAYER | Fixed values: `DB`, `API`, `UI`, `INT` | `DB`, `API`, `UI`, `INT` |
| NNN | Zero-padded 3-digit sequence within layer, starting at 001 | `001`, `002`, `015` |

**Epic Format:** `[DOMAIN]-EPIC`

One Epic per Feature group. Exactly one per Feature — no sequence number.

```
AUTH-EPIC
  -- AUTH-DB-001    (users table migration)
  -- AUTH-API-001   (login endpoint)
  -- AUTH-API-002   (JWT refresh endpoint)
  -- AUTH-UI-001    (login page component)
  -- AUTH-TEST-001  (integration tests: login + refresh + session validation)
  -- AUTH-E2E-001   (Playwright: login flow, session persistence, logout)
```

**Rules:**
- Assign all Epic IDs first, then child issue IDs, before building the dependency map
- Dependencies are always between child issues only — never reference Epic IDs in dependency arrays
- Every child issue carries a `parent_epic_id` field pointing to its Feature's Epic

---

## Execution Instructions

### Step 1 — Load Context Files

Load before any output:
1. `ai-context/agents.md`
2. `ai-context/architecture.md`
3. `ai-context/coding-standards.md`
4. `ai-context/testing.md`
5. `ai-context/test-plan.md` — extract all UT-, IT-, ST-, RT- test IDs keyed to each FR-n, AC-n, and US-XX.N
6. `ai-context/database-guidelines.md` — load naming conventions, ID strategy, migration tooling, auditing approach, soft-delete strategy, and ORM guidance. Apply these to all DB-layer issues.
7. **Entity Ownership Map** — read the `## Entity Ownership` table from `docs/features/feature-summary.md`. Build an in-memory map of which feature owns which entities. Use this to generate correct schema/migration tasks per feature and to avoid duplicate entity definitions across features.

Note missing files and proceed. If `test-plan.md` is absent, omit the Test Requirements section from issue templates and note the gap in the HITL checkpoint. If `database-guidelines.md` is absent, note the gap and use reasonable defaults for DB naming. If the Entity Ownership table is absent, infer ownership from User Story descriptions and flag ambiguities in the HITL checkpoint.

### Step 2 — Validate Feature Input

Detect input source and validate minimum completeness. Block with a structured error if 2 or more required items are missing.

### Step 3 — Parse and Decompose

**Greenfield (from `/prd-to-features`):**

| Element | Maps To |
|---------|---------|
| Feature ID (F-XX) | Epic group + domain prefix |
| User Story | Issue scope and description |
| Acceptance Expectations | Issue acceptance criteria |
| Feature Dependencies | Cross-feature issue dependencies |

**Brownfield (from `/write-feature`):**

| Element | Maps To |
|---------|---------|
| Feature ID (FEAT-XXX) | Epic group + domain prefix |
| User Story | Issue scope and description |
| Acceptance Expectations | Issue acceptance criteria |
| Existing Modules Impacted | Issues tagged with impacted service/module |

### Step 4 — Assign Epic IDs then Child Issue IDs

Assign Epic IDs first (one per Feature group), then child IDs by layer:

| Layer | ID Segment | Category | Scope | Ralph Agent |
|-------|-----------|----------|-------|-------------|
| Database | `DB` | `database` | Table definitions (fields, types, constraints), migration file specs, indexes, seed data if applicable | Ralph-impl |
| Backend/API | `API` | `backend` | Service logic, endpoints, business rules | Ralph-impl |
| Frontend/UI | `UI` | `frontend` | Components, pages, state | Ralph-impl |
| Integration | `INT` | `integration` | End-to-end feature integration — wires all DB/API/UI pieces into a cohesive, working whole and verifies the feature works end-to-end as described in the feature doc. The project-specific definition of what "integration" means (e.g. assembling screens into navigation, connecting pipeline stages, wiring services via a gateway, composing modules into the application entry point) is captured in `ai-context/architecture.md` under **Integration Layer Definition** | Ralph-impl |
| Integration Testing | `TEST` | `test` | Write IT- integration tests, validate acceptance criteria against running environment, API contract tests | Ralph-test |
| End-to-End | `E2E` | `e2e` | Write ST- Playwright/Cypress flows for critical user paths, smoke test suite | Ralph-e2e |

Assign in this order: DB → API → UI → INT → TEST → E2E. This reflects execution dependency direction.

**TEST issues** depend on all DB/API/UI/INT issues within the same feature — they cannot run until the feature is fully implemented.
**E2E issues** depend on all TEST issues for the feature — they validate the complete user-facing behaviour after integration tests pass.
**Only generate TEST and E2E issues if the project has a testing strategy defined in `ai-context/testing.md`.** If testing.md is absent, flag the gap in the HITL checkpoint.

### Step 5 — Infer Dependencies

Build the full dependency map using the Dependency Detection Logic section. Dependencies are between child issues only — never reference Epic IDs in dependency arrays.

### Step 6 — Apply the Atomicity Test

For every child issue verify:
- Completable by one engineer in one sprint
- Single, clear Definition of Done
- Executable without unfinished issues except listed dependencies
- Contains enough context for execution without clarification

### Step 7 — Assign Execution Order

| Condition | Execution Order |
|-----------|----------------|
| Epic issues | always 0 |
| No dependencies (root issues) | 1 |
| Depends only on order-1 issues | 2 |
| Depends on any order-2 issue | 3 |
| INT issues | highest order among dependencies + 1 |
| TEST issues | max execution_order of all DB/API/UI/INT issues in feature + 1 |
| E2E issues | max execution_order of all TEST issues in feature + 1 |

### Step 8 — Run Dependency Graph Validation

Check for: circular dependencies, missing ID references, execution order inconsistencies, and missing INT issues. Halt and report all errors before generating any output.

**Additional check — INT issue presence:**
For every feature group (Epic), verify at least one INT issue exists. If any feature has DB/API/UI issues but no INT issue, apply Rule 10 (auto-generate) before proceeding — do not halt, but flag the auto-generated issue in the HITL checkpoint.

```
Dependency Graph Validation Failed

Errors:
1. CIRCULAR_DEPENDENCY_ERROR: [ISSUE-ID] -> [ISSUE-ID] -> [loop back]
2. MISSING_REFERENCE_ERROR: [ISSUE-ID] references [UNKNOWN-ID] which does not exist
3. ORDER_INCONSISTENCY_ERROR: [ISSUE-ID] (order: 2) depends on [ISSUE-ID] (order: 3)
```

### Step 9 — Generate Human-Readable Issues

For each Feature group: Epic issue first (using Epic Issue Template), then child issues grouped by layer and sequenced by execution_order (using Child Issue Template).

### Step 10 — Generate Execution Plan Summary

### Step 11 — Save Machine-Readable JSON

Save the complete issue manifest to `ai-context/issues.json` within the connected project folder. This file is the handoff artifact for `/push-to-pms`.

Epic issues appear first (execution_order: 0, parent_epic_id: null). Every child issue includes parent_epic_id.

### Step 12 — Present HITL Issue Review Checkpoint

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HITL ISSUE REVIEW CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Issue decomposition complete.
[N] Epics | [N] child issues | [X] layers | [Y] execution waves | [Z] parallelisable pairs

Issue structure:
  [DOMAIN]-EPIC → [N] child issues
  [DOMAIN]-EPIC → [N] child issues

Saved to: /ai-context/issues.json

Use the `AskUserQuestion` tool to interactively collect confirmation. Present a **multi-select** question so the user confirms all items in a single interaction.

**Call `AskUserQuestion` with:**
- question: "Please confirm the Issue Review items that are complete. Select all that apply:"
- multiSelect: true
- options:
  1. All issues correctly scoped and named
  2. Acceptance criteria testable and complete
  3. Dependency ordering is correct
  4. Layer assignments correct (DB/API/UI/INT/TEST/E2E)
  5. No issues missing; no duplicate scope
  6. Execution wave plan agreed
  7. Epic groupings reflect Feature boundaries
  8. Every implementation issue has mapped UT- test IDs
  9. TEST issues cover all IT- IDs from test plan
  10. E2E issues cover all ST- smoke test IDs from test plan
  11. Every feature has at least one INT issue covering end-to-end integration (auto-generated ones confirmed and scoped correctly)

**If all 11 items are selected:** State "✅ Issue Breakdown Approved." Then instruct the user to run `/push-to-pms` to create issues in their project management platform.

**If any items are NOT selected:** List each unconfirmed item, state "⛔ Issue Breakdown requires revision — do not proceed until all items are confirmed.", and halt.

> The user may also reply EXPORT to receive the JSON manifest only (already saved — no further action needed).
```

---

## Dependency Detection Logic

### Rule 1 — Schema-Before-API (Always Blocking)
API issue reads/writes a table introduced by a DB issue → API blocking depends on DB.

### Rule 2 — API-Before-UI (Always Blocking)
Frontend issue calls an endpoint introduced by a Backend issue → UI blocking depends on API.

### Rule 3 — Auth-Before-Dependent (Always Blocking)
Any issue requires a new auth mechanism from another issue → all dependents blocking on auth issue.

### Rule 4 — Migration-Before-Seed (Always Blocking)
Seed issue depends on schema migration → seed blocking on migration.

### Rule 5 — Service-Before-Integration (Always Blocking)
Integration issue wires a service being created in this run → integration blocking on service creation.

### Rule 6 — Independent Issues (Parallel)
No rule above creates a dependency → assign type: "parallel". Do NOT manufacture dependencies.

### Rule 7 — Cross-Feature Integration
Issue integrates with a pre-existing external service (not created in this run) → type: "integration".

### Rule 8 — Implementation-Before-Test (Always Blocking)
TEST issue for a feature → depends on ALL DB/API/UI/INT issues in the same feature group. No implementation issue may be missing from the dependency list.

### Rule 9 — Test-Before-E2E (Always Blocking)
E2E issue → depends on ALL TEST issues in the same feature group. E2E cannot run until integration tests are written and passing.

### Rule 10 — INT Issue Required Per Feature (Always)
Every feature that produces any DB, API, or UI issues **must** have at least one INT issue. The INT issue must depend on all DB/API/UI siblings in the same feature.

If the feature breakdown produces DB/API/UI issues but no INT issue, **generate one** before presenting output:
- **Title:** `[DOMAIN]-INT-001 — Integrate and verify end-to-end feature flow`
- **Acceptance criteria:** The feature works end-to-end as described in the feature doc, with all components/layers integrated and verified in the target environment.
- **Dependencies:** all DB/API/UI siblings in this feature group
- **Note in HITL:** "INT-001 was auto-generated — confirm its scope reflects the project's integration layer definition in `ai-context/architecture.md`."

This rule exists because atomic DB/API/UI issues each deliver an isolated piece. Without a dedicated INT issue, nobody owns the assembly step — the point at which the feature becomes a working, connected whole.

---

## Epic Issue Template

---

### [DOMAIN]-EPIC — [Epic] Feature Name (F-XX)

**Epic ID:** `[DOMAIN]-EPIC`
**Feature Reference:** F-XX
**PRD Reference:** FR-[n] to FR-[n]
**Category:** `epic`
**Child Issues:** [N] issues across [X] layers

---

#### Overview

2-4 sentences: what this Feature delivers and why it matters. Drawn from the Feature description.

---

#### User Stories Covered

| User Story ID | Summary |
|--------------|---------|
| US-XX.1 | As a [role], I want [capability] |

---

#### Child Issue Summary

| Issue ID | Layer | Title | Execution Order |
|---------|-------|-------|----------------|
| [DOMAIN]-DB-001 | Database | [title] | 1 |
| [DOMAIN]-API-001 | Backend | [title] | 2 |
| [DOMAIN]-UI-001 | Frontend | [title] | 3 |

---

#### Definition of Done (Epic)

- [ ] All child issues are resolved
- [ ] Feature acceptance criteria from PRD are met end-to-end
- [ ] All regression tests (RT-) mapped to this feature's ACs are passing
- [ ] Smoke tests (ST-) covering this feature's critical path are passing on deployment
- [ ] No open blocking dependencies remain

---

## Child Issue Template

---

### [DOMAIN]-[LAYER]-[NNN] — [Title]

**Issue ID:** `[DOMAIN]-[LAYER]-[NNN]`
**Layer:** Database / Backend / Frontend / Integration
**Execution Order:** [N]
**Parent Epic:** `[DOMAIN]-EPIC`
**Category:** `[layer]`, `[service-or-component]`
**PRD Reference:** FR-[N], AC-[N]

**Dependencies:**
| Depends On | Type | Title |
|-----------|------|-------|
| [ISSUE-ID] | blocking / parallel / integration | [title] |

Write "None — root issue." if no dependencies.

---

#### Description

2-4 sentences: what this issue implements and why. Reference the PRD feature and user impact.

---

#### Scope

- [Specific deliverable]

**Out of Scope for this issue:**
- [Explicit exclusion]

---

#### Acceptance Criteria

- [ ] AC-[N]: Given [context], when [action], then [outcome]

---

#### Technical Notes

**Backend:** [notes, or "N/A"]
**Frontend:** [notes, or "N/A"]
**Database:** [notes, or "N/A — for DB-layer issues, see Database Specification section below"]

---

#### Database Specification *(DB-layer issues only — omit for API/UI/INT)*

> All naming, ID strategy, auditing, and soft-delete conventions come from `ai-context/database-guidelines.md`.

| Field | Value |
|-------|-------|
| **Entity** | [Entity name — from Entity Ownership Map; this feature owns it] |
| **Table Name** | [snake_case plural, per database-guidelines.md naming convention] |
| **Migration File** | `[timestamp]_[description].[ext]` — per migration tooling convention |
| **Owned By Feature** | [F-XX — from Entity Ownership Map] |

**Fields to Define** *(logical names and purpose only — engineer determines final types from guidelines)*

| Field Name | Purpose | Nullable | Sensitive |
|-----------|---------|----------|-----------|
| id | Primary key — per ID strategy in database-guidelines.md | No | No |
| [field_name] | [purpose] | Yes / No | PII / PHI / PCI / No |
| created_at | Audit timestamp — required per database-guidelines.md | No | No |
| updated_at | Audit timestamp — required per database-guidelines.md | No | No |
| deleted_at | Soft-delete — include if soft-delete strategy applies | Yes | No |

**Indexes Needed**
- [e.g., index on tenant_id for multi-tenant row filtering]
- [e.g., composite index on (user_id, created_at) for timeline queries]

**Seed Data** *(if applicable)*
- [e.g., seed default roles: admin, member, viewer]
- None

> ⚠️ If cardinality or nullable status is ambiguous for any field, use `AskUserQuestion` before generating the issue. Example: *"The [EntityName].[fieldName] field — is this required (NOT NULL) or optional (nullable)?"*

---

#### API Considerations

| Method | Route | Request Shape | Response Shape | Auth |
|--------|-------|--------------|----------------|------|

Write "N/A" if not applicable.

---

#### Test Requirements

Populate from `/ai-context/test-plan.md` by matching this issue's FR-n, AC-n, and US-XX.N references.

| Test ID | Type | Requirement | Behavior |
|---------|------|-------------|----------|
| UT-[N] | Unit | FR-n / AC-n | [What behavior is verified] |
| IT-[N] | Integration | US-XX.N | [What cross-boundary behavior is verified] |
| RT-[N] | Regression | AC-n | [What must not regress] |

Smoke coverage: list any ST- test IDs that exercise this issue's critical path. Mark blocking ones explicitly.

If `test-plan.md` is not present, write: "No test plan available — define test cases during implementation."

---

#### Definition of Done

- [ ] Code reviewed and approved
- [ ] All acceptance criteria pass
- [ ] All mapped UT- specs pass
- [ ] All mapped IT- tests pass (real vs. stubbed per test plan)
- [ ] No mapped RT- regression tests broken in related features
- [ ] Relevant ST- smoke tests pass on deployment
- [ ] No regressions in related services
- [ ] [Layer-specific item]

---

## Execution Plan Summary

### Execution Plan

| Execution Order | Issue ID | Title | Layer | Depends On | Can Parallelise With |
|----------------|---------|-------|-------|-----------|----------------------|
| 0 (Epic) | AUTH-EPIC | [Epic] Authentication | Epic | None | other Epics |
| 1 | AUTH-DB-001 | [title] | Database | None | AUTH-DB-002 |
| 2 | AUTH-API-001 | [title] | Backend | AUTH-DB-001 | None |
| 3 | AUTH-UI-001 | [title] | Frontend | AUTH-API-001 | None |

### Execution Summary

```
Wave 0 (Epics, created first): [AUTH-EPIC], [INSTR-EPIC], ...
Wave 1 (parallel):             [AUTH-DB-001], [AUTH-DB-002], ...
Wave 2 (parallel):             [AUTH-API-001], ...
Wave 3 (sequence):             [AUTH-UI-001]

Total Epics:        N
Total child issues: N
Parallelisable:     N
Sequential only:    N
Estimated waves:    N
```

---

## Machine-Readable JSON Schema

Label this block: **Issue Manifest JSON**

Epic issues appear first (execution_order: 0, parent_epic_id: null). Every child issue includes parent_epic_id.

```json
[
  {
    "id": "AUTH-EPIC",
    "title": "[Epic] Authentication (F-01)",
    "body": "## Overview\n\n...\n\n## User Stories Covered\n\n...\n\n## Definition of Done (Epic)\n\n- [ ] All child issues resolved",
    "type": "epic",
    "category": ["epic", "feature"],
    "execution_group": "epic",
    "execution_order": 0,
    "parent_epic_id": null,
    "dependencies": [],
    "prd_references": ["FR-01", "FR-02"],
    "test_ids": []
  },
  {
    "id": "AUTH-DB-001",
    "title": "Create users table migration",
    "body": "## Description\n\n...\n\n## Acceptance Criteria\n\n- [ ] AC-1: Given...\n\n## Definition of Done\n\n- [ ] Code reviewed\n- [ ] ACs pass\n- [ ] Tests passing",
    "type": "task",
    "category": ["database", "auth"],
    "execution_group": "database",
    "execution_order": 1,
    "parent_epic_id": "AUTH-EPIC",
    "dependencies": [],
    "prd_references": ["FR-01", "AC-01"],
    "test_ids": ["UT-01", "UT-02", "RT-01"]
  }
]
```

### JSON Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Epic: [DOMAIN]-EPIC. Child: [DOMAIN]-[LAYER]-[NNN]. Uppercase, stable across downstream tools. |
| `title` | string | Yes | Epics prefixed [Epic]. Matches human-readable title exactly. |
| `body` | string | Yes | Full markdown content. Portable across all platforms. |
| `type` | string | Yes | `"epic"` for Epics. `"task"` for child issues. Platform mapping handled by /push-to-pms. |
| `category` | string[] | Yes | Semantic labels. Epics: ["epic", "feature"]. Children: layer + service. Platform mapping handled by /push-to-pms. |
| `execution_group` | string | Yes | Epics: "epic". Children: "database", "backend", "frontend", or "integration". |
| `execution_order` | integer | Yes | Epics: 0. Children: >= 1. Equal values may run in parallel. |
| `parent_epic_id` | string or null | Yes | Epics: null. Children: must reference a valid Epic id. Never omit. |
| `dependencies` | object[] | Yes | Epics: []. Children: [] for root issues. Never reference Epic IDs here. |
| `dependencies[].id` | string | Yes | Must reference a valid child issue id in this array. |
| `dependencies[].type` | string | Yes | "blocking", "parallel", or "integration". |
| `prd_references` | string[] | Yes | FR-n, AC-n references that this issue satisfies. |
| `test_ids` | string[] | Yes | UT-, IT-, RT-, ST- IDs from test-plan.md that this issue must satisfy. Empty array if no test plan. |

---

## Rules / Guardrails

### NEVER
- Generate issues before running dependency graph validation
- Reference Epic IDs in the dependencies array of any issue
- Set parent_epic_id to null on a child issue
- Generate vague issues that require clarification to execute
- Create issues spanning multiple services or layers
- Skip dependencies, execution_order, or parent_epic_id on any issue
- Include platform-specific fields (GitHub numbers, Jira keys, ADO IDs) in the JSON — that is /push-to-pms's job
- Close a feature Epic without ensuring at least one INT issue covers end-to-end integration

### ALWAYS
- Assign Epic IDs before child issue IDs, before building any dependency map
- Run all three dependency graph validation checks before generating output
- Apply the atomicity test to every child issue
- Output Epic issues first in both human-readable sections and the JSON array
- Group human-readable child issues by Feature group, then by layer
- Include PRD reference (FR-N, AC-N) on every issue
- Include test_ids on every child issue (empty array if no test plan)
- Save the JSON manifest to `ai-context/issues.json` (in the connected project folder) before presenting the HITL checkpoint
- End every run with the HITL Issue Review Checkpoint
- Ensure every feature with DB/API/UI issues has at least one INT issue (auto-generate under Rule 10 if missing)
