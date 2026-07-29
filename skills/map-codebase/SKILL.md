---
name: map-codebase
description: >
  Use this skill when the user types /map-codebase, or asks anything like "map this codebase", "build a
  dependency graph", "what are the modules in this repo", "find the god objects/hubs in this code", "show
  me hidden coupling", "what would break if I changed X", or wants to understand a brownfield repo's real
  structure before writing an agent-facing constitution for it. Phase 2 of the brownfield onboarding
  pathway — reverse-engineer context — run AFTER `/assess-repo` (Phase 0) has said the repo is worth the
  investment (`ONBOARD_NOW` or `ONBOARD_AFTER_REMEDIATION`); running this on a repo Phase 0 flagged
  `DEFER`/`DO_NOT_ONBOARD` wastes the expensive graph-indexing step this skill exists to justify.
  Builds a real, deterministic dependency graph via Graphify (`uv tool install graphifyy` —
  tree-sitter AST extraction, no LLM calls by default), synthesizes it into a human-readable
  `docs/codebase-map.md` (module/community boundaries, architectural hubs, hidden cross-module coupling,
  circular dependencies, candidate entry points), and refreshes `/assess-repo`'s `zones.json` with real
  `coupling_score`/`blast_radius` now that an actual graph exists (Phase 0 only had hotspot ranking to
  carve zones with — this replaces the `null`/`"unknown"` placeholders it left with real numbers).
  This is the skill `/assess-repo`'s own `structure_graphify.py` provider and report both point to as
  "the deeper graph" when Graphify hasn't been run yet.
---

# /map-codebase — Reverse-Engineer Codebase Structure

## Workflow Role

`/map-codebase` is **Phase 2 of the brownfield onboarding pathway** (Phase 1, the autonomy floor, is
process/tooling work with no dedicated skill yet):

```
BROWNFIELD ONBOARDING:
  /assess-repo (Phase 0)  →  Phase 1 autonomy floor
                          →  [/map-codebase]  →  /discover-constitution  →  /generate-zone-context  (Phase 2)
                          →  /characterize (Phase 3)  →  /baseline-debt (Phase 4)
                          →  /plan-seams (Phase 5)  →  graduated autonomy (Phase 6)  →  /verify-context (Phase 7)
```

`/discover-constitution` and `/generate-zone-context` — this phase's other two named skills — are not yet
built. `/map-codebase`'s output (`graphify-out/graph.json`, `docs/codebase-map.md`) is what they're
expected to consume once they exist; this skill does not write `ai-context/` files itself.

**Input:** a git URL or local path (same auto-detection as `/assess-repo`), ideally one `/assess-repo` has
already scored. If `.assessment/<repo>-<shortsha>/assessment-scores.json` exists for this repo, read it
first — a `DEFER`/`DO_NOT_ONBOARD` verdict is a signal to confirm with the user before spending the time
this skill costs, not a hard block.

**Output:** `graphify-out/graph.json` + `graphify-out/.graphify_analysis.json` (written into the target
repo — Graphify's own convention, and what `/assess-repo`'s `structure_graphify.py` already expects to
find there on a re-run), `docs/codebase-map.md` (the human-readable synthesis), and a refreshed
`zones.json` alongside whichever `/assess-repo` output directory the user points at.

**Why here:** `/assess-repo` deliberately never runs a graph tool — Layer 2 metrics are optional,
expensive, and skipped by default so Phase 0 stays cheap enough for a 20-40 repo portfolio pass. Once a
specific repo clears that triage, `/map-codebase` is where the expensive part actually happens, once, for
the one repo that earned it.

---

## Design Decisions Carried Over from `/assess-repo`

- **Graphify is the structural provider**, chosen for the same reason `/assess-repo` named it: local,
  deterministic tree-sitter AST parsing, no model calls required for the base extraction.
  `graph.json`'s real schema (verified against a live `graphify` 0.9.29 install, not guessed) is
  documented in `references/graph-schema.md` — read that before touching `scripts/`.
