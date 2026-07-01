---
name: prd-to-features
description: >
  Use this skill when the user types /prd-to-features or provides a structured PRD and wants it decomposed
  into Features with embedded User Stories for downstream engineering execution.
  Trigger on: "/prd-to-features", "convert this PRD to features", "decompose PRD into features",
  "generate feature list from PRD", "break PRD into capabilities", "turn this PRD into a feature breakdown",
  or when the user shares a PRD and asks what should be built.
  Step 3 of the Greenfield workflow: /grill → /write-prd → [/prd-to-features] → HITL Feature Review
  → /write-test-plan → HITL Test Plan Review → /feature-to-issues → HITL Issue Review → Ready to Develop.
  Always use this skill before /feature-to-issues in the Greenfield path. Never skip this step.
---

# /prd-to-features — PRD to Feature Decomposition Skill

## Workflow Role

`/prd-to-features` is **Step 3 of the Greenfield workflow**.

```
GREENFIELD:  /grill → /write-prd → [/prd-to-features] → HITL Feature Review
                                                        → /write-test-plan → HITL Test Plan Review
                                                        → /feature-to-issues → HITL Issue Review → Ready to Develop
```

**Input:** Approved PRD from `/write-prd` (HITL Checkpoint Section 16 must be confirmed before this skill runs).
**Output:** Feature Breakdown → feeds into HITL Feature Review gate → then `/write-test-plan` → then `/feature-to-issues`.

**Do not run this skill if the PRD HITL review has not been completed.**
**Do not run this skill on brownfield enhancements** — use `/write-feature` instead.

## Purpose

This skill converts a structured PRD into a set of logically grouped **Features** with embedded **User Stories**.

It operates exclusively at the **Feature Layer** in the AI-driven software delivery hierarchy:

```
PRD  →  [THIS SKILL]  →  Features  →  /write-test-plan  →  /feature-to-issues  →  Issues  →  PRs
```

### What This Skill DOES

- Parses a PRD and identifies discrete business capabilities
- Groups related functionality into named, scoped Features
- Embeds User Stories within each Feature
- Identifies dependencies, sequencing, and risk
- Produces output compatible with downstream autonomous execution

### What This Skill MUST NOT DO

| Prohibited Output | Belongs To |
|---|---|
| GitHub/GitLab Issues | `/feature-to-issues` |
| API contracts or endpoint design | Engineering layer |
| Database schema or data models | Engineering layer |
| Code-level implementation details | Engineering layer |
| Test scripts or QA plans | Engineering layer |
| Sprint or ticket assignments | Delivery management layer |
| Pull Request structure | Engineering layer |

**If you find yourself writing any of the above, stop. You are operating below the Feature Layer.**

---

## Skill Execution Protocol

### Step 0 — Input Validation

Before decomposing, verify the PRD contains:

- [ ] A stated **product or system objective**
- [ ] At least one **user persona or actor**
- [ ] At least one **functional requirement or capability**

If any of these are missing, halt and output:

```
⚠️ INSUFFICIENT INPUT
This PRD is missing: [list what's absent].
Please provide a more complete PRD before running /prd-to-features.
Minimum required: product objective, at least one persona, at least one functional requirement.
```

If present, proceed.

---

### Step 1 — Load Context and Parse PRD

**Before parsing:** silently load any available project constitution files from `ai-context/` in the connected project folder. At minimum, attempt to read:
- `ai-context/project-constitution.md` — immutable principles and tech decisions
- `ai-context/architecture.md` — service boundaries and data ownership
- `ai-context/database-guidelines.md` — entity naming and DB conventions

Note any missing files and proceed. Constitution context informs Feature complexity ratings, layer assignments, and entity ownership decisions — but does not block decomposition if absent.

**Then** silently extract the following from the PRD:

1. **Primary Objective** — What is this product or system trying to accomplish?
2. **User Personas** — Who are the actors? (end users, admins, systems, external parties)
3. **Functional Domains** — What major capability areas are described?
4. **Explicit Requirements** — What must the system do?
5. **Implicit Requirements** — What is implied but not stated?
6. **Constraints** — What limitations, rules, or non-functional requirements exist?
7. **Integration Points** — What external systems, APIs, or services are referenced?
8. **Ambiguities** — What is unclear, conflicting, or underspecified?

Do not output Step 1 results directly. Use them to drive Feature decomposition.

---

