# Rubric Design Rationale

This documents the *reasoning* behind `assets/rubric.yaml` — why these weights, why these bands, and how
the ambiguous cases the plain-English spec left open were resolved. If you're reviewing the banding, this
is the doc to read alongside the rubric itself; `rubric.yaml`'s own comments point back here.

## Why "a dimension needs ALL its backing metrics, or it's unavailable" (no partial credit)

Every dimension in `rubric.yaml` lists a `backing_metrics` set. `score.py` requires every one of them to be
`confidence != "unavailable"` before it will produce a sub-score at all — if even one is missing, the whole
dimension is marked unavailable and its weight is redistributed to the dimensions that *could* be scored.

The alternative — blending a partial sub-score from whichever backing metrics happen to be present — was
considered and rejected. Deciding how to weight 3-of-5 available signals into one number is itself a
judgment call, and the design decision "no interpolation left to the implementer's discretion" reads as
ruling that out. All-or-nothing per dimension is blunter but fully mechanical: no hidden weighting choice
buried in the code that the rubric review can't see.

## Why gate metrics don't overlap 1:1 with dimension metrics

`GATE_BUILD` only checks three booleans (`containerized`, `devcontainer_present`,
`one_command_build_documented`). `build_reproducibility` (the dimension) checks those same three *plus*
`detected_systems` and `lockfiles_present`. This is deliberate: the gate asks "does an autonomy floor
exist at all" (binary), the dimension asks "how good is it" (graded). A repo can clear the gate with a bare
minimum (one documented command) while still scoring low on the graded dimension.

One consequence: it's realistically very hard for all 5 gates to pass while a dimension is fully
unavailable, because the metrics overlap. `references/build-order.md`'s test suite has to construct that
case synthetically (`scored-gates-pass-no-data.json`) — real provider gaps almost always fail a gate first.
That's expected, not a design flaw; see the verdict precedence section below.

## Dimension weights (sum to 100)

