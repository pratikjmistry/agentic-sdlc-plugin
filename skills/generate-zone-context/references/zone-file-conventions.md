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
