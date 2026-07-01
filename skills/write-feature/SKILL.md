---
name: write-feature
description: >
  Use this skill when the user types /write-feature or when a clarified feature request, enhancement,
  support-driven change request, or brownfield improvement needs to become a structured Feature document
  with embedded User Stories — without a formal PRD.
  Trigger on /write-feature, "turn this into a feature", "write a feature for", "document this enhancement",
  "convert this requirement into a feature", "structure this request", "create a feature spec for",
  or whenever a grilled requirement is ready for feature documentation but no PRD workflow was followed.
  Step 2 of the Brownfield workflow. Sits between /grill and the HITL Feature Review gate.
  Brownfield workflow: /grill → [/write-feature] → HITL Feature Review → /feature-to-issues → HITL Issue Review → Ready to Develop.
  Use this skill when working in an existing product needing Feature Layer documentation. Do NOT skip to /feature-to-issues.
---

# /write-feature — Brownfield Feature Documentation Skill

## Purpose

Convert a clarified feature request, enhancement, or support-driven change into a structured, enterprise-grade
**Feature document** with embedded **User Stories** — ready for HITL review and downstream issue decomposition.

## Workflow Role

`/write-feature` is **Step 2 of the Brownfield workflow**.

```
BROWNFIELD:  /grill → [/write-feature] → HITL Feature Review
                                         → /feature-to-issues → HITL Issue Review → Ready to Develop

GREENFIELD:  /grill → /write-prd → /prd-to-features → HITL Feature Review
                                                      → /feature-to-issues → HITL Issue Review → Ready to Develop
```

**Input:** Clarified requirement from `/grill` (all blocking questions resolved).
**Output:** Structured Feature document → feeds into HITL Feature Review gate → then `/feature-to-issues`.

**Do not use for greenfield product development.** If a formal PRD is needed, use `/write-prd` instead.

### What This Skill DOES

- Converts clarified requirements into structured Features
- Identifies business purpose, user intent, and impacted personas
- Embeds User Stories with Acceptance and Behavioral Expectations
- Identifies dependencies, impacted modules, and brownfield constraints
- Flags risks, ambiguities, and areas requiring human review
- Produces output compatible with `/feature-to-issues` and the Ralph Loop

### What This Skill MUST NOT DO

| Prohibited Output | Belongs To |
|---|---|
| GitHub/GitLab Issues | `/feature-to-issues` |
| API endpoint contracts | Engineering layer |
| Database schema or migrations | Engineering layer |
| Code-level implementation | Engineering layer |
| Test scripts or QA plans | Engineering layer |
| Sprint assignments or story points | Delivery management |
| PR structure or branch strategy | Engineering layer |

**If you find yourself writing any of the above — stop. You are below the Feature Layer.**

---

## When to Use This Skill

Use `/write-feature` when:

- No formal PRD exists for this change
- Scope is limited to one or a few features within an existing product
- Team is working in a **brownfield** (existing application) context
- Requirement source is: customer request, support ticket, product feedback, or ad-hoc enhancement
- `/grill` has already resolved blocking questions and the requirement is clarified

**Typical examples:**
- "Add low inventory indicator to product catalog"
- "Integrate QuickBooks customer sync"
- "Add vessel emissions dashboard"
- "Enable passwordless login"
- "Add export to Excel option"
- "Show order history on customer portal"

**Do not use this skill if:**
- A full formal PRD is being written → use `/write-prd` instead
- Requirement is not yet clarified → run `/grill` first

---

## Input Format

```
/write-feature [clarified requirement or /grill output]
```

**Example:**
```
/write-feature Add a low inventory warning badge to the product catalog. Show when stock < 10 units. Visible to all authenticated users. Badge must not block purchase flow.
```
> If you've just run `/grill`, the output is already in context — just type `/write-feature` to proceed.

---

## Execution Instructions

### Step 0 — Project Folder Check

Before generating the feature document:

1. Check `<env>` for `User selected a folder`.
   - **If "yes":** Proceed. The project folder is connected.
   - **If "no":** Call `mcp__cowork__request_cowork_directory` to ask the user to select the project folder. Halt if declined.
2. Verify `ai-context/project.json` exists in the project folder. If missing, warn the user that `/write-prd` should be run first to initialise the project structure, but continue if the user confirms.

---

### Step 0 — Assess Input Quality

Before writing anything, evaluate the input.

**Input is sufficient if:**
- A core user need or business problem is identifiable
- At least one user persona can be inferred
- The functional intent is clear enough to describe what the system should do
- At least the primary happy-path behavior can be described

