---
name: write-prd
description: >
  Use this skill when the user types /write-prd followed by a validated idea, a /grill output, or a sufficiently defined feature requirement.
  This skill generates a structured, implementation-ready PRD for the Greenfield workflow only.
  Trigger on /write-prd, "write a PRD for", "turn this into a PRD", "create the requirements doc", "generate requirements for", or "this is ready for PRD".
  Also trigger when the user shares /grill output and says "now write the PRD" or "we're ready to document this".
  If the input is vague or ungrilled, halt and instruct the user to run /grill first.
  This skill is Step 2 of the Greenfield workflow. Produces output consumable by /prd-to-features (mandatory next step — do NOT skip to /feature-to-issues).
  Full Greenfield workflow: /grill → /write-prd → /generate-project-constitution (optional) → /prd-to-features → HITL Feature Review → /feature-to-issues → HITL Issue Review → Ready to Develop.
  For brownfield enhancements without a formal PRD, use /write-feature instead.
---

# /write-prd — Product Requirements Document Generator

## Workflow Role

`/write-prd` is **Step 2 of the Greenfield workflow only**.

```
GREENFIELD:  /grill → [/write-prd] → /generate-project-constitution (optional) → /prd-to-features → HITL Feature Review
                                                        → /feature-to-issues → HITL Issue Review → Ready to Develop

BROWNFIELD:  /grill → /write-feature → HITL Feature Review
                                      → /feature-to-issues → HITL Issue Review → Ready to Develop
```

**If the requirement is a brownfield enhancement:** halt and redirect to `/write-feature`.
**Mandatory next step after this skill:** `/prd-to-features` — do NOT pass PRD output directly to `/feature-to-issues`.

---

## Purpose

Convert a validated, sufficiently defined idea into a structured, implementation-ready PRD.

The output must be:
- Precise and unambiguous
- Directly consumable by `/prd-to-features` for feature decomposition
- Aligned with microservices architecture and API-first design
- Complete with testable acceptance criteria and Playwright test scenarios

---

## When to Use

- After `/grill` has resolved all blocking questions
- When a feature idea has sufficient clarity to define scope, flows, and acceptance criteria
- Before any sprint planning, feature breakdown, or development begins
- When a stakeholder-approved idea needs to be formalized for engineering

---

## Input Format

```
/write-prd [validated idea, feature description, or /grill output]
```

Examples:
```
/write-prd Users can export their account data as a CSV. Export is async, delivered via email. Scoped to authenticated users only. Admins cannot export on behalf of others.
/write-prd Add two-factor authentication via TOTP for all user accounts
```
> If you've just run `/grill`, the Clarity Summary is already in context — just type `/write-prd` to proceed.

---

## Execution Instructions (Step-by-Step)

### Step 0 — Project Folder Setup

This step runs **before any other step** on every `/write-prd` invocation.

#### 0a — Check for a connected project folder

Check the `<env>` context block for `User selected a folder`.

- **If "yes":** A project folder is already connected. Proceed to Step 0b.
- **If "no":** Call `mcp__cowork__request_cowork_directory` to ask the user to select or create a project folder. Wait for confirmation before proceeding. If the user declines, halt with:

  ```
  ⛔ A project folder is required to proceed.
  All artifacts (PRD, feature breakdown, test plan, issues) will be saved there.
  Please select or create a folder and re-run /write-prd.
  ```

#### 0b — Derive the project name

Extract the project/product name from the user's input. Slugify it: lowercase, words separated by hyphens, no spaces or special characters. If the name cannot yet be derived, use `new-project` temporarily.

#### 0c — Create the standard folder structure

In the connected project folder, create the following directories if they do not already exist:

```
<project-root>/
├── ai-context/          ← agent context files (read by all downstream skills)
└── docs/
    └── features/        ← individual feature docs (write-feature brownfield outputs)
```

Create `ai-context/project.json` if it does not exist:

```json
{
  "name": "<Project Name>",
  "slug": "<project-slug>",
  "created_at": "<YYYY-MM-DD>",
  "workflow": "greenfield",
  "artifacts": {
    "prd": "docs/prd.md",
    "feature_summary": "docs/features/feature-summary.md",
    "features_dir": "docs/features/",
    "test_plan": "docs/test-plan.md",
    "issues_manifest": "ai-context/issues.json"
  }
}
```

#### Standard Project Artifact Paths

All skills in this workflow write artifacts to these **project-root-relative** paths:

