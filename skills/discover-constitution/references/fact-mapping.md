# Metric-to-Constitution-File Mapping

Human-readable mirror of what `scripts/extract_facts.py` actually does — if the two disagree, the script
wins and this doc is stale. Companion to `skills/assess-repo/references/schema.md`, which defines the
source metric IDs this document maps onto target `ai-context/*.md` files.

## Where facts come from

`constitution-facts.json` (written by `extract_facts.py <assessment_dir> <target_repo_path>`) has three
kinds of content:

1. **Passed-through metric envelopes** — verbatim `{value, unit, source, confidence, coverage_pct, notes}`
   objects copied straight out of `/assess-repo`'s `assessment-inputs.json`, partitioned by which
   constitution file they inform (table below). Nothing is recomputed or reinterpreted here — a metric
   that's `unavailable` in `assessment-inputs.json` stays `unavailable` in `constitution-facts.json`.
2. **Narrative source pointers** — paths to `docs/codebase-map.md` and `graphify-out/.graphify_analysis.json`
   (from `/map-codebase`), passed through as file paths only. The per-file generation agents (Step 3 of
   `SKILL.md`) read these directly for qualitative content (module names, hidden coupling, cyclic-dependency
   groups) — `extract_facts.py` deliberately does not re-derive any of this; `/map-codebase`'s own
   `scripts/synthesize.py` already computed it once.
3. **New detection this script alone is responsible for** — `detect_db_orm()` (marker/migrations-dir scan,
   nothing in `assess-repo`'s metric families covers this), `detect_codeowners()`, and the
   `architecture.risk_areas` synthesis (see "Known Legacy Risk Areas" below).

## Metric ID → constitution file

| Target file | Source metric IDs / signals |
|---|---|
| `tech-stack.md` | `codebase.language_census`, `codebase.distinct_stacks_count`, `build.detected_systems`, `build.containerized`, `build.lockfiles_present`, `deps.manifest_count`, `deps.direct_count`, `deps.transitive_count`, `deps.duplicate_framework_versions`, `ci.systems_detected` |
| `architecture.md` | `target.is_monorepo`/`detected_projects`, `structure.*` (all 8), `architecture.detected_patterns`/`style_summary`, `zones.json`, `map_codebase_outputs`, synthesized `risk_areas` |
| `coding-standards.md` | `debt.*` (6), `vcs.commit_msg_issue_ref_pct`, `vcs.merge_commit_ratio`, `vcs.branch_count`, `vcs.stale_branch_count` |
| `testing.md` | `test.*` (all 13), `ci.gates`, `ci.runs_on_pr` |
| `security.md` | `deps.direct_count`, `deps.duplicate_framework_versions`, `build.external_service_deps`, `build.required_env_var_count`, `ops.observability_present` — **weak proxies only**, see below |
| `deployment.md` | `ops.deploy_automation_present`, `ops.staging_env_declared`, `ops.rollback_mechanism_documented`, `build.containerized`, `build.devcontainer_present`, `ci.systems_detected`, `build.external_service_deps` |
| `observability.md` | `ops.observability_present`, `ops.feature_flag_system_present` |
| `repo-structure.md` | `target.is_monorepo`/`detected_projects`, `structure.module_count`, `structure.community_count`, `zones.json`, `context.readme_quality_score`, `context.docs_loc`, `context.adr_count` |
| `database-guidelines.md` | `detect_db_orm()` output, `context.db_schema_docs_present` |
| `api-guidelines.md` | `context.api_spec_present` (recommendation gate only — no dedicated fact bucket beyond what architecture.md/tech-stack.md already carry) |
| `design-system.md` | `codebase.language_census`'s frontend-language share (recommendation gate only) |
| `project-constitution.md` | Synthesized last from every other file plus Step 4's human mini-interview answers |
| `ralph-agent-spec.md` | No dedicated facts — the template's fixed Agent Types/Parallelization/Promotion sections apply as-is; only the Domain Map (from architecture.md) varies |

**No metric family maps to `database-guidelines.md` directly** — the only related signal in
`assessment-inputs.json` is `context.db_schema_docs_present` (a doc-marker check). `detect_db_orm()` fills
this gap with its own scan: `alembic.ini`, `prisma/schema.prisma`, `knexfile.{js,ts}`, `ormconfig.{json,js}`,
`.sequelizerc`, `config/database.yml`, `flyway.conf`, `liquibase.properties`, a `migrations/`-style
directory, or an EF Core reference in a `*.csproj` (first 50 found, cheap-scan cap).

## `security.md` — always low-confidence, and the report says so

`/assess-repo` collects **no** auth/authz signal at all — nothing in its 82 metrics observes how a system
authenticates or authorizes a request. `build_security_facts()` always includes an explicit `notes` field
saying so. Every generation agent for `security.md` inherits this and must mark anything beyond the weak
proxies (`deps.*`, `build.external_service_deps`, `ops.observability_present`) as
`[DECISION PENDING — could not be determined from static analysis]`, never a guess.

## File recommendation rules (`recommend_files()`)

Deterministic-signal analog of `/generate-project-constitution`'s "File Recommendation Logic" quick
reference — same shape (ALWAYS / RECOMMENDED-if-signal / NOT-NEEDED), but every reason traces to a measured
or derived fact instead of an interview answer:

| File | Recommend when |
|---|---|
| `project-constitution.md`, `architecture.md`, `tech-stack.md`, `coding-standards.md`, `testing.md` | Always |
| `security.md` | Always (weak-proxy caveat above) |
| `ralph-agent-spec.md` | Always — this pipeline exists to run agentic coding loops |
| `api-guidelines.md` | `context.api_spec_present` is `true` |
| `design-system.md` | Frontend languages (JS/TS/CSS/SCSS/HTML) are ≥15% of `codebase.language_census` |
| `deployment.md` | `build.containerized`, `ops.deploy_automation_present`, or `ci.systems_detected` is non-empty/`true` |
| `observability.md` | `ops.observability_present` or `ops.feature_flag_system_present` is `true` |
| `repo-structure.md` | `target.is_monorepo` is `true`, or `structure.module_count` > 5 |
| `database-guidelines.md` | `detect_db_orm().present` or `context.db_schema_docs_present` is `true` |

## Known Legacy Risk Areas (`architecture.risk_areas`)

`build_architecture_facts()` synthesizes a ranked `risk_areas` list — the direct link between this skill and
the pipeline's downstream Feathers-style phases, `/characterize` (characterization tests) and `/plan-seams`
(seam identification). Three sources, all already measured, none invented:

- **`structure.god_nodes`** (when available) — top 5 by `fan_in + fan_out`, each framed as a seam candidate.
- **`structure.cyclic_dependency_count`** (when available and > 0) — one summary entry; the specific cycles
  live in `docs/codebase-map.md`'s Cyclic Dependencies section, not re-parsed here.
- **`zones.json` entries** with `blast_radius: "wide"` or `coupling_score > 0.5` — each framed as a
  characterization-test priority.

Empty when `structure.*` is `unavailable` (no `/map-codebase` run yet) — never guessed. The architecture.md
generation agent (Step 3 of `SKILL.md`) adds a `## Known Legacy Risk Areas` section only when this list is
non-empty, naming `/characterize`/`/plan-seams` explicitly so the connection is visible to whoever reads the
constitution next, not just to this skill's own internals.