### Step 2 — Feature Decomposition Rules

Apply the following rules when grouping PRD content into Features:

**Rule 1 — Business Capability Boundary**
Each Feature must represent a single, independently understandable **business capability**. A Feature is NOT a screen, a component, or a technical module.

**Rule 2 — Minimise Cross-Feature Coupling**
Features should be as self-contained as possible. Where coupling is unavoidable, explicitly declare it as a dependency.

**Rule 3 — Persona Alignment**
Each Feature must be traceable to at least one user persona. If a Feature cannot be tied to a persona, it is likely a technical task — escalate for human review.

**Rule 4 — Decomposition Scope**
- Minimum: 3 features per PRD
- Maximum: Determined by PRD complexity (no artificial splitting or merging)
- Each Feature must be large enough to contain at least 1 User Story
- Each Feature must be small enough to be independently understood

**Rule 5 — Dependency Sequencing**
Identify which Features must be delivered before others. Express as DAG-compatible dependency notation (Feature IDs only).

**Rule 6 — Risk Classification**
Flag Features as:
- `LOW` — Well-understood, low ambiguity, safe for autonomous execution
- `MEDIUM` — Some ambiguity or complexity; AI-executable with review checkpoint
- `HIGH` — Significant ambiguity, cross-system risk, or requires human review before decomposition

---

### Step 3 — User Story Rules

Each Feature must contain **one or more User Stories**.

**Format (mandatory):**
```
As a [persona], I want [capability], so that [business outcome].
```

**Rules:**
- Personas must match those identified in the PRD (or reasonably inferred)
- The "want" clause describes a **business action**, not a technical implementation
- The "so that" clause must state a **business value**, not a system behaviour
- A single Feature may have multiple User Stories if it serves multiple personas or use cases
- User Stories must not reference database tables, API endpoints, components, or implementation details

**Each User Story must also include:**

```
Acceptance Expectations:
- [Observable business outcome that confirms the story is satisfied]
- [Edge case or boundary condition if relevant]

Behavioral Expectations:
- [How the system should behave from the user's perspective]
- [Error or exception behaviour visible to the user]
```

---

## Output Template

Generate the feature breakdown as **multiple rendered Markdown files** — one summary file and one file per feature. Use proper headings, tables, and bullet lists. Do NOT wrap output in code blocks. All files must render cleanly in any Markdown previewer.

---

### File 1 — `docs/features/feature-summary.md`

This file contains cross-feature information only. No feature-specific detail belongs here.

---

#### feature-summary.md template

```markdown
# Feature Summary — [PRD Title]

**Generated:** [YYYY-MM-DD] | **Skill:** `/prd-to-features` | **Status:** Draft — Awaiting HITL Review

---

## Overview

| | |
|---|---|
| **Total Features** | [N] |
| **Execution Approach** | Sequential / Parallel / Hybrid |
| **High-Risk Features** | F-XX, F-XX — or None |
| **HITL Review Required** | F-XX, F-XX — or None |
| **Recommended Entry Point** | F-XX |
| **Next Skills** | `/write-test-plan` → `/feature-to-issues` |

---

## Features

| ID | Name | Complexity | HITL | Detail |
|---|---|---|---|---|
| F-01 | [Feature Name] | Low / Medium / High | ✅ Yes / ❌ No | [View →](./F-01-slug.md) |
| F-02 | [Feature Name] | Low / Medium / High | ✅ Yes / ❌ No | [View →](./F-02-slug.md) |

---

## Dependency Map

```
F-01 ──► F-03 ──► F-05
F-02 ──► F-03
F-04 ──► F-05 ──► F-06
```

> `──►` = must be completed before. Independent features appear as standalone nodes.

---

## Execution Waves

### Wave 1 — Foundation *(no dependencies, begin immediately)*

| Feature | Name | Can Parallelise? |
|---|---|---|
| F-01 | [Feature Name] | Yes / No |

### Wave 2 — Core Capabilities *(depends on Wave 1)*

| Feature | Name | Can Parallelise? |
|---|---|---|
| F-03 | [Feature Name] | Yes / No |

### Wave 3 — Extended Features *(depends on Wave 2 partial or full)*

| Feature | Name | Can Parallelise? |
|---|---|---|
| F-05 | [Feature Name] | Yes / No |

**Parallelism Notes:**
- [Features within a Wave that can run concurrently]
- [Features that must be serialised even within the same Wave]

---

## Entity Ownership

> Maps which domain entities are **introduced** (owned) by each feature and which entities each feature **accesses** from other features (entity dependencies — conceptual only, no physical FK detail).

| Feature | Entities Owned | Entity Dependencies |
|---|---|---|
| F-01 | User, UserProfile | — |
| F-02 | Order, OrderItem | User (F-01) |
| F-03 | Invoice | Order (F-02), User (F-01) |

> **Entity Dependencies** are cross-feature data dependencies at the domain model level. They do NOT imply foreign keys or join queries — those are engineering decisions governed by `ai-context/database-guidelines.md`.
```