**Input is insufficient if:**
- The request is one sentence with no supporting detail
- Critical questions from a `/grill` run remain unresolved
- The scope is entirely undefined

**If insufficient, halt with:**

```
⛔ Requirement Not Ready for Feature Documentation

The following must be resolved before /write-feature can proceed:
- [List each blocking gap]

Run /grill on this requirement first, then retry /write-feature.
```

**Do not generate a partial Feature. Either proceed fully or halt.**

---

### Step 1 — Silently Extract Context

Before writing output, internally extract:

1. **Core Objective** — What business outcome does this feature achieve?
2. **Personas** — Who uses this? (end users, admins, operators, external systems)
3. **Functional Intent** — What must the system do?
4. **Brownfield Context** — What existing modules, flows, or services are affected?
5. **Scope Boundaries** — What is explicitly in and out of scope?
6. **Dependencies** — What existing services, APIs, or data sources does this touch?
7. **Risks / Ambiguities** — What is unclear, contradictory, or architecturally uncertain?
8. **HITL Triggers** — Are there irreversible operations, compliance concerns, or external integrations?

Do not output Step 1 results. Use them to drive the Feature document.

---

### Step 2 — Write the Feature Document

Use the **strict output template** below. Every section is mandatory.
Do not skip, merge, reorder, or abbreviate sections.

---

### Step 3 — Self-Review Before Output

Before finalising, verify:

- [ ] No engineering tasks, schema, endpoints, or code have been included
- [ ] Every User Story follows the exact `As a / I want / so that` format
- [ ] Every User Story has both Acceptance Expectations and Behavioral Expectations
- [ ] Brownfield impacts are explicitly identified (no silent assumptions)
- [ ] All ambiguities are surfaced — none are silently resolved
- [ ] HITL flag is set if any HITL trigger condition is present
- [ ] Recommended Next Step is consistent with HITL flags

If any check fails, self-correct before outputting.

---

## Output Template (Strict)

Produce the following output exactly. Do not skip or reorder sections.

---