| Artifact | Path in Project Folder | Skill |
|----------|------------------------|-------|
| PRD | `docs/prd.md` | `/write-prd` |
| Project Constitution | `ai-context/project-constitution.md` | `/generate-project-constitution` |
| Architecture | `ai-context/architecture.md` | `/generate-project-constitution` |
| Tech Stack | `ai-context/tech-stack.md` | `/generate-project-constitution` |
| Coding Standards | `ai-context/coding-standards.md` | `/generate-project-constitution` |
| Testing Strategy | `ai-context/testing.md` | `/generate-project-constitution` |
| Feature Summary | `docs/features/feature-summary.md` | `/prd-to-features` |
| Feature Files | `docs/features/F-XX-<slug>.md` (one per feature) | `/prd-to-features` |
| Feature Doc (brownfield) | `docs/features/<FEAT-ID>-<slug>.md` | `/write-feature` |
| Test Plan | `docs/test-plan.md` | `/write-test-plan` |
| Issue Manifest | `ai-context/issues.json` | `/feature-to-issues` |

> All paths are relative to the connected project folder. **Never write artifacts to the temporary outputs folder.** The connected folder IS the project root.

---

### Step 1 — Load Context Files

Before writing anything, load:

1. `/agents.md` — routing logic, agent roles, execution rules
2. `/ai-context/architecture.md` — system boundaries, service topology, ownership model
3. `/ai-context/tech-stack.md` — constraints: React/TypeScript, .NET Core microservices, SQL Server, Playwright

> If any file is missing, note it and proceed with available context. Do not block PRD generation for missing context files.

### Step 2 — Assess Input Quality

Before writing the PRD, evaluate the input:

**Input is sufficient if:**
- The core problem is clear
- At least one user persona is identifiable
- Functional intent is stated
- At least the happy path flow can be described

**Input is insufficient if:**
- The idea is one sentence with no supporting detail
- Critical items from the Missing Information section of a `/grill` output are unresolved
- Scope is undefined (no in/out scope signals)

**If input is insufficient:**
```
⛔ Input is not ready for PRD generation.

The following must be resolved before proceeding:
- [List blocking gaps]

Run /grill on this idea first, or provide answers to the above before retrying /write-prd.
```

**Do not generate a partial PRD. Either proceed fully or halt.**

### Step 3 — Write the PRD

Use the strict 15-section template below. Every section is mandatory. Do not skip, merge, or reorder sections.

### Step 3b — Save the PRD

After writing all 16 sections, save the completed document to the project folder:

- **File path:** `docs/prd.md` (relative to the connected project folder)
- Use the Write file tool to create or overwrite this file.
- Confirm to the user: "PRD saved to `docs/prd.md`."

---

### Step 4 — Self-Review Before Output

Before finalizing, verify:
- [ ] No vague language (e.g., "fast", "easy to use", "as needed", "etc.")
- [ ] Every functional requirement is atomic and implementable as a single unit of work
- [ ] Every acceptance criterion is binary — it either passes or fails
- [ ] Every Playwright scenario has a named flow, action sequence, and expected assertion
- [ ] API section names a specific .NET Core microservice owner
- [ ] Open Questions section is populated if any ambiguity remains

---

## Output Structure (Strict Template)

---

### 1. 📋 Feature / Product Title

> One-line name for this feature. Should be specific enough to use as a GitHub epic or Jira epic title.

**Title:** [Feature Name]
**Date:** [YYYY-MM-DD]
**Author:** [Requestor or team, if known]
**Status:** Draft

---

### 2. 🧩 Problem Statement

> What problem does this solve? Who experiences it? What is the current state without this feature?

Write 2–4 sentences. Be specific. Avoid marketing language.

Do not write: *"Users need a better experience."*
Write instead: *"Authenticated users have no mechanism to retrieve their account data in a portable format, requiring manual support requests that average 3 business days to fulfill."*

---

### 3. 🎯 Objectives

> What does success look like? Each objective must be measurable or falsifiable.

| # | Objective | Success Signal |
|---|-----------|----------------|
| 1 | | |
| 2 | | |

---

### 4. 📐 Scope

#### In Scope
- [Item 1]
- [Item 2]

#### Out of Scope
- [Item 1]
- [Item 2]

> Out of Scope items must be explicit. Do not leave scope to inference.

---

### 5. 👤 User Personas

> Who will use this feature? Include role, permissions level, and primary motivation.

| Persona | Role | Permissions | Goal |
|---------|------|-------------|------|
| | | | |

---

### 6. 🔄 User Flows

> Step-by-step interaction flows for each persona. One flow per significant path.

#### Flow 1: [Flow Name] — [Persona]