---

### File 2 — `docs/features/F-XX-<slug>.md` *(one file per Feature)*

Slugify the Feature name: lowercase, words separated by hyphens (e.g. `F-01-user-authentication.md`). Repeat this template for every Feature, linking back to the summary.

---

#### F-XX-slug.md template

```markdown
# F-XX — [Feature Name]

**Status:** Draft | **Complexity:** Low / Medium / High | **HITL Required:** ✅ Yes — [reason] / ❌ No

[← Back to Feature Summary](./feature-summary.md)

---

## Overview

| | |
|---|---|
| **Business Objective** | [One sentence — what business goal does this achieve?] |
| **AI Execution Suitability** | High / Medium / Low — [one-line rationale] |
| **Execution Strategy** | Autonomous / Autonomous with HITL checkpoint / Human-led |

---

## Scope

**In Scope:**
- [Capability or behaviour included in this Feature]

**Out of Scope:**
- [What this Feature explicitly does NOT cover]

---

## Functional Description

[2–5 sentences describing the Feature from a product perspective. No technical implementation, code, schema, or endpoints.]

---

## User Personas

| Persona | Role |
|---|---|
| [Persona Name] | [Brief role description] |

---

## User Stories

### US-XX.1 — [Short Story Title]

> As a **[persona]**, I want **[capability]**, so that **[business outcome]**.

**Acceptance Expectations:**
- [Observable outcome 1]
- [Observable outcome 2 / edge case]

**Behavioral Expectations:**
- [System behaviour from user perspective]
- [Error/exception behaviour visible to user]

### US-XX.2 — [Short Story Title] *(if applicable)*

> As a **[persona]**, I want **[capability]**, so that **[business outcome]**.

**Acceptance Expectations:**
- [...]

**Behavioral Expectations:**
- [...]

---

## Dependencies

| | |
|---|---|
| **Depends On** | [F-XX](./F-XX-slug.md), [F-XX](./F-XX-slug.md) — or None |
| **Depended On By** | [F-XX](./F-XX-slug.md) — or None |
| **Shared Services** | [auth service, notification service, audit log, etc.] — or None |

---

## Data Entities

> Conceptual domain entities relevant to this feature. Physical schema decisions (table names, columns, indexes) are deferred to `/feature-to-issues` and governed by `ai-context/database-guidelines.md`.

**Entities Owned by This Feature** *(this feature introduces and is the authoritative source for these entities)*

| Entity | Description | Sensitivity |
|---|---|---|
| [EntityName] | [One-line description] | None / PII / PHI / PCI / Confidential |

**Entity Dependencies** *(this feature reads or references entities owned by other features — no ownership, no physical FK implied)*

| Entity | Owned By | Access Type |
|---|---|---|
| [EntityName] | [F-XX Feature Name] | Read / Write / Subscribe |

---

## Risks & Ambiguities

- ⚠️ [Risk or ambiguity description]

*(None identified)*

---

## Acceptance Validation

- [How a product owner or QA lead would verify this Feature is complete]
- [What observable business outcome confirms delivery]
```

---

### Recommended Next Step

Output one of the following as plain Markdown text based on output quality and HITL flags:

**Option A — No HITL flags:**

> ✅ All features are well-defined. Submit for HITL review, then run `/write-test-plan` followed by `/feature-to-issues`.

**Option B — HITL flags present:**

> ⚠️ The following features require human review before proceeding: **F-XX** ([reason]). After sign-off, run `/write-test-plan` then `/feature-to-issues` on approved features only.

**Option C — PRD clarification needed:**

> ⛔ The following ambiguities must be resolved before decomposition is reliable: [list]. Return to the PRD author for clarification before proceeding.

---

### Phase 2 — Parallel Feature File Generation