```
═══════════════════════════════════════════════════════════════
FEATURE DOCUMENT
Skill: /write-feature
Source Requirement: [One-line summary of input]
Generated: [Today's date]
═══════════════════════════════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — FEATURE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature ID              : FEAT-001
Feature Name            : [Concise business capability name]
Feature Type            : [Enhancement | Integration | Workflow Change | UI Improvement |
                           Reporting | Infrastructure Capability | Other: ___]
Execution Complexity    : [Low | Medium | High]
AI Execution Suitability: [High | Medium | Low]
Delivery Approach       : [Agent-friendly | Human-heavy | Sequential | Parallel]
HITL Required           : [YES — reason | NO]
Downstream Skill        : /feature-to-issues

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — FEATURE DETAIL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────┐
│ FEATURE FEAT-001
└─────────────────────────────────────────────────────────────┘

Feature Objective
─────────────────
[One sentence: what business goal does this Feature achieve?]

Business Context
────────────────
[2–4 sentences: background, problem being solved, and why it matters now.
 Write from a product perspective. No technical implementation.]

Scope
─────
IN SCOPE:
  - [Capability or behaviour included in this Feature]
  - [...]

OUT OF SCOPE:
  - [What this Feature explicitly does NOT cover]
  - [...]

> Out of Scope items must be explicit. Do not leave scope to inference.

Functional Description
──────────────────────
[3–6 sentences describing the Feature from a product perspective.
 Describe what the system does, for whom, and under what conditions.
 No technical implementation. No code. No schema. No endpoints.]

Personas Impacted
─────────────────
  - [Persona Name]: [Brief role description and how they interact with this feature]
  - [...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — USER STORIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Repeat the block below for each User Story. Minimum 1. Include one per persona or distinct use case.]

  [US-001.1]
  As a [persona], I want [capability], so that [business outcome].

  Acceptance Expectations:
    - [Observable outcome that confirms the story is satisfied]
    - [Edge case or boundary condition if relevant]
    - [Error or rejection condition if applicable]

  Behavioral Expectations:
    - [How the system behaves from the user's perspective]
    - [What the user sees, receives, or experiences]
    - [Error or exception behavior visible to the user]

  [US-001.2] (add more as needed)
  As a [persona], I want [capability], so that [business outcome].

  Acceptance Expectations:
    - [...]

  Behavioral Expectations:
    - [...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — DEPENDENCIES & BROWNFIELD IMPACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Existing Modules Impacted
─────────────────────────
  - [Module/Service Name]: [Nature of impact — read, write, extend, replace, or integrate]
  - [...]
  (or "None identified — isolated new capability")

Shared Services Required
────────────────────────
  - [Authentication | Notification Service | Reporting Service | Audit Log | ...]
  - [...]
  (or "None")

Backward Compatibility Concerns
────────────────────────────────
  - [Any existing workflow, data format, or user behavior that must not break]
  - [...]
  (or "None identified")

Regression Risk Areas
─────────────────────
  - [Area of the system most likely to be inadvertently affected]
  - [...]
  (or "None identified")

External Dependencies
─────────────────────
  - [Third-party service, API, or data source required]
  - [...]
  (or "None")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5 — RISKS, AMBIGUITIES & GOVERNANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Risks / Ambiguities
───────────────────
  ⚠ [Risk or ambiguity — be specific; do not write "unclear requirements"]
  ⚠ [...]
  (or "None identified")

HITL Flag
─────────
  [YES — Reason: ___]
  [NO]

HITL Trigger Conditions Present (check all that apply):
  [ ] Ambiguous persona or ownership
  [ ] Conflicting or contradictory requirements
  [ ] External system integration not fully defined
  [ ] Regulatory, compliance, or security implication
  [ ] Irreversible or destructive operation
  [ ] Architectural uncertainty requiring review
  [ ] Low AI execution suitability

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6 — EXECUTION GUIDANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Engineering Complexity    : [Low | Medium | High]
AI Execution Suitability  : [High | Medium | Low — with one-line rationale]
Suggested Execution Strategy : [Autonomous | Autonomous with HITL checkpoint | Human-led]

Suggested Acceptance Validation
────────────────────────────────
  - [How a product owner or QA lead would verify this Feature is complete]
  - [What observable business outcome confirms delivery]
  - [...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7 — RECOMMENDED NEXT STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Choose EXACTLY ONE of the following:]

OPTION A — READY FOR HITL FEATURE REVIEW
─────────────────────────────────────────
  This Feature is well-defined, scoped, and suitable for human review.
  No blocking HITL flags are present. All User Stories have sufficient clarity.
  Next step: Submit this Feature document for HITL Feature Review.
  After approval: Run `/feature-to-issues` — the Feature document is already in context.

OPTION B — REQUIRES HITL FEATURE REVIEW (Flagged Items)
─────────────────────────────────────────────────────────
  This Feature contains one or more items requiring human review before issue decomposition.
  Flagged items:
    - [Specific item requiring review — be concrete]
    - [...]
  Action: Review flagged items with product owner or architect, then proceed to /feature-to-issues
          once items are resolved.

OPTION C — REQUIRES REQUIREMENT CLARIFICATION
───────────────────────────────────────────────
  The following ambiguities are too significant for safe decomposition:
    - [Specific unresolved question]
    - [...]
  Action: Return to the requester for clarification. Run /grill if not already done.
          Then retry /write-feature with the clarified requirement.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HITL FEATURE REVIEW CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before proceeding to /feature-to-issues, a human reviewer must confirm:

| # | Review Item | Status |
|---|-------------|--------|
| 1 | Feature name and objective are accurate | ☐ Approved / ☐ Needs Revision |
| 2 | Business context accurately reflects the requirement | ☐ Approved / ☐ Needs Revision |
| 3 | Scope (in/out) is agreed | ☐ Approved / ☐ Needs Revision |
| 4 | User Stories represent real business intent | ☐ Approved / ☐ Needs Revision |
| 5 | Impacted modules and dependencies are identified | ☐ Approved / ☐ Needs Revision |
| 6 | Risks and ambiguities are acknowledged | ☐ Approved / ☐ Needs Revision |

Status: ☐ Feature Approved — proceed to /feature-to-issues
        ☐ Requires Revision — do not proceed until revised and re-reviewed

> This is the mandatory HITL gate between Feature documentation and Issue generation.
> Agents assist. Humans approve.

═══════════════════════════════════════════════════════════════
END OF FEATURE DOCUMENT
═══════════════════════════════════════════════════════════════
```

---

## HITL Governance Rules

The following conditions **require** `HITL Flag: YES`:

1. **Ambiguous Persona** — It is unclear who the primary user of this Feature is
2. **Conflicting Requirements** — The request contains contradictory statements
3. **External System Dependency** — Integration with a third-party system not fully defined
4. **Regulatory / Compliance Risk** — Touches legal, security, privacy, or audit-sensitive areas
5. **Irreversible Operation** — Feature includes destructive, financial, or identity-altering actions
6. **Architectural Uncertainty** — Impacts on existing system are unclear or potentially breaking
7. **Low AI Suitability** — Complexity or ambiguity makes autonomous decomposition unreliable

