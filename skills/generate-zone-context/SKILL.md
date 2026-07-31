---
name: generate-zone-context
description: >
  Use this skill when the user types /generate-zone-context, or asks anything like "write per-zone context
  files", "drill into this zone's coupling", "what does Ralph need to know before touching this zone",
  "generate zone-specific ai-context", or wants agent-facing detail scoped to one candidate pilot area
  rather than the whole repo. Phase 2c of the brownfield onboarding pathway — run AFTER `/map-codebase`
  (Phase 2a) and ideally after `/discover-constitution` (Phase 2b, optional but recommended). Writes one
  context file per `zones.json` entry to `ai-context/zones/<zone-id>-<slug>.md` — which specific
  modules/communities live in that zone, which architectural hubs sit inside it, which hidden-coupling
  "surprises" touch it, and which cyclic-dependency groups involve it — detail `/discover-constitution`'s
  repo-wide `architecture.md` deliberately keeps flat and doesn't drill into per zone. Every claim is
  filtered from what `/map-codebase` already computed, never re-derived; anything ungrounded is marked
  `[DECISION PENDING]`. Explicitly frames each zone's hubs/coupling/cycles as seam candidates for the
  downstream `/plan-seams` phase and characterization-test priorities for `/characterize` — the same
  Michael Feathers *Working Effectively with Legacy Code* vocabulary `/discover-constitution` already
  connects to, just zone-scoped instead of repo-wide. Also writes a thin, auto-loading
  `.claude/rules/zones/<zone-id>-<slug>.md` per zone using Claude Code's own `paths:`-scoped rules
  mechanism, so a zone's trust level and top risk signals load automatically the instant Claude reads a
  file inside that zone — no one has to remember the full context file exists.
---

# /generate-zone-context — Per-Zone Drill-Down Context

## Workflow Role

`/generate-zone-context` is **Phase 2c of the brownfield onboarding pathway**, the last named skill in
Phase 2:

```
BROWNFIELD ONBOARDING:
  /assess-repo (Phase 0)  →  Phase 1 autonomy floor
                          →  /map-codebase  →  /discover-constitution  →  [/generate-zone-context]  (Phase 2)
                          →  /characterize (Phase 3)  →  /baseline-debt (Phase 4)
                          →  /plan-seams (Phase 5)  →  graduated autonomy (Phase 6)  →  /verify-context (Phase 7)
```

**Input:** `/assess-repo`'s `zones.json` (hard requirement — there is nothing to generate per-zone files
for without it), plus `/map-codebase`'s `docs/codebase-map.md`/`graphify-out/` in the target repo (soft —
zone files carry only identity/trust-level content without them) and optionally
`/discover-constitution`'s `constitution-facts.json` (soft, non-gating — only used for one cross-reference
section).

**Output:** `ai-context/zones/<zone-id>-<slug>.md` (the full drill-down, source of truth) and
`.claude/rules/zones/<zone-id>-<slug>.md` (a thin, `paths:`-triggered pointer to it — see Design Decisions),
one pair per zone, plus `ai-context/zones/README.md` indexing all of them.

**Why this exists, distinct from `/discover-constitution`'s `architecture.md`:** `architecture.md` has one
flat "Known Legacy Risk Areas" section covering every zone's signals together — cyclic dependencies get
exactly one repo-wide entry, not an enumeration of which groups touch which zone. This skill zooms into ONE
zone at a time with real drill-down: the specific modules, hubs, hidden coupling, and cycles that actually
touch that zone's files — what a Ralph agent (or human) needs before working in that one zone under
graduated autonomy, not the whole repo's summary.

---

## Design Decisions

- **`zones.json` is a hard requirement; missing or empty halts.** No fallback exists — unlike
  `/discover-constitution`'s treatment of a missing `zones.json` (tolerated as an empty list, since zones
  are only one input among many there), zones are this skill's entire subject.
- **`/map-codebase` output is soft, gated.** Missing `docs/codebase-map.md`/`graphify-out/` guts this
  skill's actual reason for existing (the drill-down IS the point), so — mirroring
  `/discover-constitution`'s own Step 0 pattern — soft-confirm via a 2-option `AskUserQuestion` rather than
  a hard block.
- **`constitution-facts.json` is optional and non-gating.** Every zone-specific fact this skill produces
  comes from `zones.json` + `docs/codebase-map.md`/`.graphify_analysis.json` directly; `/discover-constitution`'s
  output is only used for one "Known Legacy Risk Cross-References" link section, which degrades to a plain
  note when absent — no confirmation prompt needed for a single missing link.
