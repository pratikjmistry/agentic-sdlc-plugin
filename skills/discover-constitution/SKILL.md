---
name: discover-constitution
description: >
  Use this skill when the user types /discover-constitution, or asks anything like "generate ai-context for
  this existing codebase", "draft a constitution for this legacy repo", "reverse-engineer our architecture
  docs", "write project constitution from the code itself", or wants agent-facing `ai-context/*.md` files
  for a brownfield repo that never had them. Phase 2b of the brownfield onboarding pathway — the inverse of
  `/generate-project-constitution`: instead of interviewing a human before any code exists, it reverse-
  engineers draft `ai-context/*.md` files (architecture, tech stack, coding standards, testing, security,
  deployment, observability, repo structure, database guidelines, ralph-agent-spec, project-constitution)
  from what `/assess-repo` (Phase 0) and `/map-codebase` (Phase 2a) already measured. Asks a human only for
  the residue of governance facts — Immutable Principles, Decision Authority — that no static analysis can
  produce. Every claim is grounded in a measured or derived fact; anything static analysis can't confidently
  determine is marked `[DECISION PENDING]` rather than guessed. Also surfaces god objects, cyclic
  dependencies, and high-blast-radius zones as a "Known Legacy Risk Areas" section in architecture.md,
  explicitly framed as seam candidates for the downstream `/plan-seams` phase and characterization-test
  priorities for `/characterize` — Michael Feathers' *Working Effectively with Legacy Code* vocabulary these
  two later phases are named after.
---

# /discover-constitution — Reverse-Engineer the Project Constitution

## Workflow Role

`/discover-constitution` is **Phase 2b of the brownfield onboarding pathway**:

```
BROWNFIELD ONBOARDING:
  /assess-repo (Phase 0)  →  Phase 1 autonomy floor
                          →  /map-codebase  →  [/discover-constitution]  →  /generate-zone-context  (Phase 2)
                          →  /characterize (Phase 3)  →  /baseline-debt (Phase 4)
                          →  /plan-seams (Phase 5)  →  graduated autonomy (Phase 6)  →  /verify-context (Phase 7)
```

**Input:** `/assess-repo`'s `.assessment/<repo>-<shortsha>/assessment-inputs.json` (hard requirement — this
skill's entire fact base comes from it, there is no fallback source) and `zones.json` (soft — treated as
empty if absent), plus `/map-codebase`'s `docs/codebase-map.md` and `graphify-out/.graphify_analysis.json`
in the target repo (soft — architecture.md/repo-structure.md carry only Phase-0 heuristic signal without
them).

**Output:** the same `ai-context/*.md` file set `/generate-project-constitution` produces for a greenfield
project — `project-constitution.md`, `architecture.md`, `tech-stack.md`, `coding-standards.md`, `testing.md`,
and conditionally `security.md`, `api-guidelines.md`, `design-system.md`, `deployment.md`,
`observability.md`, `repo-structure.md`, `database-guidelines.md`, `ralph-agent-spec.md` — plus an
intermediate `constitution-facts.json` written alongside `/assess-repo`'s own output.

**Why this exists:** every subsequent skill in the pipeline, and Ralph agents later, need the same
`ai-context/` contract regardless of whether a project started greenfield or brownfield.
`/generate-project-constitution` produces it via interview; this skill produces the equivalent from
measured facts, so a brownfield repo never has to fake a greenfield-style interview about decisions that
were actually made (or drifted into) years ago.

---

## Design Decisions

- **Reuse, don't duplicate, templates.** All 13 constitution templates live in
  `skills/generate-project-constitution/templates/*.md` and are loaded directly from there — no local
  copies. This mirrors the existing cross-skill reference `/map-codebase` already makes to
  `skills/assess-repo/references/optional-tools.md`.
- **Reuse, don't re-derive, `/map-codebase`'s graph analysis.** Cycles, entry points, hub fan-in/out, and
  community naming are already computed by `scripts/synthesize.py` in `/map-codebase`. This skill's own
  `scripts/extract_facts.py` never re-parses `docs/codebase-map.md` or re-runs graph analysis — it only
  checks those files exist and passes their paths through for the generation agents to read directly.
- **Missing data never looks like measured data.** Every fact in `constitution-facts.json` carries the same
  envelope-derived `confidence` its source metric had in `assessment-inputs.json`. Any fact with
  `confidence: unavailable` or `estimated` becomes `[DECISION PENDING — could not be determined from static
  analysis]` in the generated file, never a guess — the one hard behavioral difference from
  `/generate-project-constitution`'s agents, which fill from confident interview answers.
- **git is the diff tool.** When `ai-context/` already has content, this skill runs `git status --porcelain
  -- ai-context/` rather than writing its own markdown diff/merge logic — see Step 0.5.
- **The Feathers connection is explicit, not implicit.** `/characterize` and `/plan-seams`, two phases
  downstream of this one, are named directly after Michael Feathers' *Working Effectively with Legacy Code*.
  This skill already reads the exact signals WELC cares about (god objects, cyclic dependencies, zone
  coupling/blast-radius) — Step 3's architecture.md generation surfaces them as a "Known Legacy Risk Areas"
  section, explicitly naming both downstream phases, instead of leaving the connection for a human to infer.