- **No model calls by default.** `graphify extract --code-only` and `graphify cluster-only --no-label`
  are both deterministic, LLM-free operations — this skill's default run costs no tokens/API calls beyond
  whatever the invoking agent itself uses to read and narrate the result. A `--deep` flag opts into
  Graphify's semantic LLM-assisted extraction (richer edges, real cost) and `--label` opts into
  LLM-named communities instead of positional placeholders — both are explicit, not default.
- **Artifacts live in the target repo**, not a separate output directory — unlike `/assess-repo`'s default
  read-only stance. `graphify-out/` is Graphify's own convention and the exact path
  `structure_graphify.py` already checks; writing there is the point, not an exception to "read-only by
  default." `docs/codebase-map.md` follows the same "artifacts live with the code they describe"
  reasoning `/design-ui`'s mockups and `/write-test-plan`'s test plan already use in this plugin.
- **Missing data never looks like measured data**, same envelope convention as `/assess-repo`
  (`value`/`unit`/`source`/`confidence`/`coverage_pct`/`notes`) — reused here for the same reason: a
  community with only 2 nodes and a repo with 10,000 unparsed files should never look the same as a
  clean result.

---

## Invocation

```
/map-codebase <git-url-or-local-path> [flags]
```

| Flag | Default | Meaning |
|---|---|---|
| `--deep` | off | Use Graphify's semantic LLM-assisted extraction instead of `--code-only`. Costs API calls; requires a backend configured (`--backend`). |
| `--backend <name>` | auto-detect | Graphify LLM backend for `--deep`/`--label` (gemini/kimi/claude/openai/deepseek/ollama). |
| `--label` | off | Name communities via LLM instead of leaving `Community N` placeholders. |
| `--force` | off | Re-run extraction even if `graphify-out/graph.json` already exists (Graphify's own incremental-update behavior otherwise applies). |
| `--zones <path>` | `./.assessment/<repo>-<shortsha>/zones.json` | Which `/assess-repo` zones file to refresh with real coupling data. Skipped with a note if not found — this skill doesn't require `/assess-repo` to have run first. |
| `--out <dir>` | `<target-repo>/docs/` | Where `codebase-map.md` is written. |

---

## Execution Protocol

### Step 0 — Resolve target, check for a prior assessment

Auto-detect git URL vs. local path (clone to a temp dir for a URL, same as `/assess-repo`). Look for
`.assessment/<repo>-<shortsha>/assessment-scores.json` for this commit. If found and its verdict is
`DEFER` or `DO_NOT_ONBOARD`, surface that to the user and confirm before proceeding — don't silently spend
the time this skill costs on a repo Phase 0 already flagged as low-ROI. If no prior assessment exists,
proceed anyway; `/map-codebase` doesn't require `/assess-repo` to have run.

### Step 1 — Ensure Graphify is available

Follow `skills/assess-repo/references/optional-tools.md`'s standard protocol (shared across every skill in
this plugin that shells out to an optional tool — read it if this is the first time you're running this
step). In short: check `shutil.which("graphify")`; if absent, explain that this skill's entire output
depends on it (Graphify is closer to required than optional here — there's no in-house fallback the way
`/assess-repo`'s language census has one) and ask before running `uv tool install graphifyy` (or
`pip install graphifyy` if `uv` isn't on PATH either). Never install silently, and never prompt at all in
an unattended/scripted invocation — halt with the manual install command instead. If the user declines,
halt; there is no meaningful degraded mode for this skill without Graphify.

### Step 2 — Extract

```bash
graphify extract <path> --code-only   # default
graphify extract <path> --code-only --mode deep --backend <name>   # only with --deep
```

Report the CLI's own summary line (`found N code, N docs...`, `wrote graph.json: N nodes, N edges, N
communities`) to the user verbatim — it's already a good progress signal.

### Step 3 — Cluster

```bash
graphify cluster-only <path> --no-label --no-viz   # default
graphify cluster-only <path> --no-viz              # only with --label
```

`--no-viz` by default keeps this skill's own run fast and avoids generating a `graph.html` nobody asked
for; the codebase-map doc is the deliverable, not the visualization. Mention `graphify tree`/
`graphify export callflow-html` as available follow-ups in the final summary rather than running them
unasked.

### Step 4 — Parse and synthesize

Run `scripts/synthesize.py <path> --out <out_dir>`. This reads `graphify-out/graph.json` +
`graphify-out/.graphify_analysis.json` and computes, in-house (Graphify reports neither field directly —
see `references/graph-schema.md`):

- **Cyclic dependencies** — strongly-connected-components (size > 1) over dependency-relevant edges
  (excludes structural containment relations like `contains`/`method`).
- **Candidate entry points** — file-level nodes with zero incoming edges from other files (nothing in the
  scanned code imports/calls them) — the classic "nothing points at this, something outside the repo must
  invoke it" heuristic. Cross-referenced against common entry-point filenames (`main.*`, `app.*`,
  `index.*`, `cmd/**`) when the naming matches, called out as higher-confidence.
- **Module/community summary** — one entry per community from `.graphify_analysis.json`, with member file
  count, cohesion score, and (without `--label`) an auto-derived name from the most common path prefix
  among its member nodes.
- **Architectural hubs** — from `.graphify_analysis.json`'s `gods`, with fan_in/fan_out split from
  `graph.json`'s links (Graphify's own `gods` degree figure is undirected total degree, not split).
- **Hidden coupling** — `.graphify_analysis.json`'s `surprises` verbatim (cross-community edges Graphify's
  own heuristics already flagged as unexpected).

Writes `docs/codebase-map.md` (template: `assets/templates/codebase-map.md.tmpl`).

### Step 5 — Refresh zones.json (if one exists)

For each zone in the target `zones.json`, cross-reference its `paths` against the graph's nodes:
- **`coupling_score`** — ratio of edges crossing the zone's community boundary (to nodes in a different
  `community`) versus edges staying within it. Low ratio = well-contained zone.
- **`blast_radius`** — `"contained"` if the zone's nodes' combined fan_in is mostly (>80%) from within the
  same community; `"wide"` if a meaningful share comes from multiple other communities; `"unknown"` stays
  if none of the zone's paths matched any graph node (the graph didn't cover that zone — say so, don't
  guess).

Write the updated `zones.json` back in place (the input file is overwritten with the same shape, just
`coupling_score`/`blast_radius` populated instead of `null`/`"unknown"` — every other field is untouched).

### Step 6 — Summary

```
✅ Codebase Map Generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Saved to: docs/codebase-map.md
Graph:    graphify-out/graph.json ([N] nodes, [N] edges, [N] communities)
Zones refreshed: [N] ([path to zones.json], or "none found — skipped")

Cyclic dependency groups : [N]
Architectural hubs       : [N]
Hidden coupling ("surprises") : [N]
Candidate entry points   : [N]

Next: /discover-constitution (not yet built) would read this map to draft ai-context/ from the code
itself, or explore directly with `graphify query "<question>"` / `graphify explain "<symbol>"`.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Output Files

| File | Contents | Written where |
|---|---|---|
| `graphify-out/graph.json` | Raw extracted graph (Graphify's own format) | Target repo (Graphify's convention) |
| `graphify-out/.graphify_analysis.json` | Communities, cohesion, hubs, surprises (Graphify's own format) | Target repo |
| `docs/codebase-map.md` | Human-readable synthesis — modules, hubs, coupling, cycles, entry points | Target repo (`--out` override available) |
| `zones.json` | Same shape `/assess-repo` produced, `coupling_score`/`blast_radius` now populated | Wherever `--zones` points (default: the matching `/assess-repo` output dir) |

---

## References

- `references/graph-schema.md` — the verified real `graph.json`/`.graphify_analysis.json` schema, and
  exactly which fields this skill computes itself versus reads directly (mirrors the same documentation
  in `skills/assess-repo/scripts/providers/structure_graphify.py`'s docstring — keep both in sync if either
  changes)
- `references/entry-point-heuristics.md` — the zero-fan-in heuristic's known false positives/negatives per
  language, and what to do about them
- `skills/assess-repo/references/optional-tools.md` — the shared check-explain-ask protocol for installing
  Graphify (and any other optional tool this plugin's skills use)