- **Filter already-computed output; never re-derive graph analysis — with one carve-out.**
  `scripts/extract_zone_facts.py` filters `.graphify_analysis.json`'s `communities`/`gods`/`surprises` down
  to each zone's paths (a membership check, the same category of operation `/map-codebase`'s own
  `refresh_zones()` already does). Cyclic dependencies are the one exception: they're never persisted to
  any JSON file by `/map-codebase` (only rendered text in `docs/codebase-map.md`), so re-implementing SCC
  here would duplicate real graph-analysis logic. Per-zone cycle detail is left to the Step 3 generation
  agent, which reads `docs/codebase-map.md` directly — see `references/zone-file-conventions.md`.
- **Reconciliation scoped to `ai-context/zones/` and `.claude/rules/zones/` independently**, not all of
  `ai-context/` or `.claude/` — a dirty `architecture.md` (or a dirty rule elsewhere) must not block
  zone-file generation, and a dirty zone file in one directory must not block generation into the other.
  `scripts/extract_zone_facts.py`'s `zones_dir_is_reconcilable()` and `rules_dir_is_reconcilable()` are two
  thin wrappers over one generalized git-status helper, checked and acted on separately.
- **File naming reuses the zone's own `id` verbatim** — `ai-context/zones/<zone.id>-<slug>.md` — matching
  `docs/features/F-XX-<slug>.md`'s established `<ID>-<slug>.md` precedent from `/prd-to-features`. See
  `references/zone-file-conventions.md` for the exact slug rule.
- **The `.claude/rules/zones/` file is a thin pointer, never a second copy.** It carries only trust level,
  blast radius, coupling score, blockers, and a short zone-specific risk summary, plus a link to the full
  `ai-context/zones/<zone.id>-<slug>.md` — never the modules/hubs/surprises/cycles tables. Two files
  describing one zone only stays safe from drift if one is unambiguously derivative of the other.
- **`paths:` uses the zone's exact `paths` list verbatim — never a directory glob.** Confirmed from this
  session's own real Flask dry run: a zone's `name` is not always a directory (one zone was named
  `tests/test_basic.py`, a single file), so a heuristic like `<zone.name>/**` would silently match nothing
  for that zone. Trade-off, stated plainly: a file added to that code area later won't auto-join the rule's
  `paths:` list until the next `/generate-zone-context` run — the same non-widening treatment `zone.paths`
  already gets everywhere else in this pipeline.
- **One agent per zone writes both files**, in the same turn, from the same facts bundle — not two separate
  agent fleets. This is what makes the "thin pointer, no drift" decision above actually hold in practice.
- **Rule generation is on by default, but surfaced, not silent.** `.claude/rules/` is a more central,
  always-loaded location than `ai-context/` — Step 2's confirmation explicitly names both output locations
  before Step 3 writes anything, rather than adding a separate extra confirmation step for what's already a
  visible, explicit choice.
- **The `paths:` rules mechanism itself is verified against current Claude Code documentation, not
  guessed** — `paths:` frontmatter, the unconditional-when-absent default, the 1,000-pattern/4 MiB budget,
  and multi-file/subdirectory support are confirmed-documented; project-root-relative glob resolution and
  Read-triggered (vs. every-tool-use) activation are inferred with high but not total confidence. Because of
  that gap, Step 3's summary tells the user to empirically verify at least one rule actually loads (e.g. via
  `/context` after opening a file in that zone) rather than assuming the mechanism behaves exactly as
  inferred. See `references/zone-file-conventions.md`.

---

## Execution Protocol

### Step 0 — Locate Inputs

Resolve `<assessment_dir>` (explicit arg, or auto-detect `.assessment/<repo-slug>-<shortsha>/`, same
convention as the other two brownfield skills) and `<target_repo_path>`.

**Hard requirement:** `zones.json` must exist in `<assessment_dir>` and be non-empty. If missing:

```
⛔ No zones.json found for this repo.
/generate-zone-context has nothing to generate without it — run /assess-repo first, then re-run this skill.
```

If present but empty (`[]`):

```
⛔ zones.json is empty — /assess-repo found no candidate zones for this repo.
/generate-zone-context has nothing to generate.
```

**Soft confirm on missing `/map-codebase` output:** if both `docs/codebase-map.md` and `graphify-out/` are
absent, ask via `AskUserQuestion` (2 options):