---

## Execution Protocol

### Step 0 — Locate Inputs

Resolve `<assessment_dir>` (explicit arg, or auto-detect `.assessment/<repo-slug>-<shortsha>/` for the
target repo's current resolved commit — same `slugify(source)` + 7-char short SHA convention
`skills/assess-repo/scripts/collect.py` uses) and `<target_repo_path>`.

**Hard requirement:** `assessment-inputs.json` must exist in `<assessment_dir>`. If it doesn't, halt:

```
⛔ No /assess-repo output found for this repo.
/discover-constitution has no fallback source for these facts — run /assess-repo first, then re-run this skill.
```

**Soft confirm on missing `/map-codebase` output:** if both `docs/codebase-map.md` and `graphify-out/` are
absent in the target repo, ask via `AskUserQuestion` (2 options, not free text):

- "Proceed now — architecture.md/repo-structure.md will carry only Phase-0 heuristic signal, marked
  `[DECISION PENDING — run /map-codebase for real dependency-graph data]` (Recommended if you just want a
  starting draft)"
- "Stop — I'll run /map-codebase first for real dependency-graph data"

This mirrors `/map-codebase`'s own Step 0 precedent (a low-ROI `/assess-repo` verdict is surfaced and
confirmed, never a hard block).

### Step 0.5 — Reconcile or Fresh Draft?

Run `scripts/extract_facts.py`'s `check_existing_ai_context()` / `ai_context_is_reconcilable()` logic (or
just read `constitution-facts.json`'s `existing_ai_context`/`reconciliation` fields after Step 1 runs).

- **`ai-context/` doesn't exist or is empty** → fresh draft. Every confirmed file gets written directly.
- **`ai-context/` has content and `reconciliation.reconcilable` is `true`** (git status for `ai-context/` is
  clean relative to HEAD) → overwrite in place. Tell the user: *"This is a reconciliation pass — run `git
  diff ai-context/` afterward to review what changed."*
- **`ai-context/` has content and `reconciliation.reconcilable` is `false`** (uncommitted changes, untracked
  files, or not a git repo at all) → **never overwrite.** Write every draft to
  `ai-context/.discover-constitution-draft/<file>.md` instead and tell the user to merge manually, quoting
  `reconciliation.detail` for why.

Set a mode flag (`overwrite` vs. `stage-to-draft-dir`) that Step 3's generation agents use for their
`Output file:` path.

### Step 1 — Extract Facts

```bash
python3 scripts/extract_facts.py <assessment_dir> <target_repo_path> --out <assessment_dir>/constitution-facts.json
```

Read the result. Report the top-line summary to the user: how many metrics were measured vs. unavailable,
whether `/map-codebase` output was found, whether `db_orm`/`codeowners` markers were found, and the
reconciliation verdict from Step 0.5.

### Step 2 — Recommend File Set

Same ALWAYS/RECOMMENDED/NOT-NEEDED presentation as `/generate-project-constitution`'s Step 2, but every
reason traces to `constitution-facts.json`'s `file_recommendations` (a measured or derived signal, not an
interview answer — see `references/fact-mapping.md`'s rule table):

```
Based on the measured facts, I recommend generating the following constitution files:

ALWAYS INCLUDED:
  ✅ project-constitution.md — master governance doc, immutable principles, index (generated last)
  ✅ architecture.md         — system topology, domain map, Known Legacy Risk Areas
  ✅ tech-stack.md           — canonical technology choices
  ✅ coding-standards.md     — language conventions and review standards
  ✅ testing.md              — test strategy and coverage expectations
  ✅ security.md             — [reason: always recommended; no auth/authz signal available — see notes]
  ✅ ralph-agent-spec.md     — [reason: always recommended; this pipeline runs agentic coding loops]

RECOMMENDED FOR THIS REPO:
  ✅ deployment.md       — [reason: <file_recommendations["deployment.md"].reason>]
  ...

NOT NEEDED FOR THIS REPO:
  ⬜ design-system.md    — [reason: <file_recommendations["design-system.md"].reason>]
  ...

Shall I proceed with these files, or do you want to add or remove any?
```

Wait for the user to confirm or adjust before generating anything.

### Step 3 — Generate Draft Files

#### Phase 1 — Load Templates (parent context)

Find `skills/generate-project-constitution/` from the `<location>` tag the same way that skill's own Step 3
does, and `Read` `templates/<filename>.md` for every confirmed file except `project-constitution.md` (loaded
last, in Phase 3 below). No local template copies in this skill's own directory.

#### Phase 2 — Parallel Constitution File Generation

**Spawn one Agent per confirmed file** (except `project-constitution.md`) **in a single response** so they
run in parallel. Each agent is self-contained.

```
You are drafting a single project constitution file from measured repo-analysis facts, not an interview.
Use the Write tool to save it and return one confirmation line.

