# Legacy Stack Notes

Tree-sitter grammars (Graphify's parsing layer, Phase 2's `/map-codebase`) don't cover several stacks named
in this plugin's brownfield scope. This documents, per stack, what degrades and what the fallback is — the
goal stated in `SKILL.md` holds regardless: **a repo the parsers can't read must still produce a usable
verdict from Layer 1 (git + language census) alone.**

## The general pattern

Every stack below hits the same three degradations, for the same underlying reason (no AST parser):

1. **`structure.*` becomes fully `unavailable`** — `parser_coverage_pct` will be low (near 0 for a
   single-stack legacy repo), which drops the whole family below `structure_parser_coverage_min_for_use`
   (50%, see `rubric.yaml`). This is correct behavior, not a bug: reporting `cyclic_dependency_count: 0`
   next to "well-modularized" when the parser silently skipped 90% of the codebase would be actively
   misleading (see `rubric-design.md`'s section on why `parser_coverage_pct` gates the family).
2. **`analyzability`'s own sub-score reflects that same low `parser_coverage_pct` directly** — it's the one
   dimension that measures parse coverage itself rather than using it as a gate on other data, so a
   legacy-heavy repo will score low here specifically, which is the intended signal ("Phase 2 will be
   expensive/incomplete for this repo").
3. **`debt.violations_total`/`violations_by_severity`/`analyzer_used` become `unavailable`** unless a
   stack-native analyzer happens to be installed — semgrep and ruff (this build's two integrations) don't
   cover any of the stacks below. `debt.todo_fixme_hack_count` still works regardless (it's a plain regex
   sweep, not parser-dependent) as long as the file extension is in `debt_probe.py`'s
   `TEXT_LIKE_EXTENSIONS` set.

What does **not** degrade: `git_history.py` (churn/hotspots/authorship are language-agnostic) and
`language_census.py` (extension-based, once the extension is mapped — see gaps below).

---

## ASP.NET WebForms (`.aspx`, `.ascx`, `.asmx`)

- **Language census:** covered (`ASP.NET WebForms`).
- **Generated code exclusion:** `*.designer.cs`/`*.Designer.vb` (WebForms' code-behind designer partials)
  are in the default exclusion list already.
- **Structure:** the markup/code-behind split means even a working parser would need special handling —
  the `.aspx` markup itself isn't really "AST structure" in the sense `god_nodes`/`fan_out` assume. Expect
  this family `unavailable` regardless of Graphify's general capability.
- **Test:** WebForms-era code is typically tightly coupled to `Page_Load` and the control tree; expect
  `test_file_count` near zero and `GATE_TEST_SIGNAL` to fail honestly — that's an accurate reflection of
  the codebase, not a probe gap.
- **Build — known gap:** `build_probe.py` detects `.csproj`/`.sln` generically but doesn't check for a
  `build.bat`/`build.ps1`/`deploy.ps1` convention some WebForms shops use as their "one command." If one
  exists, `one_command_build_documented` may under-report — extend `build_probe.py`'s
  `one_command_build_documented` check if this comes up in practice.

## VB6 (`.frm`, `.bas`, `.cls`, `.vbp`)

- **Language census:** covered (`VB6`) — **known collision:** `.cls` is also Salesforce Apex's class file
  extension. This heuristic map has no content-sniffing, so a repo mixing VB6 and Apex (unlikely, but
  possible in a portfolio) will misattribute `.cls` files to whichever the map says. Not resolved here;
  flagged rather than silently wrong.
- **Structure:** no tree-sitter grammar exists for VB6 at all — `parser_coverage_pct` will be at or near 0%
  for a VB6-heavy repo, correctly making `structural_modularity` unavailable. This is the canonical case
  the "a repo the parsers can't read must still produce a usable verdict from Layer 1 alone" requirement is
  written for.
- **Build:** VB6 has no modern manifest convention at all (no `package.json`-equivalent) — `build_probe`
  will almost always report `detected_systems: []` for a pure-VB6 repo. **This is accurate, not a false
  negative** — there usually isn't a one-command build path, and `GATE_BUILD` failing honestly reflects
  real Phase 1 work needed, not a probe limitation.
- **Test:** essentially never automated in VB6-era code. Expect `GATE_TEST_SIGNAL` to fail.

## Classic ASP (`.asp`) + VBScript (`.vbs`)

- **Language census:** covered (`Classic ASP`, `VBScript`).
- **Structure:** same hybrid-markup problem as WebForms, compounded by no tree-sitter grammar for VBScript
  at all — expect this family fully `unavailable`.
- **Build:** classic ASP apps are frequently deployed as-is to IIS with no build step whatsoever.
  `detected_systems: []` here is often simply correct, not a gap.

## PL/SQL (`.sql`, `.pls`, `.pks`, `.pkb`)

- **Language census:** covered (`SQL`, `PL/SQL`).
- **Structure:** no tree-sitter grammar for PL/SQL packages — family unavailable, same pattern.
- **Test — known gap:** utPLSQL is the standard PL/SQL testing framework; `test_probe.py`'s
  `detect_frameworks` doesn't check for it (no `utPLSQL`/`ut3` marker file convention, no naming-convention
  check for `*_test`/`test_*` packages). A PL/SQL repo with real utPLSQL coverage will currently
  under-report `test.frameworks_detected` and likely fail `GATE_TEST_SIGNAL` even with real tests present.
  Worth fixing before running this against a PL/SQL-heavy portfolio.
- **Debt:** `debt.todo_fixme_hack_count` still works (`.sql`/`.pls`/`.pks`/`.pkb` are all in
  `TEXT_LIKE_EXTENSIONS`); real static analysis (`violations_total` etc.) has no PL/SQL-native integration
  here and stays `unavailable`.

## Older Delphi (`.pas`, `.dpr`, `.dfm`, `.dproj`)

- **Language census:** covered (`Delphi/Pascal`).
- **Build:** `.dproj`/`.dpr` are now detected as a `delphi` build system (added during this skill's own
  build, after `references/provider-adapters.md`'s dry-run-driven testing pattern caught the gap).
- **Structure:** no standard tree-sitter grammar for Delphi/Pascal — family unavailable, same pattern.
- **`.dfm` files (form definitions) — judgment call, not automated:** these resemble generated design
  metadata (similar in spirit to `*.designer.cs`), but many Delphi teams do hand-edit specific `.dfm`
  properties. They are **not** in the default generated-code exclusion list — deliberately left as regular
  source rather than silently deciding this for every team. If your team never hand-edits `.dfm`, add
  `generated:*.dfm` to a `--extra-exclusions` file.

## What this means for a legacy-heavy portfolio pass

Expect most of the stacks above to land in `ONBOARD_AFTER_REMEDIATION` (gates failing honestly) with
`structure_modularity`/`analyzability`/`debt_containability` all `unavailable`, weight redistributed across
`build_reproducibility`, `test_safety_net`, `change_demand`, `stack_coherence`, and `context_availability` —
the dimensions Layer 1 alone can actually speak to. That's the intended degrade path, not a sign the
assessment is broken for these repos.