**Before spawning agents:**

1. Resolve entity ownership: for each entity, identify exactly one owning feature. If ambiguous, use `AskUserQuestion` first.
2. Collect the connected project folder absolute path.
3. Summarise any constitution context loaded in Step 1 (1–2 sentences per file).

**Spawn one Agent per feature in a single response** so they run in parallel. Each agent prompt must be fully self-contained — sub-agents cannot read the parent conversation.

Use this prompt template for each agent (fill in all placeholders before spawning):

---
```
You are generating a single feature specification file. Use the Write tool to save it and return one confirmation line.

Project folder (absolute path): [PROJECT_FOLDER]
Output file: docs/features/[F-XX-slug].md

Constitution context:
[1-2 line summary of relevant tech/compliance decisions from loaded constitution files, or "None loaded"]

Entity Ownership Map:
| Feature | Entities Owned | Entity Dependencies |
[PASTE FULL TABLE]

Feature data:
- ID: [F-XX]
- Name: [Feature Name]
- Complexity: [Low / Medium / High]
- HITL Required: [Yes — reason / No]
- Business Objective: [objective]
- AI Execution Suitability: [High/Medium/Low — rationale]
- Execution Strategy: [Autonomous / Autonomous with HITL / Human-led]
- In Scope: [bullet list]
- Out of Scope: [bullet list]
- Functional Description: [2–5 sentences]
- User Personas: [Name | Role per row]
- User Stories:
  [US-XX.1 — Title]
  > As a [persona], I want [capability], so that [outcome].
  Acceptance: [list]
  Behavioral: [list]
  [repeat for each story]
- Feature Dependencies: [F-XX links or None]
- Depended On By: [F-XX links or None]
- Shared Services: [list or None]
- Entities Owned by This Feature: [Name | Description | Sensitivity per row]
- Entity Dependencies: [Entity | Owned By | Access Type per row]
- Risks & Ambiguities: [list or None]
- Acceptance Validation: [list]

Generate docs/features/[F-XX-slug].md with this exact Markdown structure:

# [F-XX] — [Feature Name]

**Status:** Draft | **Complexity:** [value] | **HITL Required:** [value]

[← Back to Feature Summary](./feature-summary.md)

---

## Overview
| | |
|---|---|
| **Business Objective** | [value] |
| **AI Execution Suitability** | [value] |
| **Execution Strategy** | [value] |

---

## Scope
**In Scope:**
- [items]

**Out of Scope:**
- [items]

---

## Functional Description
[text]

---

## User Personas
| Persona | Role |
|---|---|
[rows]

---

## User Stories
### [US-XX.1 — Title]
> As a **[persona]**, I want **[capability]**, so that **[outcome]**.

**Acceptance Expectations:**
- [items]

**Behavioral Expectations:**
- [items]

[repeat for each story]

---

## Dependencies
| | |
|---|---|
| **Depends On** | [links or None] |
| **Depended On By** | [links or None] |
| **Shared Services** | [list or None] |

---

## Data Entities

**Entities Owned by This Feature**
| Entity | Description | Sensitivity |
|---|---|---|
[rows]

**Entity Dependencies**
| Entity | Owned By | Access Type |
|---|---|---|
[rows]

---

## Risks & Ambiguities
- [items or *(None identified)*]

---

## Acceptance Validation
- [items]

Use the Write tool to save the file. Reply with exactly: "✅ [F-XX] → docs/features/[F-XX-slug].md"
```
---

Spawn all feature agents at once in a single response. Wait for all confirmations before proceeding.

**After all agents confirm:** proceed to Phase 3.

---

### Phase 3 — Assemble Summary and HITL Checkpoint

Generate `docs/features/feature-summary.md` in the parent context (it links to all feature files just written), then save it to the project folder.