Project folder (absolute path): [TARGET_REPO_PATH]
Output file: [ai-context/FILENAME.md, or ai-context/.discover-constitution-draft/FILENAME.md per Step 0.5's mode flag]
Project name: [PROJECT_NAME]

Relevant facts for this file (from constitution-facts.json's facts.[BUCKET] key):
[PASTE ONLY THE RELEVANT constitution-facts.json BUCKET — not the whole file]

Narrative sources to read directly for qualitative content (only if present):
[docs/codebase-map.md path, .graphify_analysis.json path, from constitution-facts.json's map_codebase_outputs]

Template — required sections and example structure:
[PASTE THE FULL CONTENT OF templates/FILENAME.md AS READ IN PHASE 1]

Generate a complete, project-specific ai-context/[FILENAME].md. Every statement must trace to a fact above
or a narrative source. Any fact whose confidence is "unavailable" or "estimated" must be written as
"[DECISION PENDING — could not be determined from static analysis]", never guessed or invented. Do not
write aspirational/intended-design language — describe what the measured facts say the codebase actually
does, consistent with how this whole pipeline treats legacy code. Cross-reference other constitution files
by path rather than repeating content.

Use the Write tool to save the file. Reply with exactly: "✅ [OUTPUT_PATH]"
```

**architecture.md's agent gets one addition**, appended to the prompt above: if `facts.architecture.risk_areas`
is non-empty, instruct it to add a `## Known Legacy Risk Areas` section immediately after "Key architectural
constraints," one entry per `risk_areas` item, each explicitly framed as a seam candidate for the upcoming
`/plan-seams` phase and a characterization-test priority for `/characterize` (reuse each entry's `why` field
verbatim — it's already written in that framing). This does not modify
`skills/generate-project-constitution/templates/architecture.md` itself — the instruction lives only in this
agent's prompt, so the shared template stays reusable as-is for greenfield projects with no legacy code to
flag.

Wait for all agent confirmations before proceeding.

### Step 4 — Human Mini-Interview

Run the 3-call sequence in `references/mini-interview.md`: Immutable Principles (`AskUserQuestion`,
dynamically-generated options), Decision Authority (free text, `CODEOWNERS`-grounded if found), Residual
Gaps (`AskUserQuestion`, always includes `security.md`).

### Step 5 — Generate `project-constitution.md`

Parent context, last. Read `templates/project-constitution.md`, synthesize it from every file just written
plus Step 4's answers. Tag each Immutable Principle `(derived from measured baseline)` or `(team-declared)`
per its provenance (see `references/mini-interview.md`).

### Step 6 — HITL Checkpoint

Same 2-call/5-item `AskUserQuestion` pattern as `/generate-project-constitution`'s Step 4
(`AskUserQuestion` hard-caps at 4 options/call, split 5 items across 2 sequential `multiSelect: true`
calls, aggregate before evaluating, `"[No preference]"` = zero selected):

**Call 1 of 2:**
1. Tech stack facts match what's actually deployed
2. Architecture and domain map match the real dependency graph (or are honestly marked `[DECISION PENDING]`
   where `/map-codebase` hasn't run)
3. No `[DECISION PENDING]` markers remain in files you expected to be complete

**Call 2 of 2:**
4. Immutable Principles and Decision Authority reflect how this team actually works
5. No contradictions between constitution files

**All 5 selected:** "✅ Constitution Approved." Instruct the user to run `/generate-zone-context` next.

**Any unselected:** list each unconfirmed item, "⛔ Constitution requires revision — update the relevant
files before proceeding.", halt.

---

## Output Files

| File | Contents | Written where |
|---|---|---|
| `constitution-facts.json` | Extracted, file-partitioned facts + recommendations | `<assessment_dir>` (same dir `/assess-repo` wrote its own output to) |
| `ai-context/project-constitution.md` | Master governance doc | Target repo (or `.discover-constitution-draft/` per Step 0.5) |
| `ai-context/architecture.md` | System topology, domain map, Known Legacy Risk Areas | Target repo |
| `ai-context/tech-stack.md`, `coding-standards.md`, `testing.md` | Always-included files | Target repo |
| `ai-context/security.md`, `api-guidelines.md`, `design-system.md`, `deployment.md`, `observability.md`, `repo-structure.md`, `database-guidelines.md`, `ralph-agent-spec.md` | Conditional, per Step 2 | Target repo |

---

## References

- `references/fact-mapping.md` — the metric-ID → constitution-file mapping, the file-recommendation rule
  table, and the Known Legacy Risk Areas synthesis rules
- `references/mini-interview.md` — the exact 3-call human-residue question set
- `skills/generate-project-constitution/SKILL.md` — the greenfield counterpart this skill mirrors (Step 2
  file recommendation UI, Step 3 parallel-agent generation pattern, Step 6 HITL checkpoint pattern)
- `skills/map-codebase/references/graph-schema.md` — what `docs/codebase-map.md`/`.graphify_analysis.json`
  actually contain, for the generation agents' own narrative-source reading
- `skills/assess-repo/references/schema.md` — the full `assessment-inputs.json` metric reference
