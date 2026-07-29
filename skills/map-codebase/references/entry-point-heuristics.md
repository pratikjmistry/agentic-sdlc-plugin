# Entry-Point Detection: Known Limitations

"Candidate entry points" are file-level nodes with zero incoming edges from any other node in the
extracted graph — nothing in the scanned code imports or calls them, so something *outside* the repo
(a process manager, a WSGI server, a test runner, a build tool) must be invoking them directly. This is a
structural heuristic over a `--code-only` (AST-only) graph, not a real "this is the entry point" fact —
know its failure modes before trusting the list uncritically:

## False positives (flagged as an entry point, but isn't really one)

- **Dead code.** A file nothing calls because nothing calls it anymore, not because something external
  invokes it. Cross-check against `vcs.commits_last_365d`/`git log -- <path>` from `/assess-repo` — a
  "entry point" with no commits in years and no obvious external trigger is more likely dead than special.
- **Dynamically-loaded code.** Plugin systems, dependency-injection containers, ORMs that discover model
  classes by convention rather than explicit import, and framework "auto-wiring" (Spring `@Component`
  scanning, Django app registries, Flask blueprints registered by string path) — the AST extraction has no
  way to see a reference that only exists at runtime via reflection or string-based lookup. These will
  show zero fan-in and look like entry points even though a framework wires them up indirectly.
- **Configuration-referenced files** (a `Dockerfile`'s `CMD`, a `package.json` `"main"`/`"bin"` field, a
  `Procfile`, a CI job's script step) — these ARE genuinely the real entry points, but Graphify's AST
  extraction doesn't parse non-code config files by default, so it can't confirm the reference either way.
  Cross-check the candidate list against these files manually; they're usually the fastest way to confirm
  a real entry point versus a false positive.

## False negatives (a real entry point, but not flagged)

- **Test files.** `tests/test_*.py`-style files are almost always invoked externally (by a test runner)
  with zero internal fan-in too — they'll correctly show up as "zero fan-in," but they aren't useful
  "entry points" in the application sense. This skill doesn't filter them out by naming convention because
  that convention varies too much across stacks to hardcode reliably; when reading the candidate list,
  mentally exclude anything under a `test`/`spec`/`__tests__` path.
- **A file only reachable via a relation type `--code-only` extraction doesn't capture at all** (e.g. a
  route registered by string path in a router config, rather than a direct import) will show zero fan-in
  for the wrong reason — it looks like "nothing calls this" when actually "the AST pass couldn't see the
  call." `--mode deep`'s semantic LLM-assisted extraction is more likely to catch these; `--code-only`
  trades that recall for being free and deterministic.

## What to actually do with this

Treat the candidate list as a **starting point for a human/agent to confirm**, not a final answer —
exactly the same posture `/assess-repo` takes toward every heuristic-derived metric (`confidence:
"derived"`, never `"measured"`, when a real judgment call like this is involved). Cross-referencing against
naming convention (`main.*`, `app.*`, `index.*`, `cmd/**/main.go`) raises confidence but doesn't confirm it
alone; cross-referencing against a Dockerfile `CMD`, a `package.json` `bin`/`main`, or a WSGI/ASGI app
factory reference is the strongest available confirmation this skill can offer without running the code.
