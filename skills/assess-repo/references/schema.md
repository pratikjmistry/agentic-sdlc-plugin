# `assessment-inputs.json` Field Reference

Canonical machine-readable definition: `scripts/schema/assessment-inputs.schema.json` (JSON Schema
2020-12). This document is the human-readable mirror — if the two disagree, the schema file wins and this
doc is stale.

## Envelope

Every entry under `metrics` uses the same shape:

```json
{
  "value": null,
  "unit": "",
  "source": "",
  "confidence": "measured | derived | estimated | unavailable",
  "coverage_pct": null,
  "notes": ""
}
```

**Invariant, enforced by the schema:** `confidence == "unavailable"` if and only if `value` and
`coverage_pct` are both `null`. A metric with real data always sets `confidence` to something other than
`unavailable` and always has a non-null `value`. This is what makes "missing data never looks like bad
data" a checkable property, not a convention people forget.

## Top-level shape

| Key | Purpose |
|---|---|
| `schema_version` | Fixed `"1.0"` for this revision. |
| `rubric_version` | The rubric this run's collection targeted — `score.py` checks this against the rubric file it's given. |
| `assessment_id` | Unique per run, e.g. `flask-36e4a82-20260727T120000Z`. |
| `generated_at` | ISO-8601 timestamp. |
| `target` | Where the code came from and what was actually analyzed — see below. |
| `providers` | One entry per provider that was invoked or considered, with its outcome. |
| `exclusions` | The exclusion set applied before any counting, and what it removed. |
| `human_inputs` | Business context only a human can supply — see below. |
| `metrics` | All 80 required metric IDs, each as an envelope above. |

### `target`

`mode` is `git_url` or `local_path`. `resolved_commit` and `default_branch` are empty strings when the
target isn't a git repository at all (degrade, don't crash). `history_complete` is `false` whenever
`--depth` was used — every metric that depends on full history must then report itself
`confidence: "unavailable"` and say why in `notes`, rather than compute a number from partial history and
present it as reliable. `detected_projects` is non-empty only for monorepos.

### `providers`

One row per provider considered, not just those that ran — a provider skipped by policy still gets a row
with `status: "skipped_by_policy"` and a `reason`, so a reader can see *why* a metric family is
`unavailable` without cross-referencing logs.

### `human_inputs`

Nullable everywhere — a field is `null` until a human actually answers it, never defaulted to a guessed
middle value. `collected_at` records when the human inputs were captured, since these can go stale
independently of the repo's own commit history.

## The 80 required metric IDs

Grouped by family (the dot prefix, e.g. `vcs.hotspots`, is part of the metric ID):

- **`codebase.*`** (8): `total_loc`, `file_count`, `language_census`, `distinct_stacks_count`,
  `generated_loc_pct`, `largest_file_loc`, `avg_file_loc`, `p95_file_loc`.
  `language_census`'s `value` is an array of `{language, loc, pct, files}`.
- **`vcs.*`** (13): `history_days`, `commits_last_90d`, `commits_last_365d`, `active_authors_last_90d`,
  `total_authors`, `author_concentration_gini`, `single_author_file_pct`, `default_branch`,
  `branch_count`, `stale_branch_count`, `merge_commit_ratio`, `commit_msg_issue_ref_pct`, `hotspots`.
  `hotspots`'s `value` is an array of `{path, commits_365d, loc, authors, hotspot_score}`, ranked.
- **`build.*`** (8): `detected_systems`, `containerized`, `devcontainer_present`,
  `one_command_build_documented`, `lockfiles_present`, `required_env_var_count`,
  `external_service_deps`, `attempt`. `attempt`'s `value` is `{attempted, exit_code, duration_s,
  stderr_tail}` — `attempted: false` in detect-only mode (the default).
- **`test.*`** (13): `frameworks_detected`, `test_file_count`, `test_to_source_ratio`, `coverage_pct`,
  `coverage_source`, `suite_executes`, `suite_duration_s`, `pass_rate`, `flake_indicators`,
  `unit_present`, `integration_present`, `e2e_present`, `fixture_or_seed_data_present`.
- **`ci.*`** (5): `systems_detected`, `runs_on_pr`, `gates`, `success_rate_recent`, `avg_duration_s`.
  `gates`'s `value` is `{lint, test, coverage, security, build}` booleans.
- **`deps.*`** (7): `manifest_count`, `direct_count`, `transitive_count`,
  `duplicate_framework_versions`, `eol_components`, `median_majors_behind`,
  `known_vuln_count_by_severity`. `duplicate_framework_versions` value is an array (e.g. three React
  majors in one repo); `eol_components` value is an array of `{name, version, eol_date, severity}`.
- **`structure.*`** (8): `parser_coverage_pct`, `module_count`, `community_count`, `god_nodes`,
  `cyclic_dependency_count`, `avg_fan_out`, `max_fan_out`, `cross_stack_edge_count`. `parser_coverage_pct`
  bounds the credibility of the rest of this family — if it's low, the whole family should be treated as
  `unavailable` regardless of what the parser did manage to produce (see
  `references/legacy-stack-notes.md`, planned). `god_nodes` value is an array of `{symbol, path, fan_in,
  fan_out}`.
- **`debt.*`** (6): `analyzer_used`, `violations_total`, `violations_per_kloc`,
  `violations_by_severity`, `todo_fixme_hack_count`, `baselineable`.
- **`context.*`** (7): `readme_quality_score`, `adr_count`, `docs_loc`, `api_spec_present`,
  `db_schema_docs_present`, `domain_glossary_present`, `ai_context_present` — the last one specifically
  checks for this plugin's own `ai-context/` directory, since its presence changes which onboarding phase
  actually applies.
- **`ops.*`** (5): `deploy_automation_present`, `staging_env_declared`, `observability_present`,
  `feature_flag_system_present`, `rollback_mechanism_documented`. `staging_env_declared` is a hard input
  to the L4 trust-level gate, because `ralph-e2e` writes tests against staging — no declared staging
  environment caps a zone at L3 regardless of every other metric.

## Validation

```bash
python3 scripts/validate.py path/to/assessment-inputs.json
```

Uses `jsonschema` if installed for richer path-qualified errors; otherwise falls back to an equivalent
dependency-free check (same invariants, plainer messages) so validation never requires a pip install.
