# Zone Context File Conventions

Companion to `skills/map-codebase/references/graph-schema.md` (the raw `graph.json`/`.graphify_analysis.json`
schema — read that for field-level detail, not restated here) and
`skills/discover-constitution/references/fact-mapping.md` (the repo-wide equivalent of this doc).

## Naming

`ai-context/zones/<zone.id>-<slug>.md`, e.g. `ai-context/zones/ZONE-01-src-core.md`. The `<zone.id>` prefix
is reused verbatim from `zones.json` (already `ZONE-01`/`ZONE-02`-shaped, 2-digit zero-padded) — this
matches `docs/features/F-XX-<slug>.md`'s `<ID>-<slug>.md` precedent from `/prd-to-features` rather than
inventing a new scheme.

`<slug>` is `scripts/extract_zone_facts.py`'s `slugify_zone_name()`: the same safe-character regex
`skills/assess-repo/scripts/collect.py`'s `slugify()` uses (`re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-")
.lower()`), applied to the zone's **full** `name` field — not truncated to a single path segment. `"src/core"`
→ `"src-core"`, `"lib/core"` → `"lib-core"` — two zones with the same last path segment never collide, even
though the `ZONE-NN` prefix alone already guarantees filename uniqueness on its own. Falls back to
`"zone"` if slugification yields an empty string (defensive only — `zones.json` entries always have a
non-empty `name`).

## Why cyclic dependencies are never in `zone-facts.json`

`scripts/extract_zone_facts.py` filters `.graphify_analysis.json`'s `communities`/`gods`/`surprises` down to
a zone's paths — a membership check (`path in zone["paths"]`), not new graph analysis. Cyclic dependencies
are different: `map-codebase/scripts/synthesize.py` computes them via a hand-rolled Tarjan's SCC but never
writes the result to any JSON file — they exist only as rendered text in `docs/codebase-map.md`'s "Cyclic
Dependencies" section. Re-implementing SCC in this skill just to filter it would duplicate real
graph-analysis logic, which this plugin's established discipline forbids (the same reason
`/discover-constitution`'s `extract_facts.py` gives cyclic dependencies one flat repo-wide entry instead of
enumerating groups — see its `_build_risk_areas()`). So per-zone cycle detail is deliberately left to the
Step 3 generation agent: it reads `docs/codebase-map.md` directly and notes which numbered cycle group(s)
mention any path from the zone — a narrative-source read, the same kind `/discover-constitution`'s agents
already do for qualitative content.

## Cross-reference discipline

Every zone file links to `ai-context/architecture.md`, `docs/codebase-map.md`, and its own `zones.json`
entry by path/id — it never repeats their content. The one exception that looks like repetition but isn't:
`risk_area_cross_references` (from `constitution-facts.json`'s `facts.architecture.risk_areas`, filtered to
`kind: "zone_blast_radius"` entries whose `identifier` matches this zone's `name` or `id`) is a **link**, not
a copy — the zone file should reference it by name ("see architecture.md's Known Legacy Risk Areas — <this
zone's entry>") rather than reproduce its `detail`/`why` text verbatim a second time.

## Why `constitution-facts.json` is optional here

Every zone-specific fact this skill produces — identity, coupling, filtered communities/hubs/surprises —
comes from `zones.json` and `docs/codebase-map.md`/`.graphify_analysis.json` directly, never from
`/discover-constitution`'s output. `constitution-facts.json` is read only for the risk-area cross-reference
link above. A repo that has run `/map-codebase` but not yet `/discover-constitution` can still get full,
useful zone context files — the cross-reference section just says "Not available — run
`/discover-constitution`" instead of linking anywhere.

## The `.claude/rules/zones/` auto-load mechanism

`ai-context/zones/<zone.id>-<slug>.md` only gets read if someone already knows to go look for it. Claude
Code has a real, separate mechanism for auto-loading context based on which files are actually being
touched: a `.claude/rules/*.md` file with a `paths:` (plural) frontmatter field — a list of globs — whose
markdown body loads automatically once a matching file enters context. `/generate-zone-context` writes one
such rule per zone, at `.claude/rules/zones/<zone.id>-<slug>.md`, as a **thin pointer** to the full context
file (see `templates/zone-rule.md`'s "Hard Rule" — never a second copy of the drill-down tables).

**What's confirmed, from current Claude Code documentation (not guessed):**
- `paths:` is documented for `.claude/rules/*.md` files only — never `SKILL.md`, never frontmatter anywhere
  else in the repo (frontmatter outside `.claude/rules/` is not parsed at all by Claude Code).
- A rule with no `paths:` field loads unconditionally, for every file. A rule with `paths:` only loads once
  a matching file enters context.
- A single rule's whole `paths` list shares a combined budget of 1,000 expanded patterns and 4 MiB. Brace
  groups multiply the pattern count (`src/*.{ts,tsx}` = 2 patterns); non-brace patterns count as 1 each.
  Not a practical concern at current zone sizes — `zones.json` carves zones from a handful to a few dozen
  churn-ranked files, never a whole subtree — but worth knowing if a future zone ever grows large.
- Multiple rule files can coexist, including in subdirectories (`.claude/rules/zones/` is exactly this).
- The markdown body is injected verbatim into context once triggered.

**What's inferred with high but not total confidence** — not stated outright in the documentation, only
consistent across every example:
- Glob resolution is relative to the project root.
- Triggering happens on Read-style file access, not on every tool use (Edit/Write/Grep behavior isn't
  explicitly confirmed either way).

Because of that gap, `SKILL.md`'s Step 3 summary tells the user to empirically check that at least one
generated rule actually loads — open a file inside a zone in a fresh session and confirm the rule's content
appeared (e.g. via `/context`) — rather than treating the inferred behavior as guaranteed.

**Why `paths:` uses each zone's exact `paths` list, never a directory glob like `<zone.name>/**`:** a
zone's `name` is not always a directory. This session's own real Flask dry run produced a zone named
`tests/test_basic.py` — a single file. A directory-glob heuristic would have silently generated a rule that
matches nothing for that zone; the exact-path list is always correct because it's the same list `zones.json`
itself already validated as this zone's content, never widened or guessed at.
