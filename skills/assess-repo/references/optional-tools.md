# Optional Tool Installation — Standard Protocol

This plugin never hard-depends on an external analysis tool — every skill that can use one degrades
gracefully without it (see each provider's own `unavailable`-with-reason behavior). But "degrade
gracefully" and "silently install things" are different failure modes, and this plugin does neither by
default: it **asks**. This doc is the one shared protocol every skill that shells out to an optional tool
follows, so the experience is the same regardless of which skill triggered it.

**Referenced by:** `/assess-repo` (Step 2) and `/map-codebase` (Step 1). If you add a new skill that shells
out to another optional tool, follow this same protocol and add a row to the table below rather than
inventing a new pattern.

## Why not install automatically on plugin install/update

Checked directly: Claude Code's plugin manifest (`.claude-plugin/plugin.json`) has no install-time
lifecycle hook — `postInstall`, `setupScript`, and similar don't exist in the schema. The closest real
mechanism is a plugin-shipped `SessionStart` hook, which *could* silently install a tool in the background
on every session launch. That was considered and rejected for this plugin: it would run for every user of
this plugin regardless of whether they ever touch a skill that needs the tool, and — more importantly —
it would be a silent environment mutation (installing third-party software) with no user consent, which
contradicts how every other optional tool in this plugin already behaves.

## The protocol

1. **Check first, cheaply.** `shutil.which("<tool>")` (or the language-appropriate equivalent) before
   attempting anything. If found, use it — no prompt needed.
2. **If absent, explain before asking.** State plainly which metrics/capability this unlocks and why it
   currently can't run — not just "tool missing," but "without X, these specific metrics stay unavailable."
3. **Ask explicitly, every time it's relevant.** A simple yes/no (via `AskUserQuestion` in an interactive
   session, or a plain prompt in a scripted context) — "Install now via `<command>`?" Never install without
   this step, even if the same tool was declined in a previous run; there's no durable "don't ask again"
   state to check, and re-asking once per relevant invocation is cheap.
4. **If yes:** run the install command, then re-check availability before proceeding. If the install
   itself fails, report the failure and continue in degraded mode — don't retry indefinitely.
5. **If no (or the tool is unavailable to install, e.g. no `uv`/`pip` on PATH):** proceed in degraded mode.
   Every metric the tool would have backed reports `confidence: "unavailable"` with a `notes` reason
   naming the tool and its install command — so a reader of the final report sees exactly what was skipped
   and why, not just a blank field.
6. **Never install as a side effect of a background/automated run** (e.g. a CI job invoking `/assess-repo
   --quick` across a portfolio). If no interactive session is available to ask, skip straight to degraded
   mode — an unattended run must never install software without a human present to consent.

## Tools this protocol currently covers

| Tool | Used by | Install command | Unlocks |
|---|---|---|---|
| Graphify | `structure_graphify.py` (`/assess-repo`), `/map-codebase` (primary purpose) | `uv tool install graphifyy` (or `pip install graphifyy` if `uv` isn't on PATH) | All of `structure.*` in `/assess-repo`; `/map-codebase`'s entire output — this one is closer to required than optional for `/map-codebase` specifically, since building the graph *is* what that skill does |
| semgrep | `debt_probe.py` (`/assess-repo`) | `pip install semgrep` (or platform package manager) | `debt.violations_total`/`violations_per_kloc`/`violations_by_severity`/`analyzer_used`/`baselineable` — `debt.todo_fixme_hack_count` works regardless, it's a plain regex sweep |
| ruff | `debt_probe.py` (`/assess-repo`), Python-only fallback if semgrep isn't installed | `pip install ruff` | Same `debt.*` fields as semgrep, Python repos only |
| tokei / scc / cloc | `language_census.py` (`/assess-repo`) | `cargo install tokei` / `brew install scc` / `apt install cloc` (etc., pick one) | Faster and more precise `codebase.*` language census on very large repos — **lower priority to prompt about**, since an in-house pure-Python counter is always the guaranteed fallback here (unlike Graphify/semgrep/ruff, no `codebase.*` metric is ever fully `unavailable` without these) |

## Explicitly out of scope for auto-install prompting

`endoflife.date` (or similar EOL databases), package-registry "latest version" lookups, and vulnerability
databases (OSV/GitHub Advisory/npm audit/pip-audit) all require **network access to a third party**, not
just a local binary — these stay behind a separate, stricter bar (client data policy, explicit opt-in flag)
per `/assess-repo`'s own "no hard dependency, policy-gated" design decision, not this protocol. Don't extend
this lazy-install-prompt pattern to a provider that would transmit repo data off-machine; that needs the
policy gate, not just a yes/no prompt.
