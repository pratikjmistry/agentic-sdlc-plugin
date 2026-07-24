---
name: design-ui
description: >
  Use this skill when the user types /design-ui or wants to design the UI/UX for an approved Feature
  Breakdown before issues are created — screens, navigation, layout, and visual style, derived from
  User Stories rather than personal taste. Trigger on: "/design-ui", "design the UI", "design the
  interface", "design the layout", "create UI mockups", "design the control plane", "design the
  navigation", "generate UI options", "how should this look", "design the screens", "wireframe this",
  or any request to define the visual/interaction design of a product before implementation issues
  are generated. Elicits design preferences (colors, typography, iconography, layout, navigation) via
  an adaptive interview, generates 2-3 low-fidelity structural layout options for the user to pick or
  merge, then applies the approved style to produce polished HTML mockups and a screen/component
  inventory. Step 3.75 of the Greenfield workflow: /write-test-plan → HITL Test Plan Review →
  [/design-ui] → HITL UI Design Review → /feature-to-issues → Ready to Develop.
---

# /design-ui — UI Design Elicitation and Mockup Generator

## Workflow Role

`/design-ui` is **Step 3.75 of the Greenfield workflow** — inserted after HITL Test Plan Review and before `/feature-to-issues`.

```
GREENFIELD:
  /grill → /write-prd → /generate-project-constitution → /prd-to-features
    → HITL Feature Review → /write-test-plan → HITL Test Plan Review
    → [/design-ui] → HITL UI Design Review
    → /feature-to-issues → HITL Issue Review → Ready to Develop
```

**Input:** Approved Feature Breakdown (`docs/features/*.md` — screens are derived from User Stories and
their Acceptance/Behavioral Expectations) + `ai-context/test-plan.md` (informational only — critical
user journeys hint at which screens matter most; never dictates a visual or structural decision) +
`ai-context/project-constitution.md` / `ai-context/tech-stack.md` (frontend framework, existing design
tokens) + a scan of the connected project folder for an existing design system.

**Output:** `docs/design/ui-design.md` (screen inventory, component inventory, navigation map, captured
design preferences) + `docs/design/mockups/*.html` (rendered HTML/CSS mockups) + an identical copy at
`ai-context/ui-design.md` so `/feature-to-issues` can read it at its expected path.

**Why here:** Screens and navigation must be settled before Frontend issues can be atomic — a UI-layer
issue like "build the dashboard" is not executable without knowing what the dashboard contains and how
it's laid out. Placing this step after the test plan (so it stays out of the implementation-independent
test-writing process) but before issue creation (so issues can reference concrete screen/component IDs)
mirrors why `/write-test-plan` sits where it does.

**What this skill does NOT do:**
- Does not replace a full brand-identity or design-system engagement — if the project needs
  professional visual-brand work or Figma-based designer handoff, treat this skill's output as the
  starting draft, not the final polish.