| Dimension | Weight | Why this weight |
|---|---|---|
| `build_reproducibility` | 20 | Tied for highest — nothing else matters if agents can't build the thing. |
| `test_safety_net` | 20 | Equally highest — nothing else matters if agents can't tell if they broke it. |
| `change_demand` | 15 | Third-highest on purpose: this is the ROI half of the equation, not a quality signal. A repo can be perfect on every other axis and still not be worth onboarding (see `DO_NOT_ONBOARD`). |
| `structural_modularity` | 12 | Determines how cleanly zones can be carved later (Phase 5) — important, but a downstream concern relative to build/test. |
| `stack_coherence` | 10 | Multiple duplicate framework majors in one repo is a real agent hazard (which one does the agent write against?), but it's more a friction multiplier than a blocker. |
| `debt_containability` | 8 | Debt matters, but *containable* debt (Phase 4's ratchet) is explicitly workable — this rewards containability, not zero debt. |
| `context_availability` | 5 | Nice to already have, but this whole pathway exists *because* it's usually absent — low weight so its absence doesn't unfairly tank an otherwise-strong repo. |
| `blast_radius_containment` | 5 | Matters most at Phase 6 (per-zone trust), less at the portfolio-triage stage this skill covers. |
| `analyzability` | 5 | A leading indicator for Phase 2 cost, not Phase 0 risk — low weight accordingly. |

## Why `structure.parser_coverage_pct` gates the whole structural family

The spec calls this out explicitly: "report this prominently; it bounds the credibility of everything
else in this family." A repo that's 70% VB6 will get a `cyclic_dependency_count` of 2 not because it's
clean, but because tree-sitter couldn't parse most of it. Reporting that "2" next to a "well-modularized"
verdict would be actively misleading. `structural_modularity` treats `parser_coverage_pct < 50` as making
the *entire family* unavailable, not just discounting it — a low-confidence structural signal is worse than
no signal, because it looks authoritative. `analyzability` is the one dimension that uses
`parser_coverage_pct` directly as its own subject (rather than as a gate on other structure.* metrics), so
it's exempt from that cutoff by design.

## Why `change_demand` is human-input-only, never derived from git activity

This was almost derived from `vcs.commits_last_90d` as a fallback when the human input is missing. It
isn't, on purpose: a quiet repo can be quiet because it's stable and correct, or because it's abandoned and
dying, and commit velocity can't tell those apart. `DO_NOT_ONBOARD` — which explicitly overrides a perfect
score — hinges on this exact field. Letting a proxy metric quietly stand in for it would undermine the one
verdict this skill is most obligated to get right (recommending *against* wasted investment). If the human
input isn't collected yet, `change_demand` reports itself `unavailable`, full stop.

## Verdict precedence — resolving what the spec left ambiguous

The spec gives four verdicts and their conditions, but two combinations aren't fully specified: what
happens when gate failures and a `DEFER`-shaped score coincide, and what a `DO_NOT_ONBOARD` verdict does to
an otherwise-passing gate set. `score.py`'s `determine_verdict` resolves this with an explicit precedence
(mirrored in `rubric.yaml`'s `verdict_precedence` block):

1. **`DO_NOT_ONBOARD` override runs first, unconditionally.** The spec's own language — "regardless of how
   high the score is" — reads as an override, not a tiebreaker, so it's checked before gates or score at
   all. It only fires on a *collected* human answer (`roadmap_demand_next_2q` in `{none, low}`, or a
   confirmed sunset date) — never guessed from a missing value.
2. **Gate failure is checked next, and caps the verdict at `ONBOARD_AFTER_REMEDIATION` regardless of
   score.** This reads the spec's "caps the verdict" language as a ceiling: even a hypothetical 95 score
   can't reach `ONBOARD_NOW` if the autonomy floor (build+test+CI) doesn't exist yet. An **unavailable**
   gate-backing metric counts as failing, not passing — the alternative (assume pass when unverifiable)
   would let an unfinished probe rollout quietly report false floors.
3. **Only once all gates pass does the score threshold apply** (`>= 70` → `ONBOARD_NOW`, `45-69` →
   `ONBOARD_AFTER_REMEDIATION`).
4. **`DEFER` requires gates to pass** — this is the one place the resolution isn't obvious from the spec.
   `DEFER`'s own definition ("real investment required, revisit after remediation") sounds like it should
   apply to a repo with real problems, which usually also fails gates. But if gates already fail, rule 2
   already produced a verdict; reaching rule 4 means the autonomy floor genuinely exists (gates passed) and
   the *rest* of the repo (structure, debt, coherence) is what's dragging the score down. That's a
   materially different, narrower scenario than "the floor doesn't exist" — worth its own verdict precisely
   because the floor *does* exist and the remaining work is more attributable to real technical debt.
5. **Below the remediation threshold with gates passing but demand not heavy** falls through to
   `ONBOARD_AFTER_REMEDIATION` rather than some fifth outcome — since the floor already exists (gates
   passed), it's still a reasonable remediation candidate, just not urgent enough to justify `DEFER`'s
   "come back to this deliberately" framing.
6. **`weighted_score is None`** (every dimension unavailable) is treated as its own
   `ONBOARD_AFTER_REMEDIATION` case with an explicit note, reachable only if gates somehow all passed
   despite near-total data absence — a genuine edge case documented rather than silently handled.

## Trust-level recommendation: why Phase 0 can only ever suggest L0 or L1

The trust-level table's own gates for L2-L4 are *earned through operating history* (">80% PR acceptance
over 20 PRs", "zero escape defects over 4 weeks", "sustained L2 metrics") — none of which a first
assessment can have observed. So `recommend_trust_level` doesn't try to project a higher starting level
from a good score; it's binary: `L0` if any gate fails (or `DO_NOT_ONBOARD` applies, in which case there's
no starting level at all), otherwise `L1`. The evidence gate reported to "advance one level" is read
directly from the fixed trust-level table for whichever level comes next — deterministic, no scoring
judgment involved.

## One dependency: PyYAML

`score.py` imports `yaml` to parse `rubric.yaml`. This is the one dependency beyond the standard library in
the entire scoring path, and it was a deliberate call, not an oversight: `rubric.yaml` is meant to stay
genuinely human-readable (real comments, the `bands`/`when` documentation you're reading about right now),
which JSON can't do inline, and PyYAML is about as close to a universal, lightweight Python package as
exists. If this needs to be zero-dependency instead — matching `validate.py`'s jsonschema-with-fallback
pattern — a bundled minimal parser for this rubric's specific shape (block mappings, block sequences,
folded `>` scalars, comments) is a bounded follow-up, not a redesign.