1. User navigates to [location]
2. User [action]
3. System [response]
4. ...
5. End state: [final system state]

#### Flow 2: [Flow Name] — [Persona]
*(Repeat as needed)*

> Every flow must have a defined end state. Do not leave flows open-ended.

---

### 7. ⚙️ Functional Requirements

> Atomic, implementation-ready requirements. Each item must map to a single unit of work.

Use the ID format `FR-[n]` for traceability.

| ID | Requirement | Priority |
|----|------------|----------|
| FR-1 | | Must Have |
| FR-2 | | Must Have |
| FR-3 | | Should Have |
| FR-4 | | Nice to Have |

**Priority definitions:**
- **Must Have** — feature cannot ship without this
- **Should Have** — strong business need, can be deferred by one sprint
- **Nice to Have** — improvement, not blocking

> Each requirement must be a complete sentence describing system behavior. Not a topic. Not a verb fragment.

❌ *"Export button"*
✅ *"FR-1: The system shall provide an Export button on the Account Settings page, visible only to authenticated users."*

---

### 8. ✅ Acceptance Criteria

> Testable, binary pass/fail criteria. Each criterion maps directly to one or more FRs.

Use the ID format `AC-[n]`.

- **AC-1:** [Condition] → [Expected outcome] *(maps to FR-n)*
- **AC-2:** [Condition] → [Expected outcome] *(maps to FR-n)*
- ...

> Every AC must be binary. If it cannot be evaluated as pass/fail, rewrite it.

❌ *"Export should be reasonably fast"*
✅ *"AC-5: When a user triggers an export of fewer than 10,000 records, the system shall initiate the job and return a 202 Accepted response within 500ms. (maps to FR-3)"*

---

### 9. 🔌 API Considerations

> Which microservice owns this? What endpoints are expected? What do the data contracts look like?

**Owning Service:** [Service name from architecture.md]

#### Expected Endpoints (High-Level)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/[resource]` | | Yes/No |
| GET | `/api/v1/[resource]/{id}` | | Yes/No |

#### Request / Response Contracts (if known)

```json
// POST /api/v1/[resource] — Request
{
  "field": "type"
}

// Response — 202 Accepted
{
  "field": "type"
}
```

> Contracts are indicative at PRD stage. Final contracts are owned by the service team. Mark any contract detail as `[TBD]` if unknown.

---

### 10. 💾 Data Requirements

> Capture conceptual data entities and their sensitivity. **Do NOT define tables, columns, data types, foreign keys, indexes, constraints, or migration specs here** — that is engineering work done in `/feature-to-issues` guided by `database-guidelines.md`.

#### Entity Inventory

| Entity | One-Line Description | Sensitivity Classification | High-Level Storage |
|--------|----------------------|---------------------------|--------------------|
| | | None / PII / PHI / PCI / Confidential | Relational / Document / Cache / Object |

> Sensitivity classifications: **None** (no special handling), **PII** (personally identifiable), **PHI** (health data — HIPAA), **PCI** (payment card — PCI-DSS), **Confidential** (internal business-sensitive).

#### Compliance Obligations

- Applicable frameworks: [HIPAA / GDPR / SOC 2 / PCI-DSS / none — list all that apply]
- Encryption requirements: [at rest / in transit / both / none]
- Audit trail requirements: [e.g., all writes must be logged with user + timestamp / none]
- Data residency / localization: [e.g., EU data must stay in EU / no constraint]
- Retention and deletion policies: [e.g., user data deleted within 30 days of account closure]

> ⚠️ **Boundary:** Do not specify table names, column definitions, data types, foreign keys, indexes, constraints, or migration details in this section. Those decisions are owned by the engineering layer and governed by `ai-context/database-guidelines.md`.

---

### 11. ⚠️ Edge Cases & Failure Scenarios

> Explicit handling of errors and unusual flows. Each scenario must include the expected system behavior.

| # | Scenario | Expected System Behavior |
|---|----------|--------------------------|
| 1 | | |
| 2 | | |
| 3 | | |

*Minimum 4 scenarios. Cover: invalid input, unauthorized access, downstream service failure, concurrent operations, empty/zero states.*