Confirm all saved files to the user:
```
✅ Feature Breakdown Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docs/features/feature-summary.md
docs/features/F-01-[slug].md
docs/features/F-02-[slug].md
[...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then run the HITL checkpoint below.

---

### HITL Feature Review Checkpoint

Use the `AskUserQuestion` tool to interactively collect confirmation before proceeding. Present a **multi-select** question so the user confirms all items in a single interaction.

**Call `AskUserQuestion` with:**
- question: "Please confirm the Feature Breakdown review items that are complete. Select all that apply:"
- multiSelect: true
- options:
  1. All Feature IDs and names are correct and agreed
  2. User Stories accurately represent business intent
  3. Feature scope boundaries are accepted
  4. Dependency ordering is correct
  5. All HITL-flagged features have been reviewed
  6. Execution wave plan is agreed

**If all 6 items are selected:** State "✅ Feature Breakdown Approved." Then instruct the user to run `/write-test-plan` next, followed by `/feature-to-issues`.

**If any items are NOT selected:** List each unconfirmed item, state "⛔ Feature Breakdown requires revision — do not proceed until all items are confirmed.", and halt.

> This is the mandatory HITL gate between Feature planning and Issue generation. Agents assist. Humans approve.
---

## Downstream Compatibility

This skill's output is explicitly designed for compatibility with the following systems:

| System | Compatibility |
|---|---|
| `/feature-to-issues` | ✅ Feature IDs and User Stories are structured for direct ingestion |
| Ralph Loop | ✅ Execution waves and AI Suitability flags support autonomous orchestration |
| GitHub/GitLab Hierarchy | ✅ Feature IDs map to Epic/Milestone level; User Story IDs map to Story level |
| HITL Governance | ✅ HITL flags and recommended next steps support human review gates |
| `/write-prd` output | ✅ Designed to consume structured PRD output from `/write-prd` |

### Parent-Child Traceability Model

```
PRD
 └── Feature (F-XX)               ← This skill produces this layer
      └── User Story (US-XX.N)    ← Embedded within Features by this skill
           └── Issue              ← Produced by /feature-to-issues
                └── Sub-task / PR ← Produced by engineering execution layer
```

Feature IDs (F-XX) and User Story IDs (US-XX.N) must be preserved verbatim by all downstream skills and systems to maintain traceability.

---

## HITL Governance Rules

The following conditions **require** a HITL flag (`HITL Flag: YES`) on a Feature:

1. **Ambiguous Persona** — It is unclear who the user of this Feature is
2. **Conflicting Requirements** — The PRD contains contradictory statements about this capability
3. **External System Dependency** — The Feature requires integration with an external system not fully defined in the PRD
4. **Regulatory or Compliance Risk** — The Feature touches areas with legal, security, or compliance implications
5. **Irreversible Operations** — The Feature includes destructive, financial, or identity-altering operations
6. **Low AI Execution Suitability** — The Feature's complexity or ambiguity makes autonomous decomposition unreliable

When HITL is flagged, Section 5 must recommend **Option B** or **Option C** accordingly.

---

## Quality Standards

Before finalising output, verify:

- [ ] Every Feature has a unique F-XX ID
- [ ] Every User Story has a unique US-XX.N ID
- [ ] Every User Story follows the exact `As a / I want / so that` format
- [ ] Every User Story has both Acceptance Expectations and Behavioral Expectations
- [ ] No Feature contains engineering tasks, code references, or schema definitions
- [ ] All dependencies are expressed as Feature IDs only (no prose)
- [ ] The Dependency Map is consistent with the Feature Breakdown (no orphan IDs)
- [ ] Execution Waves respect the dependency ordering
- [ ] All HIGH-risk Features have a HITL flag
- [ ] Section 5 recommendation is consistent with HITL flags present

If any check fails, self-correct before outputting.

---

## Prohibited Output Checklist

Before finalising, scan output for the following and **remove or escalate** if found:

| Prohibited Content | Action if Found |
|---|---|
| API endpoint paths (`/api/`, `GET`, `POST`) | Remove — belongs to engineering layer |
| Database table or column names | Remove — belongs to engineering layer |
| Component or class names | Remove — belongs to engineering layer |
| Test cases or QA scripts | Remove — belongs to engineering layer |
| GitHub Issue format (`- [ ] task`) | Remove — belongs to `/feature-to-issues` |
| Sprint points or effort estimates | Remove — belongs to delivery management |
| Framework or library names | Remove — belongs to engineering layer |

---

## ID Conventions

| ID Format | Meaning | Example |
|---|---|---|
| `F-01`, `F-02` ... | Feature ID (sequential, padded to 2 digits) | `F-03` |
| `US-01.1`, `US-01.2` ... | User Story within Feature 01 | `US-03.2` |

IDs must be:
- Globally unique within this decomposition
- Preserved verbatim in all downstream artifacts
- Assigned in the order Features are presented (Wave 1 → Wave 2 → Wave 3)