- Does not produce production-ready application code — mockups are static HTML/CSS for review and
  issue-scoping. The actual frontend implementation (in the project's real framework/component library)
  is `/feature-to-issues` → Ralph-impl's job.
- Does not invent brand-critical decisions (primary brand color, logo, product name styling) without
  either scan evidence or explicit user input. If genuinely unspecified, ask — never guess.

---

## Core Principle: Screens Derive from User Stories, Layout Is Separate from Style

Every screen in this design traces back to a User Story's Acceptance or Behavioral Expectations — a
screen that cannot be justified by a User Story is either scope creep or a sign a User Story is missing.

**Layout (structure) and style (color/type/iconography) are resolved in separate steps, deliberately.**
Design is subjective, and bundling both into a single generated option forces the user to accept or
reject a whole page at once — reject the palette, lose the nav decision too. Splitting them means each
round of feedback is cheap and precise: pick a layout structure first, apply style second.

---

## Execution Protocol

### Step 0 — Project Folder Setup and Context Load

Confirm a project folder is connected (same check as `/write-prd` Step 0a — if not connected, call
`mcp__cowork__request_cowork_directory` and wait for confirmation).

Load, in order:
1. `docs/features/feature-summary.md` and every `docs/features/F-XX-*.md` — **mandatory**. If absent,
   halt with:
   ```
   ⛔ INSUFFICIENT INPUT
   No approved Feature Breakdown found at docs/features/.
   Run /prd-to-features (and complete HITL Feature Review) before /design-ui.
   ```
2. `ai-context/test-plan.md` — extract E2E-/smoke scenarios only, as a signal for which screens are
   highest-priority. Do not let this file drive any structural or visual decision.
3. `ai-context/project-constitution.md` and `ai-context/tech-stack.md` — extract frontend
   framework/library (React, Vue, etc.) so mockups can later be described in terms the implementer
   will recognize.
4. `ai-context/coding-standards.md` — note any stated component or naming conventions.

Note any missing optional file (2–4) and proceed; only file 1 blocks.

**Then scan the project folder** for evidence of an existing design system: Tailwind/CSS config files,
`:root` CSS custom properties, an existing component library directory (e.g. `components/ui`,
`src/design-system`), Storybook config, existing brand assets (logo, favicon, manifest colors). Record
what is found — this pre-fills Step 1 and avoids re-asking for decisions the project already made.

---

### Step 1 — Design Preference Elicitation

**1a — Report scan findings first.** State plainly what was found (e.g. "Found a Tailwind config with
`primary: #1E40AF` and an existing `components/ui` library using shadcn/ui conventions") or "No existing
design system detected — this will be a from-scratch style pass."

**1b — Ask only for what scan evidence didn't already answer.** Use `AskUserQuestion` (max 4 questions
per call — split across two calls if needed). Skip any question fully answered by the scan; state what
you're skipping and why.

1. **Brand color(s)** — free text (hex values, or "use the existing tokens found above")
2. **Typography** — free text (existing tokens, a named font, or "use system font stack")
3. **Iconography** — options: *Use existing icon set found* / *Lucide* / *Heroicons* / *Phosphor* /
   *Other (describe)*
4. **Layout leaning** (a starting bias, not a final answer — Step 3 still generates real options) —
   options: *Sidebar-first* / *Top-nav* / *Command-palette-first* / *No preference, show me options*
5. **Theming** — options: *Light only* / *Dark only* / *Both, with a toggle* / *Not sure yet*
6. **Reference anchor** — free text: "Should this feel like a specific product you already know?
   (e.g. Linear, Stripe, Notion, or your own product)" — this single question often resolves more
   ambiguity than several narrow style questions combined.

Do not proceed to Step 2 until every question has an answer or an explicit skip-with-reason.

---

### Step 2 — Screen and Component Inventory (Structural Layer)

For each Feature (F-XX) and each of its User Stories, derive the screens/views required to satisfy that
story's Acceptance and Behavioral Expectations.

**A screen is a distinct navigable view** (has its own route/entry point). A modal, drawer, or dialog is
a **state of its parent screen**, not a separate screen, unless it is independently navigable.

For each screen, capture:

```
SCR-[NNN]: [Screen Name]
Owning Feature(s) : F-XX [, F-XX]
User Stories       : US-XX.N [, US-XX.N]
Purpose            : [One sentence — what this screen lets the user do]
States             : Empty | Loading | Error | Populated | [feature-specific state, e.g. "Pending approval"]
Primary Actions    : [What a user can do from this screen]
Data Displayed     : [What information appears, in conceptual terms — no field-level schema]
```

Then identify **shared/reusable components** that appear across more than one screen (navigation shell,
data table pattern, form pattern, card pattern, empty-state pattern):

```
CMP-[NNN]: [Component Name]
Used On    : SCR-[NNN], SCR-[NNN]...
Purpose    : [One sentence]
```

Finally, build a **Navigation / IA Map** — the hierarchy of screens and how a user moves between them
(entry points, primary nav destinations, drill-down paths). Render this as an indented list or simple
tree; no HTML yet.

**This step must not reference colors, fonts, or icons.** If you find yourself writing a hex code or a
font name here, stop — that belongs in Step 1/Step 5, not the structural inventory.

---

### Step 3 — Generate Layout Options (Low-Fidelity, Structural Only)

Identify the **layout-defining screen(s)**: usually the primary authenticated shell (dashboard, control
plane, main workspace) plus any screen that is unusually data-dense or multi-panel. Most other screens
will simply inherit whatever pattern is chosen here — you do not need multiple options per screen.

For each layout-defining screen, produce **2–3 structurally distinct concepts**:
- Real, valid, renderable HTML files — grayscale, neutral borders, labeled regions (e.g. "Nav",
  "Content", "Detail Panel"). No color, font, or icon decisions yet — that is what makes these cheap to
  compare and cheap to discard.
- Each concept must represent a genuinely different structural approach (e.g. Concept A: sidebar nav +
  single content pane; Concept B: top nav + tabbed sections; Concept C: command-palette-first with
  minimal persistent chrome) — not the same layout with cosmetic HTML differences.

Save each as `docs/design/mockups/layout-option-[a|b|c].html`.

---

### Step 4 — HITL Layout Selection Checkpoint

Present the concepts via `AskUserQuestion` (single-select unless genuinely comparing independent
layout-defining screens, in which case one question per screen):

- question: "Which layout structure fits best? (You can also describe a merge — e.g. 'nav from A, content density from B' — using Other.)"
- options: one per concept, each with a `description` summarizing its structural approach and a
  `preview` containing a compact text/HTML sketch of the region layout. Always include a path pointer
  to the saved file for full inspection.

**If the user selects a merge or describes one via free text:** restate the merged structure in one
sentence and get an explicit confirmation before proceeding — do not silently interpret an ambiguous
merge request.

**If the user rejects all options:** ask one open question about what's missing, generate one more
round of concepts addressing it, and re-present. Do not proceed past two rounds without escalating —
if still unresolved, ask the user to describe the layout directly in free text.

---

### Step 5 — Apply Visual Style and Render Polished Mockups

Using the Step 1 preferences and the Step 4 selected/merged layout, produce fully styled HTML/CSS
mockups:

- Regenerate the layout-defining screen(s) first, now with real color/typography/iconography applied.
- Then render mockups for the remaining screens from the Step 2 inventory that are highest-complexity
  or highest-visibility, following the same layout pattern for consistency. **Cap at 8 screens total**
  for this pass (matching the discipline used elsewhere in this plugin for smoke-test scope) — note any
  skipped screens explicitly in the Step 6 summary. Skipped screens still have a full structural entry
  from Step 2, which is enough for `/feature-to-issues` to scope an atomic Frontend issue even without a
  rendered mockup.
- All mockups share one stylesheet (`docs/design/mockups/style.css`, linked from every mockup file) so
  they read as one coherent system rather than N unrelated pages.
- For any preference left unspecified in Step 1, use design judgment for non-brand-critical choices
  (spacing, minor layout polish) but **never invent a brand-critical decision** (primary color, tone) —
  loop back to a targeted `AskUserQuestion` instead.

Save each screen mockup to `docs/design/mockups/[SCR-NNN]-[slug].html`.

---

### Step 6 — Write the UI Design Document

Compose `docs/design/ui-design.md`:

```markdown
# UI Design — [Project Name]

**Generated:** [YYYY-MM-DD] | **Skill:** `/design-ui` | **Status:** Draft — Awaiting HITL Review

---

## Design Preferences

| | |
|---|---|
| **Color palette** | [captured values or token reference] |
| **Typography** | [captured value] |
| **Iconography** | [captured choice] |
| **Theming** | [Light / Dark / Both] |
| **Reference anchor** | [product named, or "None given"] |
| **Selected layout pattern** | [Concept name/merge description from Step 4] |

---

## Navigation & IA Map

[Tree/indented list from Step 2]

---

## Screen Inventory

| Screen ID | Name | Feature(s) | States | Mockup |
|---|---|---|---|---|
| SCR-001 | [Name] | F-XX | Empty, Loading, Populated | [Link](./mockups/SCR-001-slug.html) / *structural only* |

---

## Component Inventory

| Component ID | Name | Used On | Purpose |
|---|---|---|---|
| CMP-001 | [Name] | SCR-001, SCR-003 | [purpose] |

---

## Screen Detail

### SCR-001 — [Screen Name]

**Owning Feature(s):** F-XX | **User Stories:** US-XX.N
**Purpose:** [sentence]
**States:** [list]
**Primary Actions:** [list]
**Data Displayed:** [list]
**Mockup:** [Link](./mockups/SCR-001-slug.html) *(or "Structural inventory only — not mocked in this pass")*

[Repeat per screen]
```

**Save to both:**
1. `docs/design/ui-design.md` (human-readable, version-controlled with project docs)
2. `ai-context/ui-design.md` (identical copy, so `/feature-to-issues` can read it at its expected path)

Output a summary:

```
✅ UI Design Generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Saved to: docs/design/ui-design.md  |  ai-context/ui-design.md
Mockups:  docs/design/mockups/ ([N] screens rendered, [N] structural-only)

Screens    : [N]  (across [N] features)
Components : [N] shared components identified
Layout     : [selected/merged concept]

Skipped from mockup pass (structural inventory only): [SCR-IDs, or "None"]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Step 7 — HITL UI Design Review Checkpoint

Use the `AskUserQuestion` tool. Present a **multi-select** question so the user confirms all items in a
single interaction.

**Call `AskUserQuestion` with:**
- question: "Please confirm the UI Design review items that are complete. Select all that apply:"
- multiSelect: true
- options:
  1. Screen inventory covers every User Story's needed views
  2. Navigation/IA map matches the expected user flows
  3. Selected layout pattern (including any merge) is approved
  4. Color palette, typography, and iconography match brand expectations
  5. Mockups accurately reflect the approved layout and style
  6. Component inventory has no obvious missing shared components
  7. Theming choice (light/dark/both) is correctly reflected

**If all 7 items are selected:** State "✅ UI Design Approved." Then instruct the user to run
`/feature-to-issues`.

**If any items are NOT selected:** List each unconfirmed item, state "⛔ UI Design requires revision —
do not proceed until all items are confirmed.", and halt.

> This is the mandatory HITL gate between UI design and issue generation. Agents assist. Humans approve.

Next step: `/feature-to-issues`
(When running `/feature-to-issues`, UI-layer issues should reference the Screen ID / Component ID and
mockup path from this document.)

---

## ID Conventions

| Prefix | Type | Format |
|--------|------|--------|
| `SCR-` | Screen (distinct navigable view) | `SCR-001`, `SCR-002`… |
| `CMP-` | Shared/reusable component | `CMP-001`, `CMP-002`… |

Zero-padded to 3 digits, globally unique within this design document. Downstream artifacts
(`/feature-to-issues`, PR descriptions) must reference these IDs verbatim to maintain traceability.

---

## Design Guardrails

### NEVER
- Invent a brand-critical decision (primary color, logo treatment, tone) without scan evidence or
  explicit user input — ask instead of guessing.
- Skip Step 3's multi-option generation for the layout-defining screen(s), even under time pressure —
  presenting a single generated layout as if it were the only option defeats the purpose of this skill.
- Mix layout (structural) and style (visual) decisions into the same round of options — Step 3 stays
  grayscale; color/type/icons apply only from Step 5 onward.
- Derive a screen from anything other than a User Story's Acceptance or Behavioral Expectations — a
  screen with no traceable story is scope creep; flag it instead of quietly including it.
- Silently interpret an ambiguous "merge these layouts" request — restate and confirm first.

### ALWAYS
- Report existing design-system scan findings before asking questions that evidence already answers.
- Trace every screen to at least one Feature ID and User Story ID.
- Cap the styled-mockup pass at 8 screens and explicitly list what was skipped.
- Save both `docs/design/ui-design.md` and `ai-context/ui-design.md`.
- End every run with the HITL UI Design Review Checkpoint.

---

## Downstream Compatibility

| System | Compatibility |
|---|---|
| `/feature-to-issues` | ✅ Screen IDs, Component IDs, and mockup paths are structured for direct reference in UI-layer child issues |
| `/write-test-plan` | ➖ No dependency — test plan is written before this skill and must remain implementation-independent |
| Ralph-impl | ✅ Mockups describe intended structure/style for the UI layer; actual component implementation still follows `ai-context/coding-standards.md` and the project's real framework |

Screen IDs (`SCR-NNN`) and Component IDs (`CMP-NNN`) must be preserved verbatim by all downstream skills
to maintain traceability.