**State Cross-Product Table (mandatory whenever the Clarity Summary's State Matrix is non-empty):**

> If any entity or actor in this feature has more than one state (session, account, subscription,
> connection status, etc.), a fixed count of "4 scenarios" is not sufficient — every combination of
> (entity state × actor state × entry point) must get an explicit row. A feature is not ready for
> engineering until every cell below is filled, not just the primary/happy-path combination.

| # | State Combination | Entry Point | Expected System Behavior |
|---|--------------------|-------------|---------------------------|
| 1 | | | |
| 2 | | | |

---

### 12. 🛡️ Non-Functional Requirements

#### Performance
- [Specific latency, throughput, or load targets]

#### Security
- [Auth requirements, data access controls, audit logging needs]

#### Scalability
- [Expected volume, growth assumptions, concurrency requirements]

#### Accessibility
- [WCAG level target, keyboard navigation, screen reader requirements — if applicable]

#### Resilience
- [What happens to the rest of the system when this feature's dependency call fails — a single
  external-dependency failure (timeout, 5xx, malformed response) must degrade this feature gracefully
  and must never take down unrelated requests or crash the process. State the specific fallback:
  stale-data display, cached last-known-good value, disabled control with a message, etc. — not just
  "handle errors gracefully."]
- [If this feature has multiple failure classes from the same dependency (e.g. rate-limit vs. timeout
  vs. server error), state whether they all get the same fallback treatment or differ, explicitly.]

> Do not write "the system should be secure." Write the specific control required.

---

### 13. 🧪 Playwright Test Scenarios (MANDATORY)

> Define every scenario that must be covered by Playwright E2E tests. These feed directly into test generation.

Use the ID format `PT-[n]`.

#### Happy Path

- **PT-1: [Scenario Name]**
  - **Precondition:** [System state before test]
  - **Steps:** [Numbered user actions]
  - **Assertion:** [What Playwright must assert at the end]

#### Negative Cases

- **PT-[n]: [Scenario Name]**
  - **Precondition:** [System state before test]
  - **Steps:** [Numbered user actions]
  - **Assertion:** [What Playwright must assert — error message, blocked action, redirect]

#### Edge Cases

- **PT-[n]: [Scenario Name]**
  - **Precondition:** [System state before test]
  - **Steps:** [Numbered user actions]
  - **Assertion:** [What Playwright must assert]

*Minimum 6 Playwright scenarios total: at least 2 happy path, 2 negative, 2 edge case.*
*Flag any scenario that requires test data seeding, mocking, or cross-service coordination.*

---

### 14. 🔗 Dependencies

> Cross-service, external system, or infrastructure dependencies required before this feature can ship.

| # | Dependency | Type | Owner | Blocking? | Contract Verified? |
|---|-----------|------|-------|-----------|---------------------|
| 1 | | Internal Service | | Yes/No | Y/N/N-A |
| 2 | | External / Third Party | | Yes/No | Y/N |

> **Contract Verified?** applies to any `External / Third Party` dependency this feature's FRs rely on
> for a *specific* capability (a filter param, a response shape, which host serves an endpoint, a rate
> or tier limit) — "Y" means that capability was checked against real documentation or a spike, not
> assumed. Any row with `Blocking: Yes` and `Contract Verified: N` must be copied into §15 Open Questions
> as a **blocking** item — do not proceed to `/prd-to-features` with an unverified external contract that
> the FRs depend on.

---

### 15. ❓ Open Questions

> Any remaining ambiguities that could not be resolved from the input. These must be answered before development starts.

| # | Question | Owner | Blocking? |
|---|---------- |-------|-----------|
| 1 | | | Yes/No |

> If this section is empty, the PRD is complete and ready for `/prd-to-features`.
> If this section is non-empty, do not proceed until all blocking questions are resolved.

---

### 16. ✅ HITL Checkpoint — PRD Review

Use the `AskUserQuestion` tool to interactively collect confirmation before proceeding. Present a **multi-select** question so the user confirms all items in a single interaction.

**Call `AskUserQuestion` with:**
- question: "Please confirm the PRD review items that are complete. Select all that apply:"
- multiSelect: true
- options:
  1. Problem statement accurately reflects the business need
  2. Scope boundaries are explicitly defined and agreed
  3. All Must Have functional requirements are included
  4. Acceptance criteria are binary and testable
  5. Open Questions section is empty or has named owners

**If all 5 items are selected:** State "✅ PRD Approved." Then remind the user the next step is `/generate-project-constitution` (optional, to define engineering standards) or proceed directly to `/prd-to-features`.

**If any items are NOT selected:** List each unconfirmed item, state "⛔ PRD requires revision — do not proceed to the next step until all items are confirmed.", and halt.

> This checkpoint is the handoff gate between Product planning and Feature decomposition.

---

## Rules / Guardrails

### NEVER
- Use vague language: "fast", "easy", "simple", "as needed", "etc.", "and so on", "good performance"
- Leave acceptance criteria that cannot be evaluated as binary pass/fail
- Skip the Playwright section or write generic scenarios ("test that it works")
- Omit the Out of Scope section — silence is not out-of-scope
- Write functional requirements as topics or fragments
- Generate a partial PRD — either the input is ready or it is not

### ALWAYS
- Load `/agents.md`, `/ai-context/architecture.md`, `/ai-context/tech-stack.md` before writing
- Name a specific microservice owner in the API section
- Use ID prefixes (`FR-`, `AC-`, `PT-`) on all requirements, criteria, and test scenarios
- Map every AC to one or more FRs
- Populate Open Questions if any ambiguity remains after writing
- Write every Playwright scenario with Precondition, Steps, and Assertion
- Halt with a structured error message if input is insufficient — do not guess
- End every output with the HITL Checkpoint (Section 16) — never skip it
- Save the completed PRD to `docs/prd.md` in the connected project folder before presenting the HITL checkpoint
- Remind the user: after HITL review passes, optionally run `/generate-project-constitution` to establish engineering standards, then proceed to `/prd-to-features`
- Redirect to `/write-feature` if the input describes a brownfield enhancement, not a new product

### LANGUAGE STANDARD

Every functional requirement must follow the format:
> *"The system shall [behavior] when [condition], resulting in [outcome]."*

Every acceptance criterion must follow the format:
> *"When [condition], the system shall [measurable outcome]."*

---

## Example Usage

**Input:**
```
/write-prd Users can export their account data as a CSV. Export is async — system emails a download link when ready. Scoped to authenticated users only. Export includes: profile info, transaction history, activity log. Max export size: 50,000 rows. Admins cannot export on behalf of others. Owned by the UserDataService.
```

**Selected output excerpts (abbreviated):**

---

**📋 Feature / Product Title**
**Title:** Async Account Data Export
**Status:** Draft

---

**🧩 Problem Statement**
Authenticated users have no self-service mechanism to retrieve a portable copy of their account data. This results in manual support requests averaging 3 business days to fulfill, impacting user trust and support team capacity.

---

**⚙️ Functional Requirements (excerpt)**

| ID | Requirement | Priority |
|----|------------|----------|
| FR-1 | The system shall provide an Export My Data button on the Account Settings page, visible only to authenticated users. | Must Have |
| FR-2 | The system shall limit export scope to the requesting user's own data; admin roles shall not be permitted to trigger exports on behalf of other users. | Must Have |
| FR-3 | The system shall generate the export asynchronously and send a time-limited download link to the user's verified email address upon completion. | Must Have |
| FR-4 | The system shall enforce a maximum export size of 50,000 rows; requests exceeding this limit shall be rejected with an HTTP 422 and a descriptive error message. | Must Have |

---

**✅ Acceptance Criteria (excerpt)**

- **AC-1:** When an authenticated user clicks Export My Data, the system shall return an HTTP 202 Accepted response within 500ms and display a confirmation message: "Your export is being prepared. You'll receive an email when it's ready." *(maps to FR-1, FR-3)*
- **AC-2:** When an admin-role user attempts to trigger an export for another user's account via the API, the system shall return HTTP 403 Forbidden. *(maps to FR-2)*
- **AC-3:** When a user's export contains more than 50,000 rows, the system shall reject the request with HTTP 422 and the message: "Export exceeds the maximum allowed size of 50,000 rows." *(maps to FR-4)*

---

**🧪 Playwright Test Scenarios (excerpt)**

- **PT-1: Authenticated user triggers export successfully**
  - **Precondition:** User is logged in; account has between 1 and 49,999 rows of exportable data
  - **Steps:** 1. Navigate to Account Settings. 2. Click "Export My Data". 3. Observe confirmation message.
  - **Assertion:** Playwright asserts confirmation banner is visible with text "Your export is being prepared."

- **PT-3: Admin cannot export on behalf of another user**
  - **Precondition:** Admin user is logged in; target user account exists
  - **Steps:** 1. Admin navigates to user management. 2. Attempts to trigger export for another user via UI action or direct API call.
  - **Assertion:** Playwright asserts HTTP 403 response and no export job is created in the database.

- **PT-5: Export exceeds 50,000-row limit**
  - **Precondition:** Test account seeded with 50,001 exportable rows
  - **Steps:** 1. Authenticated user navigates to Account Settings. 2. Clicks "Export My Data".
  - **Assertion:** Playwright asserts error message "Export exceeds the maximum allowed size of 50,000 rows." is displayed; no email is sent; no export job is created.
  - **Note:** Requires test data seeding via fixture before run.
