---
name: grill
description: >
  Use this skill when the user types /grill followed by any idea, feature request, user story, or vague requirement.
  This skill interrogates incomplete or ambiguous ideas BEFORE any PRD, design, or development begins — through an
  interactive dialogue, one question at a time, with selectable options wherever possible.
  Trigger on /grill, or any variation like "grill this idea", "interrogate this requirement", "clarify this feature",
  "is this ready for dev?", or "what am I missing?". Also trigger when a user shares a rough feature brief and
  clearly needs to think it through before writing a PRD or feature spec.
  This is Step 1 in BOTH the Greenfield workflow (→ /write-prd) and the Brownfield workflow (→ /write-feature).
---

# /grill — Interactive Requirement Interrogation

## Workflow Role

`/grill` is **Step 1** in all planning workflows:

| Flow | Path After /grill |
|---|---|
| **Greenfield** (new product/module, large scope) | → `/write-prd` → `/prd-to-features` → `/feature-to-issues` |
| **Brownfield** (existing app, enhancement) | → `/write-feature` → `/feature-to-issues` |

---

## Purpose

Interactively interrogate a vague or partially defined idea — one question at a time — until it reaches
**developer-level clarity**: the point where a developer can start building without needing to ask a single
clarifying question.

**This skill never generates solutions, code, or architecture. It only asks questions and records answers.**

---

## How It Works

This is a **conversational interrogation loop**, not a document dump.

1. Parse the requirement. Silently identify every unknown and ambiguity.
2. Prioritize the unknowns — tackle the ones that block the most downstream decisions first.
3. Ask **one question at a time** (or a tight cluster of 2-3 that are tightly related).
4. For questions with a bounded answer space, **offer selectable options** using the `AskUserQuestion` tool (in Cowork) or a numbered list (in Claude Code / text environments).
5. Listen to the answer. Update your internal model of the requirement. Identify the next unknown.
6. Repeat until developer-level clarity is reached — no artificial limit on number of questions.
7. When clarity is reached, produce a **Clarity Summary** and recommend the next skill.

---

## Execution

### Step 1 — Load Context (silently, before asking anything)

Attempt to load these files. If missing, continue without them and note the gap internally.

- `/agents.md` — routing and agent roles
- `/ai-context/architecture.md` — system boundaries and service topology
- `/ai-context/tech-stack.md` — stack constraints (React/TypeScript, .NET Core, SQL Server, Playwright)

### Step 2 — Parse and Summarize

Before asking any questions, output a brief **Understanding Summary** — 2–4 sentences restating the idea
neutrally and precisely. Highlight any language that is already ambiguous even in the restatement.
Make clear what you understood and what you're about to dig into.

Keep this short. Don't generate sections, tables, or structured output yet — that comes at the end.

### Step 3 — Interrogation Loop

Begin asking questions. Follow these principles:

**One at a time (usually).** Ask the single most important open question. Occasionally, group 2–3 questions
that are tightly coupled and meaningless to separate (e.g., "What format?" and "Who triggers the export?"
are separate; "Does the user confirm before submitting?" and "What happens after they confirm?" can travel together).

**Offer options wherever the answer space is bounded.** If the question has a finite set of reasonable answers,
present them as choices. Always include an "Other / something else" escape hatch. Examples where options help:
- Delivery mechanism: synchronous download / async email / in-app notification / TBD
- User roles that can trigger this: all authenticated users / admins only / account owners / role-based
- Data format: CSV / JSON / Excel / PDF / user-configurable

**Don't offer options when the answer is genuinely open-ended.** For questions like "What data entities
should be exportable?", free text is right.

**How to offer options (environment-aware):**

In Cowork (when the `AskUserQuestion` tool is available):
- Use `AskUserQuestion` with `multiSelect: false` for single-choice questions
- Use `AskUserQuestion` with `multiSelect: true` for multi-select questions
- Use a plain text question in your response for free-form answers

In Claude Code / text environments:
- Present options as a numbered list and ask the user to reply with the number(s) or type their own answer

**Track what you've learned.** Maintain an internal running picture of the requirement as answers come in.
Use each answer to inform which question is most valuable next. Don't ask questions that the user's previous
answers have already resolved.

**No minimum, no maximum.** Ask as many questions as it takes. Don't stop early because you've hit some
arbitrary section count. Don't pad if clarity has been reached.

**Quality bar for every question:**
> *"Could a developer make a wrong implementation decision if this goes unanswered?"*
>
> If yes → ask it. If no → skip it.

### Step 4 — Clarity Check

After each answer, silently evaluate:

> Have we reached developer-level clarity? That means a dev could open a ticket and start building
> without asking a single question about:
> - What to build (scope and behavior)
> - Who it's for (roles and permissions)
> - How it handles edge cases and failures
> - How it fits with existing services and data
> - How it will be tested

