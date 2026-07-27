---
name: assess-repo
description: >
  Use this skill when the user types /assess-repo, or asks anything like "is this repo ready for agents",
  "assess this codebase", "should we onboard [repo] for agentic development", "triage these repos", "agent
  readiness", "can Ralph work on this codebase", "what's blocking autonomy here", "score this repo for
  onboarding", or wants a portfolio of brownfield repos ranked for AI-agent readiness before investing in
  them. This is a DECISION skill, not a code-comprehension skill — it answers one question per repository:
  should we invest in making this repo agent-ready, and what specifically blocks autonomy today? It runs
  cheaply (default ≤10 min, ≤2 min with --quick) across a portfolio of 20-40 repos using only git, a
  language census, and standard shell tooling — no graph tool, no model pass over source code, and no
  hard external dependency. Trigger this BEFORE recommending /generate-project-constitution or any other
  greenfield skill on an existing, undocumented, multi-year codebase — running the greenfield spec-first
  flow on an unassessed brownfield repo produces an aspirational constitution the repo contradicts.
  Phase 0 of the brownfield onboarding pathway (Phase 0 — assess-repo → Phase 1 autonomy floor → Phase 2
  reverse-engineer context (/map-codebase, /discover-constitution, /generate-zone-context) → Phase 3
  characterization tests (/characterize) → Phase 4 debt baseline (/baseline-debt) → Phase 5 seam creation
  (/plan-seams) → Phase 6 graduated autonomy per zone → Phase 7 context drift detection (/verify-context)).
  This pathway is separate from and does not replace the Greenfield workflow (/grill → /write-prd →
  /generate-project-constitution → ...) — that one assumes specification precedes code; this one assumes
  code is the only source of truth.
---

# /assess-repo — Agent-Readiness Portfolio Triage

## Build Status

All 8 build steps in `references/build-order.md` are implemented: schema, validator, all Layer 1/2
providers, `rubric.yaml`, `score.py`, the determinism test suite, `render.py`, and the reference docs.
Verified end-to-end against a real public repo (Flask) and all 6 verification cases in
`references/build-order.md`.

**Known limitations, by design, not oversight** — read these before trusting a `GATE_BUILD`/
`GATE_TEST_SIGNAL` failure at face value:

- **Detect-only mode cannot pass `GATE_TEST_SIGNAL` from static signals alone.** `test.suite_executes` is
  always `unavailable` unless `--attempt-test` actually runs the suite — a committed coverage report or a
  green CI badge isn't treated as proof the suite currently passes, since neither confirms it against the
  commit being assessed. A real, well-tested, actively-maintained repo will still show
  `ONBOARD_AFTER_REMEDIATION` / trust level `L0` in the default run; that reflects what detect-only mode can
  verify, not the repo's real quality. Use `--attempt-build --attempt-test` (inside a disposable container)
  for a verdict that can reach `ONBOARD_NOW`.
- **`structure.*` (Graphify) integration is unverified against a real install** — Graphify wasn't available
  to test against while building this; the parsing code is defensive (falls back to `unavailable`
  per-metric on any schema mismatch) but its assumed `graph.json` shape is a documented best guess, not a
  confirmed schema. See `structure_graphify.py`'s module docstring.
- **`debt_probe.py`'s semgrep/ruff integration is likewise unverified** — neither was installed in this
  build's environment; the fallback (`todo_fixme_hack_count` only) is what's actually been exercised.
- **Legacy-stack gaps** (PL/SQL's utPLSQL not detected, VB6/.cls colliding with Salesforce Apex, WebForms'
  `build.bat` convention not checked) are catalogued in `references/legacy-stack-notes.md` rather than
  silently present.
- **`ci.success_rate_recent`, `ci.avg_duration_s`, and all of `deps.eol_components`/
  `median_majors_behind`/`known_vuln_count_by_severity`** require network access to a CI provider API,
  package registry, or vulnerability database respectively — none implemented by default, per the "no hard
  external dependency" design decision. `references/provider-adapters.md` documents how to add one as an
  explicit, policy-gated opt-in.

## Workflow Role

`/assess-repo` is **Phase 0 of the brownfield onboarding pathway** — a separate pathway from this plugin's
Greenfield workflow, for long-lived repos where code is the source of truth and documentation doesn't exist.

