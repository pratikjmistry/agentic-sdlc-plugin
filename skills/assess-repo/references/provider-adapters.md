# Adding a New Provider

Every metric family follows the same shape: a function that returns a `dict[str, dict]` mapping fully
qualified metric IDs (e.g. `test.coverage_pct`) to the standard envelope, and nothing else. Providers never
touch scoring, never call the model, and never fail the whole run — `collect.py`'s `_dispatch` wrapper
catches any exception a provider raises and converts it into `unavailable` metrics with the exception
message as the reason.

## Where a provider lives

- `scripts/providers/<name>.py` — for a metric family tied to a specific stack/tool concern (build, test,
  CI, deps, debt, structure). This is most new providers.
- `scripts/<name>.py` (not under `providers/`) — for cross-cutting concerns that don't belong to one stack
  or tool (`exclusions.py`, `context_ops_probe.py`). Only reach for this if the metric family genuinely
  doesn't fit the provider shape below.

## The provider contract

1. **A `collect(...)` function** taking at minimum `repo_path: Path`, plus whatever the family needs
   (`included_files`, `quick`, `attempt`, etc. — see existing providers for the pattern). Returns
   `dict[str, dict]` covering every metric ID in that family, every time — even when everything is
   `unavailable`, the keys must all be present (the schema is closed).
2. **Every value goes through the envelope** — `value`, `unit`, `source`, `confidence`, `coverage_pct`,
   `notes`. Never skip `notes` when `confidence` isn't `measured`; that field is what makes "missing data
   never looks like bad data" actually legible to a reader.
3. **Detect-only by default.** If a metric can only be produced by actually running something (a build, a
   test suite), it must default to `unavailable` with a note pointing at the relevant `--attempt-*` flag,
   never guess from static signals what execution would have shown.
4. **Best-effort external tools degrade to `unavailable`, never to a crash.** Check with `shutil.which`
   before invoking anything external; wrap the actual invocation in a broad `try/except` and fall back
   cleanly on any failure — missing binary, non-zero exit, unparseable output. See `debt_probe.py`'s
   `_try_semgrep`/`_try_ruff` for the pattern, and note their docstrings explicitly flag that neither tool
   was installed in the environment this skill was built in — that flag stays until someone runs it against
   a real install and can remove the caveat.
5. **Network access is opt-in and policy-gated, never silent.** If a metric genuinely requires an external
   API (an EOL database, a vulnerability feed, a CI provider's REST API), it stays `unavailable` by default
   with a note saying exactly what it would need — see `deps_probe.py`'s `eol_components`,
   `median_majors_behind`, and `known_vuln_count_by_severity` for the pattern. Wiring one of these in for
   real is a deliberate, separate decision (an explicit opt-in flag, checked against `--policy` before any
   request goes out), not something a provider does by default just because it's technically possible.

## Wiring it into `collect.py`

1. Add the metric ID list as a `*_METRIC_IDS` constant near the top of `collect.py`.
2. Add the module to the `providers` import.
3. Add the name to `ALL_PROVIDER_NAMES`.
4. Call it through `_dispatch(name, metric_ids, lambda: your_module.collect(...))` alongside the others —
   this gets you the exception safety, the `--providers` opt-out, and the policy gate for free.

## Wiring it into `score.py` / `rubric.yaml`

Only needed if the new metrics should feed a scoring dimension (some metrics — like most of `deps.*`'s
network-gated fields — may just be informational for the report and never feed a dimension at all, which
is fine). If they should:

1. Add the metric IDs to the relevant dimension's `backing_metrics` in `rubric.yaml`, and document the
   band thresholds in its `bands` list (human-readable, not executable).
2. Update the matching `score_<dimension>` function in `score.py` to actually use the new metric — remember
   the "all backing metrics must be available or the whole dimension is unavailable" rule; don't special-
   case a partial-credit path.
3. Add or extend a fixture in `scripts/tests/build_fixtures.py` and a test in `test_score.py` proving the
   new band edges land where you documented them, and re-run the determinism test.

## Testing a new provider

There's no test harness specific to providers (unlike `score.py`, they're not required to be pure/
deterministic — they read the filesystem and sometimes the network). The pattern used throughout this
skill's build is: construct a tiny synthetic git repo or plain directory with `git init`/`printf` in a
single `Bash` call (shell state doesn't persist across separate tool calls — see `git_history.py`'s own
early smoke tests for exactly this pitfall), call `collect()` directly against it, and eyeball the output
against hand-computed expectations before wiring it into `collect.py` at all. Cheap, fast, and it's what
caught the real bugs during this skill's own build (the `uv.lock` exclusion gap, hotspots not respecting
the exclusion set, the zone-carving grouping bug) — all found by running against real or realistic data
before trusting the code.
