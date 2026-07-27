# Build Order

This skill is implemented in stages. Each stage is only marked done once its output has been reviewed.

1. ✅ Scaffold the skill directory and `SKILL.md`.
2. ✅ `assessment-inputs.json` schema (`scripts/schema/assessment-inputs.schema.json`) + validator (`scripts/validate.py`).
3. ✅ `git_history.py` and `language_census.py` — these alone produce a usable partial assessment.
4. ✅ `rubric.yaml` + `score.py` + fixture-based determinism tests. *(stopped here for a review checkpoint; approved to continue.)*
5. ✅ Remaining Layer 1 probes: `build_probe.py`, `test_probe.py`, `ci_probe.py`, `deps_probe.py`, `debt_probe.py` — plus `context_ops_probe.py` for the `context.*`/`ops.*` families (not a dedicated stack-provider, folded in per `provider-adapters.md`'s guidance on where cross-cutting concerns live).
6. ✅ `structure_graphify.py` adapter, with clean skip when Graphify is absent or policy-denied.
7. ✅ `render.py` + `assets/templates/*.md` → `agent-readiness-report.md`, `remediation-plan.md`, `portfolio.csv`, `zones.json`.
8. ✅ `references/rubric-design.md`, `references/provider-adapters.md`, `references/legacy-stack-notes.md`.

## Verification cases — all run and passing

- ✅ **A modern well-tested public repo — should score high and land `ONBOARD_NOW`.** Demonstrated via the
  `scored-strong.json` fixture (weighted score 100, verdict `ONBOARD_NOW`, trust level `L1`). Not
  achievable from a *real* public repo in the default detect-only run — see SKILL.md's Build Status
  section on why `GATE_TEST_SIGNAL` needs `--attempt-test` for a real repo to reach `ONBOARD_NOW`.
- ✅ **A large legacy public repo with sparse tests — should surface gate failures cleanly.** Demonstrated
  both by the `scored-sparse-legacy.json` fixture and by a real run against `pallets/flask`
  (`GATE_TEST_SIGNAL` failed with a clear, actionable remediation string; the other 4 gates passed
  correctly).
- ✅ **A local multi-stack folder that is not a git repo at all — must degrade, not crash.** Verified: a
  non-git two-file (Python + JS) folder produced `target.mode: local_path`, `resolved_commit: ""`, every
  `vcs.*` metric `unavailable`, 8/9 providers still `ok`, and a complete rendered report — no crash.
- ✅ **A repo with zero tests — must fail `GATE_TEST_SIGNAL` and still produce a full report.** Covered by
  the same non-git-folder run above and by `scored-sparse-legacy.json`.
- ✅ **A repo mostly in a language the structural parser doesn't support — must report low
  `structure.parser_coverage_pct`, mark the structural family unavailable, redistribute weights, and say so
  in the report.** Covered two ways: `test_low_parser_coverage_makes_structural_family_unavailable`
  exercises the exact `<50%` threshold path directly, and the real Flask run exercises the
  Graphify-absent path (functionally identical outcome — `structure.*` unavailable, weight redistributed,
  the report's "What We Could Not Measure" section states why).
- ✅ **The same repo twice at the same commit — `assessment-scores.json` must be byte-identical.** Proven
  three ways: the fixture-based `test_byte_identical_across_repeated_runs` (7 scenarios x re-serialized
  input x fresh rubric load), a direct `score.py` re-run against the real Flask `assessment-inputs.json`
  diffed byte-for-byte, and `collect.py` re-run against the same local clone producing the same
  `codebase.total_loc`/`vcs.history_days` (the exceptions — `commits_last_90d`/`365d`,
  `active_authors_last_90d` — are documented as wall-clock-relative by design in `git_history.py`, not a
  determinism violation of `score.py`'s own contract).

## Real bugs this build process actually caught

Worth keeping as a record of why "dry-run against a real repo" was the right call at every checkpoint,
not just at the end:

- `uv.lock` wasn't in the default exclusion list — inflated `codebase.total_loc` and topped the hotspot
  ranking on the very first real run (Flask).
- `vcs.hotspots`/`vcs.single_author_file_pct` weren't scoped to the post-exclusion file set — vendored/
  generated files git still had history for were polluting both, caught by a synthetic fixture before the
  first real run.
- Zone-carving grouped by immediate parent directory, letting unrelated root-level files (`CHANGES.rst` +
  `pyproject.toml`) outrank the real `src/flask` module as the "recommended pilot zone" — caught on the
  real Flask run after `render.py` was built, fixed by grouping on the first two path segments and
  excluding root-level files from zone candidacy entirely.
- Gate failure-reason strings said "probe not yet implemented" even after the probes were built and
  correctly reporting `unavailable` for execution-dependent metrics in detect-only mode — a staleness bug
  in the messaging, not the logic; caught by re-reading the real Flask report output, not by the test suite
  (the tests only assert which gates fail, not the exact wording).
- VB6 (`.frm`/`.bas`/`.cls`/`.vbp`) and Delphi project files (`.dproj`) weren't recognized by
  `language_census.py`/`build_probe.py` — caught while writing `legacy-stack-notes.md`, which forced
  actually checking each claim against the code rather than asserting coverage from memory.