```
BROWNFIELD ONBOARDING:
  [/assess-repo]  →  Phase 1 autonomy floor (reproducible build + test signal)
                  →  Phase 2 reverse-engineer context: /map-codebase, /discover-constitution,
                                                        /generate-zone-context
                  →  Phase 3 /characterize (characterization test harness)
                  →  Phase 4 /baseline-debt (debt baseline + ratchet)
                  →  Phase 5 /plan-seams (seam creation, lazy, per-zone)
                  →  Phase 6 graduated autonomy per zone (trust levels L0-L4)
                  →  Phase 7 /verify-context (context drift detection in CI)
```

**Input:** a git URL or local filesystem path, plus a handful of business inputs only a human can supply
(criticality, roadmap demand, data policy, sunset plans).

**Output:** a scored, ranked verdict (`ONBOARD_NOW` / `ONBOARD_AFTER_REMEDIATION` / `DEFER` /
`DO_NOT_ONBOARD`), a recommended starting trust level, a candidate pilot zone, and a portfolio CSV row —
saved to `--out` (default `./.assessment/<repo>-<shortsha>/`), never into the analyzed repo itself.

**Why this exists:** the Greenfield workflow works because `/generate-project-constitution` writes
`ai-context/` *before* any code exists, so nothing in the repo can contradict it. A multi-year brownfield
repo has the opposite problem — running that same constitution interview on it produces a document 80% of
the repo already contradicts, and every downstream Ralph agent then generates inconsistency at machine
speed, confidently. This skill exists to answer, cheaply and defensibly, whether a given repo is worth that
investment at all before anyone writes a line of agent-facing context for it.

**Trust levels referenced throughout this skill's output:**

| Level | Agent may | Gate to advance |
|---|---|---|
| L0 | Read + propose plans only | — |
| L1 | Open PRs, human reviews every line | >80% PR acceptance over 20 PRs |
| L2 | Open PRs, human reviews diff summary | zero escape defects over 4 weeks |
| L3 | Auto-merge on green CI, low-blast-radius changes | sustained L2 metrics |
| L4 | Multi-issue autonomous loops (Ralph) | zone coverage >70% at seams |

---

## Non-Negotiable Design Decisions

These are load-bearing and must not be relitigated by a future edit to this skill without discussion:

1. **Three-layer architecture.** Layer 1 = deterministic facts from in-house scripts (git, build detection,
   test detection, dependency manifests, language census) — the highest-signal input, always available.
   Layer 2 = structural/debt metrics from *optional* external providers behind an adapter, never a hard
   dependency. Layer 3 = narrative synthesis, zone carving, and recommendations, produced by the agent.
2. **Scores are computed by code, never by the model.** `scripts/score.py` is a pure function over Layer
   1/2 metrics and a versioned `assets/rubric.yaml`. Same commit + same rubric version → byte-identical
   scores, always — this output gets used to defend budget allocation across a portfolio. The agent writes
   prose and zone recommendations only; it must never eyeball or adjust a sub-score.
3. **No graph tool required for a default run.** The default triage pass completes with only `git`, a
   language counter, and standard shell tooling. Expensive graph indexing is Phase 2's job
   (`/map-codebase`), not this skill's.
4. **Optional structural provider is Graphify** (`uv tool install graphifyy`) — local, deterministic
   tree-sitter AST parsing, no model calls, emits a stable on-disk `graph.json` a scoring script can parse
   without a running server or graph DB. One adapter among several; if `graphify-out/graph.json` already
   exists in the target, consume it rather than rebuilding. GitNexus is explicitly **not** used here — it's
   reserved for the later `/impact-analysis` skill, where its blast-radius MCP tooling is the right fit.
5. **Missing data must never look like bad data.** Every metric carries `confidence:
   measured|derived|estimated|unavailable` and `coverage_pct`. An unmeasurable dimension is excluded from
   the weighted score with weight redistribution — never silently scored as zero.
6. **Read-only on the target by default.** Nothing is written into the analyzed repo unless
   `--write-in-repo` is passed. All artifacts go to a separate output directory.
7. **Client data policy gates provider selection.** Before invoking any provider that transmits code,
   paths, or symbol names off-machine, check the declared policy and skip the provider with a recorded
   reason if not permitted. Many target repos are client code under MSAs forbidding third-party tooling.

