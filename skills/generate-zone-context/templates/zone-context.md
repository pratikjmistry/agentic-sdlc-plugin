# Template: ai-context/zones/<ZONE-ID>-<slug>.md

## Required Sections

- **Header** — `# Zone Context — <ZONE-ID>: <zone name>`, generated date, and the source `zones.json` path
  this file was drafted from (so a reader knows exactly which `/assess-repo` run produced the underlying
  data).
- **Zone Identity** — table: `id`, `name`, `paths` (the file list this zone covers), `stack`, `loc`,
  `coverage_pct`. If `coverage_pct` is `null`, say so explicitly — `/assess-repo` Phase 0 only measures
  aggregate repo-wide coverage, not per-zone, so `null` here is expected, not a gap.
- **Trust Level & Blockers** — `recommended_trust_level` and `blockers` from the zone's `zones.json` entry.
  Cross-reference `ai-context/ralph-agent-spec.md` by path for what each trust level actually permits —
  do not restate the trust-level ladder here.
- **Coupling & Blast Radius** — `coupling_score` and `blast_radius`, with one plain-language paragraph
  interpreting what they mean for someone about to touch this zone (e.g. a `"wide"` blast radius means
  changes here are more likely to break code outside this zone than a `"contained"` one). If both are still
  `null`/`"unknown"` (no `/map-codebase` run yet), write `[DECISION PENDING — run /map-codebase for real
  coupling data]` rather than guessing.
- **Modules/Communities in This Zone** — table (`Community | Files in Community | Overlap with This Zone |
  Cohesion`) built from the zone's filtered community data. A community only partially inside this zone is
  still listed, with the overlap count shown, not silently dropped or misrepresented as fully contained.
- **Architectural Hubs in This Zone** — table (`Symbol | Path | Fan-in | Fan-out`) — only hubs whose own
  node sits inside this zone's paths, not hubs elsewhere in the repo that merely call into this zone.
- **Hidden Coupling ("Surprises") Touching This Zone** — table (`Source | Target | Relation | Why`) — only
  surprises where at least one endpoint's source file is inside this zone's paths.
- **Cyclic Dependencies Touching This Zone** — this is the one section NOT sourced from the filtered facts
  bundle (`zone-facts.json` deliberately excludes cycles — see `references/zone-file-conventions.md` for
  why). Read `docs/codebase-map.md`'s "Cyclic Dependencies" section directly and note which numbered
  group(s), if any, mention a path from this zone's `paths` list. "None detected touching this zone's
  paths" if none do — never invent a cycle that isn't in that section.
- **Known Legacy Risk Cross-References** — bullet list of this zone's `risk_area_cross_references` (already
  filtered to `kind: "zone_blast_radius"` entries matching this zone), each linking to
  `ai-context/architecture.md`'s "Known Legacy Risk Areas" section by name rather than repeating its content
  verbatim. If empty because `constitution-facts.json` wasn't available, write "Not available — run
  `/discover-constitution` to populate this cross-reference," not silence.
- **What a Ralph Agent Needs to Know Before Touching This Zone** — 3-6 bullets synthesized from this zone's
  *own* signals above (its specific hubs, surprises, coupling score) — not a restatement of
  `architecture.md`'s repo-wide list. If this zone has no hubs, no surprises, and a contained blast radius,
  say so plainly ("Low-risk zone — no architectural hubs or hidden coupling detected here") rather than
  padding with generic advice.
- **Forward Reference to `/characterize` and `/plan-seams`** — one paragraph, explicitly naming both
  downstream phases, framed in Michael Feathers' *Working Effectively with Legacy Code* vocabulary: what in
  this zone is a seam candidate for `/plan-seams`, and what should get a characterization test from
  `/characterize` before anyone refactors here. If this zone has no risk signals, say the seam/
  characterization-test priority is elsewhere, don't manufacture urgency that isn't supported by the data.
- **Footer** — cross-reference links to `ai-context/architecture.md`, `docs/codebase-map.md`, and this
  zone's own `zones.json` entry (by id). No content duplication — link, don't repeat.
