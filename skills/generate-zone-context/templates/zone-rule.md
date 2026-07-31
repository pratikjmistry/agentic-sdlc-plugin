# Template: .claude/rules/zones/<ZONE-ID>-<slug>.md

This is a **thin, auto-loading pointer**, not a second copy of `ai-context/zones/<ZONE-ID>-<slug>.md`. It
exists so Claude Code's `paths:`-scoped rules mechanism loads this zone's highest-value facts the instant a
matching file is read — see `references/zone-file-conventions.md` for what's confirmed-documented vs.
inferred about how that mechanism behaves.

## Required Shape

- **Frontmatter** — `paths:` set to the zone's exact `paths` list, verbatim, copied from
  `zone-facts.json`'s `zone.paths` for this zone. Never widen this to a directory glob (e.g. never invent
  `<zone-name>/**`) — some zones are a single file, not a directory, and a directory glob would silently
  match nothing for those. Never narrow it either — every path in the zone belongs in the list.
- **One-line header** — `# Zone: <zone name> (<ZONE-ID>)`.
- **Compact status line** — trust level, blast radius, coupling score, and blocker count on one line, e.g.
  `Trust: L0 · Blast radius: wide · Coupling: 0.72 · Blockers: 1`. Not a table — this file is meant to be
  skimmed in under a second.
- **2-4 sentence risk summary** — synthesized from this zone's own `hubs`/`surprises`/
  `risk_area_cross_references` (from `zone-facts.json`, already filtered to this zone) — never from
  `architecture.md`'s repo-wide risk list. If this zone has no hubs, no surprises, and a contained blast
  radius, say so plainly rather than padding.
- **Closing pointer** — one line: `Full detail: ai-context/zones/<ZONE-ID>-<slug>.md`.

## Hard Rule

**Never include the Modules/Communities, Architectural Hubs, Hidden Coupling, or Cyclic Dependencies
tables here.** Those stay exclusively in `ai-context/zones/<ZONE-ID>-<slug>.md`. This file's only job is to
get triggered automatically and tell the reader enough to know whether to go read the full file — content
duplication here is exactly what turns two files describing one zone into two files that quietly disagree
over time.