---

## Invocation

```
/assess-repo <git-url-or-local-path> [flags]
```

| Flag | Default | Meaning |
|---|---|---|
| `--attempt-build` | off | Execute build commands from the target. Warns about untrusted code first. |
| `--attempt-test` | off | Requires `--attempt-build`. Executes the test suite. |
| `--providers <list>` | auto-detect | Override which providers run. |
| `--rubric <path>` | `assets/rubric.yaml` | Override the default rubric. |
| `--out <dir>` | `./.assessment/<repo>-<shortsha>/` | Output directory. |
| `--depth N` | full history | Shallow clone override — downgrades churn/velocity/hotspot/bus-factor metrics to `unavailable` and says so. |
| `--submodules` | off | Analyze enumerated submodules, not just list them. |
| `--write-in-repo` | off | Allow writes inside the analyzed repo (e.g. a provider's own cache). |
| `--policy <path>` | none | Client data policy file gating provider selection. |
| `--quick` | off | Skip anything over ~2 min; portfolio-wide fast pass. |

**Default mode is detect-only for build and test** — infer capability from Dockerfiles, devcontainers,
compose files, CI configs, lockfiles, and README build sections, rather than executing anything. If the
user wants a real build/test signal, recommend running with `--attempt-build`/`--attempt-test` **inside a
disposable container**, and say so explicitly before running either flag.

### Auto-detecting the input

- Matches a git URL pattern (GitHub/GitLab/Azure DevOps/Bitbucket, HTTPS or SSH) → clone to a temp working
  directory, full history by default (churn/velocity/hotspot/bus-factor metrics all depend on it).
- Otherwise, treat as a local filesystem path. If it isn't a git repository at all, degrade gracefully:
  still run the language census and structural probes, mark every `vcs.*` metric `unavailable`, and still
  produce a full report — never crash because history doesn't exist.
- Detect monorepos (multiple independent projects under one root) and report per-project as well as
  aggregate. Enumerate submodules; analyze them only if `--submodules` is passed. Detect Git LFS and note
  it — large binaries under LFS should not distort LOC/file-count metrics.

---

## Human Inputs This Skill Must Actively Ask For

These cannot be inferred from the repo and directly drive the ROI verdict (in particular the
`DO_NOT_ONBOARD` path, which overrides a high score outright). Ask interactively via `AskUserQuestion`
(batched at **≤4 options per call** — this tool hard-caps there), or read from a `--policy`/config file if
one is supplied. Record every answer verbatim in `human_inputs` in `assessment-inputs.json`:

- Business criticality (1-5)
- Roadmap demand over the next two quarters: none / low / moderate / heavy
- Client data policy: third-party tooling allowed? external LLM allowed? may code leave premises?
- Sunset or replatform planned (bool + target date)
- Domain expert availability (bool) and onboarding squad size
- Regulatory or audit constraints

Do not guess at these or infer them from repo signals (e.g. commit velocity is *not* a substitute for
"roadmap demand" — a repo can be quiet because it's stable, not because it's dying). If the user can't
answer one right now, record it as unavailable and note the verdict is provisional until it's supplied —
never silently default business criticality or roadmap demand to a middle value.

---

## Exclusion Handling

Build the exclusion set **before** counting anything, and report excluded LOC/file-count separately from
the analyzed total — every metric downstream is garbage if this step is wrong. Start from
`assets/default-exclusions.txt` (vendored directories, `node_modules`, package dirs, build output,
minified assets, migrations, and generated code — including, for legacy .NET, `*.designer.cs`, `*.g.cs`,
`*.Designer.vb`, generated EDMX/dbml, WSDL/service-reference proxies, and scaffolded T4 output) and let the
user extend it per repo. Never count excluded files toward `total_loc`, `language_census`, hotspot ranking,
or any structural metric — but always report how much was excluded and why, so a reviewer can sanity-check
that "small codebase" isn't just "everything got excluded."

---

## Execution Protocol

### Step 0 — Resolve target and check policy

Auto-detect git URL vs. local path (see above). If a `--policy` file is supplied, load it before selecting
any provider — a provider that would transmit code, paths, or symbol names off-machine and isn't permitted
is skipped with `status: "skipped_by_policy"` and a recorded reason in `providers[]`. This check happens
**before** invocation, not as cleanup after.

### Step 1 — Ask for human inputs

Run the `AskUserQuestion` batch(es) above if not already supplied via config. Record raw answers into
`human_inputs`.

### Step 2 — Collect Layer 1 + Layer 2 metrics

Run `scripts/collect.py`, which builds the exclusion set, then dispatches to each provider in
`scripts/providers/` (git history, language census, build probe, test probe, CI probe, deps probe, debt
probe, and the Graphify structural adapter if present and permitted) plus `context_ops_probe.py` for the
`context.*`/`ops.*` families. Each provider either returns metrics with real values and
`confidence: measured|derived|estimated`, or reports itself unavailable/skipped with a reason — it never
fails the whole run. See Build Status above for which integrations are verified against real tooling versus
defensive-but-unverified (Graphify, semgrep/ruff).

Validate the result against the schema before proceeding (`scripts/validate.py`). Save
`assessment-inputs.json` to `--out`.

### Step 3 — Score

Run `scripts/score.py` against `assessment-inputs.json` and `assets/rubric.yaml` (or `--rubric` override).
This is a pure function — no model call, no network access. It evaluates the five hard gates, computes the
nine weighted dimension sub-scores (redistributing weight away from any dimension whose backing metrics are
all `unavailable`), derives the verdict and recommended starting trust level, and states the specific
evidence gate required to advance one level. Save `assessment-scores.json` to `--out`.

**Do not narrate a verdict differently from what `assessment-scores.json` says.** If the agent's prose in
the eventual report disagrees with the computed verdict, the report is wrong, not the score.

### Step 4 — Zone carving

Handled inside `scripts/render.py`'s `carve_zones`: groups `vcs.hotspots` by the first two path segments
(a package/module boundary, not the immediate parent directory — see `render.py`'s comments for why), skips
root-level scattered files entirely (they aren't a cohesive code area), and ranks the top 5 by combined
churn x size. `coupling_score` and `blast_radius` stay `null`/`"unknown"` until Phase 2's real dependency
graph exists — Phase 0 only has hotspot ranking to carve with, not a real coupling signal.

### Step 5 — Render narrative outputs

Run `scripts/render.py <out_dir>` to produce `agent-readiness-report.md`, `remediation-plan.md`,
`zones.json`, and append a row to `portfolio.csv`. This step only narrates what
`assessment-scores.json` already computed — it never re-derives a verdict or score.

---

## Output Files

Written to `--out` (default `./.assessment/<repo>-<shortsha>/`):

| File | Contents |
|---|---|
| `assessment-inputs.json` | Raw normalized metrics with provenance |
| `assessment-scores.json` | Gate results, sub-scores, weighted total, verdict, trust level — deterministic |
| `zones.json` | Candidate zone carving (top 5 by hotspot ranking) |
| `agent-readiness-report.md` | Human narrative, the artifact circulated for review |
| `remediation-plan.md` | Ranked blockers mapped to phase, effort estimate, driver |
| `portfolio.csv` | Single appendable row for cross-repo ranking |

Full schemas: `assessment-inputs.json` in `references/schema.md` (mirrors `scripts/schema/assessment-inputs.schema.json`); the rubric structure in `references/rubric-design.md`.

---

## Constraints

- Default run: ≤10 minutes wall clock per repo, ≤2 minutes under `--quick`. No model pass over source code.
- Redact secrets from every emitted artifact — collectors read config files and may see them.
- `score.py` is import-clean, network-free, and unit-tested with fixture inputs proving byte-identical
  output across repeated runs.
- Degrade gracefully and loudly. Never fail the whole run because one provider is missing.
- This skill never modifies anything under `skills/` other than its own directory, and never touches the
  Greenfield skills or their workflow.

---

## References

- `references/build-order.md` — the staged build plan this skill is being implemented against, and current status
- `references/schema.md` — full `assessment-inputs.json` field reference
- `references/rubric-design.md` — rationale for gate thresholds, dimension weights, and scoring bands
- `references/provider-adapters.md` — how to add a new Layer 1/2 provider
- `references/legacy-stack-notes.md` — per legacy stack (WebForms, VB6, classic ASP, PL/SQL, older Delphi), which metrics degrade and the fallback heuristic