When HITL is flagged, Section 7 **must** recommend Option B or Option C.

---

## Brownfield Awareness Rules

Apply these rules when working in existing product contexts:

1. **Never assume isolated delivery** — Explicitly identify every module or service this feature touches
2. **Preserve existing behavior** — Flag any scenario where existing workflows could be disrupted
3. **State backward compatibility status** — Do not leave compatibility to inference
4. **Surface regression risk** — Name the areas most likely to be inadvertently broken
5. **Flag architectural review triggers** — Any change to shared services, data contracts, or auth flows requires HITL

---

## User Story Rules

| Rule | Requirement |
|---|---|
| Format | Exact: `As a [persona], I want [capability], so that [business outcome].` |
| Persona | Must be named and traceable to a real role — not "user" or "person" |
| Want clause | Describes a business action — not a technical implementation |
| So that clause | States a business value — not a system behavior |
| Acceptance Expectations | Observable outcomes — what can be seen, tested, or measured |
| Behavioral Expectations | System behavior from the user's perspective — including errors |
| Prohibited content | No database tables, API endpoints, component names, or framework references |

---

## Quality Checklist (Self-Review Before Output)

- [ ] Every section of the template is present and populated
- [ ] FEAT-001 ID assigned (increment if multiple features in one run: FEAT-002, etc.)
- [ ] Every User Story uses the exact `As a / I want / so that` format
- [ ] Every User Story has both Acceptance Expectations and Behavioral Expectations
- [ ] No engineering tasks, endpoints, schemas, or code are present anywhere
- [ ] Brownfield impact section is populated — not left as "N/A" without justification
- [ ] All ambiguities are surfaced — none silently resolved
- [ ] HITL flag is set if any trigger condition is present
- [ ] Section 7 Recommended Next Step matches the HITL flag state
- [ ] Output is self-contained and ready for handoff to a human reviewer or `/feature-to-issues`
- [ ] Feature document saved to `docs/features/<FEAT-ID>-<slug>.md` in the connected project folder

---

## Prohibited Output Checklist

Scan the output before finalizing. Remove anything matching:

| Prohibited Content | Action |
|---|---|
| API endpoint paths (`/api/`, `GET`, `POST`) | Remove — engineering layer |
| Database table or column names | Remove — engineering layer |
| Component, class, or function names | Remove — engineering layer |
| Test cases, scripts, or QA checklists | Remove — engineering layer |
| GitHub Issue format (`- [ ] task`) | Remove — `/feature-to-issues` layer |
| Sprint points, effort estimates, T-shirt sizing | Remove — delivery management |
| Framework or library names (React, .NET, etc.) | Remove — engineering layer |

---

## Downstream Compatibility

This skill's output is designed for direct consumption by:

| System | Compatibility |
|---|---|
| `/feature-to-issues` | ✅ Feature ID, User Story IDs, and Acceptance Expectations structured for direct ingestion |
| Ralph Loop | ✅ AI Execution Suitability and Delivery Approach flags support orchestration decisions |
| GitHub/GitLab hierarchy | ✅ Feature ID maps to Epic/Milestone; User Story IDs map to Story level |
| HITL Governance | ✅ HITL flag and Recommended Next Step support human review gates |
| `/write-prd` workflow | ✅ Output structure mirrors `/prd-to-features` Feature Layer for consistency |

### Traceability Model

```
Raw Requirement
 └── /grill (clarification)
      └── Feature (FEAT-XXX)               ← This skill produces this layer
           └── User Story (US-XXX.N)       ← Embedded within Features by this skill
                └── Issue                  ← Produced by /feature-to-issues
                     └── Sub-task / PR     ← Produced by engineering execution layer
```

Feature IDs (`FEAT-XXX`) and User Story IDs (`US-XXX.N`) must be preserved verbatim by all downstream
skills and systems to maintain end-to-end traceability.

---

## ID Conventions

| ID Format | Meaning | Example |
|---|---|---|
| `FEAT-001`, `FEAT-002` | Feature ID (sequential, zero-padded to 3 digits) | `FEAT-003` |
| `US-001.1`, `US-001.2` | User Story within Feature 001 | `US-002.3` |

IDs must be:
- Globally unique within this feature document
- Assigned sequentially in order of appearance
- Preserved verbatim in all downstream artifacts