If the answer is no, identify the next unknown and continue the loop. If yes, move to Step 5.

You can also check in with the user periodically: *"I think we're getting close — do you want to add
anything, or shall I wrap up the summary?"*

### Step 5 — Clarity Summary

Once clarity is reached, output a structured **Clarity Summary** that captures everything learned.
This document becomes the input for the next skill.

---

## Clarity Summary Format

Use this exact structure:

## Clarity Summary: [Feature Name]

### What We're Building
[1-3 sentence precise description of the feature, grounded in the answers given]

### In Scope
- [Explicitly confirmed items]

### Out of Scope
- [Explicitly ruled out, or deferred to a later phase]

### User Roles & Permissions
- [Who can do what, as confirmed]

### Key Functional Behaviors
- [Confirmed behaviors, rules, and outcomes]

### Edge Cases & Error Handling
- [Confirmed handling for each edge case discussed]

### State Matrix (omit this section if no entity in scope has more than one state)
- [Entity/actor with multiple states — list the states]
- [For each relevant cross-product of entity state × actor state × entry point discussed,
  one row: Combination → Confirmed behavior]
- [Any UI component's confirmed loading/empty/error states and dismissal triggers, if applicable]

### Data & State
- [What data is involved, where it lives, retention, ownership]

### Integration Points
- [Services, APIs, or systems this touches]

### Testing Notes (Playwright)
- [Key scenarios that must be E2E tested, as identified during the conversation]

### Open Items (if any)
- [Anything still unresolved — flag these as blockers before proceeding]

### Recommended Next Step
[Greenfield → /write-prd | Brownfield → /write-feature]
Reason: [Why this routing was chosen]
Command: `/write-prd` or `/write-feature` — the Clarity Summary above is already in context, no need to paste it.

---

## Question Categories to Draw From

Use these as a mental checklist of domains to cover. Only ask where there are real unknowns.

- **Functional behavior** — What should the system do? Rules, outcomes, state transitions.
- **User roles & workflows** — Who triggers this? What's the end-to-end flow? Permission boundaries?
- **Edge cases & failure modes** — Concurrent access, empty states, partial failures, timeouts, invalid input.
- **Entity lifecycle & state matrix** — For every entity or actor with more than one state (e.g. session:
  valid/expired, account: active/pending-deletion, integration: connected/revoked), don't stop at the
  primary state. Ask what happens for the *cross-product* of (entity state × actor state × entry point) —
  e.g. "what happens when a user with a pending account deletion tries to sign in after their session has
  expired?" A feature description that only covers the happy-path state combination is not yet clear.
- **UI component contract** (when the feature includes interactive or overlay UI — dropdowns, panels,
  modals, forms) — For every new interactive/overlay element, confirm: its loading state, its empty
  state, its error state, and *every* way it can be dismissed (an explicit close control, Escape, clicking
  outside it, and what happens immediately after a selection is made). Don't let "it closes" go unasked —
  ask which of those triggers apply.
- **Third-party contract verification** — When a feature depends on a specific capability of an external
  API (a filter parameter, a text-search behavior, which host serves which endpoint, a rate/tier limit),
  ask explicitly whether that capability has been checked against real documentation or a spike — not
  assumed from the API's general purpose. If unverified, it must be flagged as a blocking Open Item in the
  Clarity Summary, not silently treated as available.
- **Technical constraints** — API boundaries, microservice ownership, SQL Server, .NET Core / React+TypeScript.
- **Integration points** — External systems, internal services, third-party dependencies, notification pipelines.
- **Data & state** — What data is created/mutated/deleted? Who owns it? Retention, sync, audit trail.
- **Scale & growth** — Expected user count, concurrent users, data volume at launch and in 2–3 years, peak load patterns (burst vs. steady). Do you have existing data or legacy systems that need to be migrated INTO this system?
- **Data sensitivity & compliance** — Does this feature handle PII, PHI, PCI, or other regulated data? Applicable frameworks (HIPAA, GDPR, SOC 2, PCI-DSS)? Encryption requirements (at rest, in transit)? Audit trail requirements? Data residency or localization constraints? Retention and deletion policies?
- **Testing** — Essential Playwright scenarios. What requires mocking or cross-service coordination?

---

## Rules

**Never:**
- Dump all questions at once
- Generate solutions, code, or architecture
- Make silent assumptions — surface them and ask
- Ask generic questions ("What is the goal?" is too broad)
- Answer your own questions
- Stop before developer-level clarity is reached just because you've asked "enough" questions

**Always:**
- Ask one question at a time (with rare exceptions for tightly coupled pairs)
- Offer selectable options when the answer space is bounded
- Track answers and reprioritize remaining unknowns as you go
- Reference Playwright explicitly when discussing testing
- End with a Clarity Summary and a routing recommendation