- "Proceed now — zone files will carry only identity/trust-level content from `zones.json`, with drill-down
  sections marked `[DECISION PENDING — run /map-codebase for real dependency-graph data]` (Recommended if
  you just want a starting draft)"
- "Stop — I'll run /map-codebase first for real dependency-graph data"

**Informational, non-gating note** if `constitution-facts.json` is absent: mention in Step 1's summary that
the "Known Legacy Risk Cross-References" section will say "run `/discover-constitution`" instead of
linking anywhere — no confirmation needed.

### Step 0.5 — Reconcile or Fresh Draft?

Two independent git-status checks, one per output directory — `scripts/extract_zone_facts.py`'s
`zones_dir_is_reconcilable()` (scoped to `ai-context/zones/`) and `rules_dir_is_reconcilable()` (scoped to
`.claude/rules/zones/`). Each sets its own mode flag; a dirty verdict in one never affects the other.

For each directory:
- **Doesn't exist or is empty** → fresh draft.
- **Has content, git status for that directory is clean** → overwrite in place. Tell the user to run
  `git diff <that directory>` afterward.
- **Has content, git status is dirty/untracked, or not a git repo** → never overwrite. Write drafts to
  `<that directory>/.generate-zone-context-draft/<file>.md` instead.

### Step 1 — Extract Per-Zone Facts

```bash
python3 scripts/extract_zone_facts.py <assessment_dir> <target_repo_path> --out <assessment_dir>/zone-facts.json
```

Report: zone count, whether `/map-codebase` output was found, whether `constitution-facts.json` was found,
and both reconciliation verdicts from Step 0.5.

### Step 2 — Confirm Zone List

Present every zone from `zones.json` (id, name, trust level, blast radius) and confirm generating all of
them or a subset — plain-text confirm, not the full ALWAYS/RECOMMENDED menu machinery
`/discover-constitution` uses, since every zone is equally in-scope by default (there's no "not needed"
category for a zone the way there is for an optional constitution file). State both output locations
explicitly before asking for confirmation, e.g.:

```
For each confirmed zone, this writes two files:
  ai-context/zones/<id>-<slug>.md        — full drill-down detail (source of truth)
  .claude/rules/zones/<id>-<slug>.md     — thin pointer, auto-loads when Claude reads a file in that zone

Generate all 5 zones listed above, or a subset?
```

### Step 3 — Generate Zone Files

#### Phase 1 — Load Templates (parent context)

`Read` `templates/zone-context.md` and `templates/zone-rule.md` once each (identical instructions apply to
every zone).

#### Phase 2 — Parallel Zone File Generation

**Spawn one Agent per confirmed zone** (single response, so they run in parallel). Each agent is
self-contained and writes **both** files for its zone.

```
You are drafting two files for a single zone from measured/filtered repo-analysis facts, not an interview:
a full context file and a thin auto-loading pointer. Use the Write tool to save both and return two
confirmation lines.

Project folder (absolute path): [TARGET_REPO_PATH]
Context output file: [ai-context/zones/ZONE-ID-slug.md, or ai-context/zones/.generate-zone-context-draft/ZONE-ID-slug.md per Step 0.5's ai_context_zones mode flag]
Rule output file: [.claude/rules/zones/ZONE-ID-slug.md, or .claude/rules/zones/.generate-zone-context-draft/ZONE-ID-slug.md per Step 0.5's rules_zones mode flag]

This zone's filtered facts bundle (from zone-facts.json's zones[] entry for this zone — identity, coupling,
rule_output_path, filtered communities/hubs/surprises, risk_area_cross_references):
[PASTE ONLY THIS ZONE'S BUNDLE]

Narrative source to read directly for this zone's Cyclic Dependencies section (only if map_codebase_available
is true): docs/codebase-map.md at [codebase_map_path] — read its "Cyclic Dependencies" section and note
which numbered group(s), if any, mention a path from this zone's paths list: [PASTE zone.paths]

Context file template — required sections and example structure:
[PASTE THE FULL CONTENT OF templates/zone-context.md AS READ IN PHASE 1]

Rule file template — required shape (this file is a THIN POINTER, never a copy of the context file's
tables — see the template's "Hard Rule" section):
[PASTE THE FULL CONTENT OF templates/zone-rule.md AS READ IN PHASE 1]

Generate the complete, zone-specific context file first. Every claim must trace to the facts bundle above or
the narrative source read. Anything ungrounded (map_codebase_available is false, or a section has no data)
must be written as "[DECISION PENDING — could not be determined from static analysis]" or the template's
specified explicit fallback text, never guessed or invented. Do not restate architecture.md's repo-wide
content — link to it by path instead.

Then generate the rule file. Its `paths:` frontmatter must be exactly this zone's paths list, verbatim, no
additions or widening: [PASTE zone.paths as a YAML list]. Its body must be the compact status line + short
risk summary the template specifies, plus a pointer to the context file just written — never the
modules/hubs/surprises/cycles tables.

Use the Write tool to save both files. Reply with exactly:
"✅ [CONTEXT_OUTPUT_PATH]"
"✅ [RULE_OUTPUT_PATH]"
```

Wait for all agent confirmations before proceeding.

### Step 4 — Generate `ai-context/zones/README.md`

Parent context, last, after every zone agent confirms. Overview table (Zone ID | Name | Trust Level | Blast
Radius | Blockers | context file link | rule file link), generation metadata, and a "Next Steps" pointer to
`/characterize` and `/plan-seams`. Also include the empirical-verification note from Design Decisions:
suggest the user open a file inside one zone in a fresh session and confirm the matching rule's content
loaded (e.g. via `/context`) — the real acceptance test for the `paths:` trigger, not something this skill
can confirm on its own.

### Step 5 — HITL Checkpoint

6 items, split 4+2 across two `AskUserQuestion` calls (`AskUserQuestion` hard-caps at 4 options/call,
`multiSelect: true`, aggregate before evaluating, `"[No preference]"` = zero selected):

**Call 1 of 2:**
1. Zone identity fields (id/name/paths/stack/loc/trust level/blockers) match `zones.json` for every zone file
2. Drill-down sections (Modules/Communities, Architectural Hubs, Hidden Coupling, Cyclic Dependencies)
   accurately reflect `docs/codebase-map.md`/`.graphify_analysis.json`, correctly filtered per zone
3. Every zone in `zones.json` has a corresponding `ai-context/zones/<id>-<slug>.md` file — none skipped
4. Forward-references to `/characterize` and `/plan-seams` are specific to each zone's actual signals, not
   generic filler

**Call 2 of 2:**
5. The `.claude/rules/zones/` files are thin pointers (no duplicated tables) and their `paths:` lists match
   each zone's actual `zones.json` paths exactly
6. `ai-context/zones/README.md` correctly links every per-zone file (both the context and rule file), and
   `zones.json` itself is unmodified (this skill only reads it — it never writes back, unlike
   `/map-codebase`'s `refresh_zones()`)

**All 6 selected:** "✅ Zone Context Approved." Instruct the user to run `/characterize` next.

**Any unselected:** list each unconfirmed item, "⛔ Zone context requires revision — update the relevant
files before proceeding.", halt.

---

## Output Files

| File | Contents | Written where |
|---|---|---|
| `zone-facts.json` | Per-zone filtered facts bundle | `<assessment_dir>` (same dir `/assess-repo`/`/discover-constitution` wrote their own output to) |
| `ai-context/zones/<zone-id>-<slug>.md` | One per zone — identity, coupling, filtered modules/hubs/surprises/cycles, risk cross-references, Ralph-facing summary | Target repo (or `ai-context/zones/.generate-zone-context-draft/` per Step 0.5) |
| `.claude/rules/zones/<zone-id>-<slug>.md` | One per zone — thin, `paths:`-triggered pointer (trust level, blast radius, coupling score, blockers, short risk summary, link to the context file) | Target repo (or `.claude/rules/zones/.generate-zone-context-draft/` per Step 0.5) |
| `ai-context/zones/README.md` | Index of every zone's context + rule file | Target repo |

---

## References

- `references/zone-file-conventions.md` — the naming rule, the cyclic-dependency narrative-agent carve-out
  and why, the cross-reference discipline, and the `paths:` rules mechanism (confirmed-documented vs.
  inferred behavior, the exact-path-glob rationale, the thin-body rule, the 1,000-pattern/4 MiB budget)
- `skills/map-codebase/references/graph-schema.md` — the raw `graph.json`/`.graphify_analysis.json` schema
  this skill filters
- `skills/discover-constitution/SKILL.md` — the sibling skill this skill's risk-area cross-reference
  optionally depends on, and the template for the git-status reconciliation pattern
- `skills/assess-repo/scripts/render.py`'s `carve_zones()` — the source of `zones.json`'s shape
