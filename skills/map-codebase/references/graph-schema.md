# Graphify's Real Output Schema

Verified by actually installing `graphifyy` (0.9.29) and running `graphify extract . --code-only` +
`graphify cluster-only . --no-label --no-viz` against a real synthetic repo — not guessed. This mirrors
the same verification documented in `skills/assess-repo/scripts/providers/structure_graphify.py`'s
docstring; keep both in sync if Graphify's output shape changes in a future version.

## `graphify-out/graph.json`

NetworkX node-link JSON format (`networkx.node_link_data`), **not** a custom schema:

```json
{
  "directed": false,
  "multigraph": false,
  "graph": {},
  "nodes": [
    {
      "label": "models.py",
      "file_type": "code",
      "source_file": "src/models.py",
      "source_location": "L1",
      "_origin": "ast",
      "id": "src_models",
      "community": 1,
      "norm_label": "models.py"
    }
  ],
  "links": [
    {
      "relation": "imports_from",
      "context": "import",
      "confidence": "EXTRACTED",
      "source_file": "src/service.py",
      "source_location": "L1",
      "weight": 1.0,
      "_origin": "ast",
      "source": "src_service",
      "target": "src_models",
      "confidence_score": 1.0
    }
  ],
  "hyperedges": []
}
```

Observed `relation` values so far: `contains` (structural — a file/class containing a symbol),
`method` (structural — a class containing a method), `imports_from`, `calls`. Treat this as a non-exhaustive
sample from one small repo, not a closed enum — `--mode deep`'s semantic extraction likely adds more
(`inherits`, `uses`, `returns`, etc. are plausible given Graphify's stated scope, unverified here).

**What's absent, despite being intuitive to assume:** no `parser_coverage`, no `cycles`, no `modules`, no
per-node `fan_in`/`fan_out`. Every one of these is computed in-house in `scripts/` — see below.

## `graphify-out/.graphify_analysis.json`

A separate sidecar file, not nested inside `graph.json`:

```json
{
  "communities": { "0": ["src_service", "src_service_create_user", "..."], "1": ["src_models", "..."] },
  "cohesion": { "0": 0.7, "1": 0.5 },
  "gods": [ { "id": "src_models_user", "label": "User", "degree": 5 } ],
  "surprises": [
    {
      "source": "test_create_user()", "target": "create_user()",
      "source_files": ["tests/test_service.py", "src/service.py"],
      "confidence": "EXTRACTED", "relation": "calls",
      "why": "connects across different repos/directories; peripheral node ... unexpectedly reaches hub ..."
    }
  ],
  "questions": [ { "type": "bridge_node", "question": "Why does `User` connect Community 1 to Community 0?", "why": "..." } ],
  "tokens": { "input": 0, "output": 0 }
}
```

`gods[].degree` is **undirected total degree** (in + out combined) — this skill and `structure_graphify.py`
both split it into `fan_in`/`fan_out` themselves using `graph.json`'s `links`, since Graphify doesn't
expose the split. `questions` appeared only after running `cluster-only` in testing, not immediately after
`extract` — treat its presence as version/mode-dependent, not guaranteed.

## What this skill computes in-house (Graphify reports none of these as a field)

| Metric | How it's computed |
|---|---|
| Cyclic dependencies | Strongly-connected-components (size > 1) over `links` filtered to exclude structural relations (`contains`, `method`, `attribute`, `field`, `parameter`) — a hand-rolled iterative Tarjan's algorithm, no `networkx` dependency (see below for why). |
| fan_in / fan_out per node | Count of `links` where the node is `target` / `source`, respectively. |
| Candidate entry points | File-level nodes with zero incoming edges from other nodes in the same graph — see `entry-point-heuristics.md`. |
| Module/community names (without `--label`) | Most common path-prefix among a community's member nodes' `source_file` values — a placeholder better than `Community N`, not a real name. |
| Cross-zone coupling for `zones.json` refresh | Ratio of a zone's edges that cross into a different `community` versus staying within it. |

## Why no `networkx`, even though Graphify itself depends on it

`graphify` is installed via `uv tool install graphifyy`, which creates its own **isolated** virtual
environment — `networkx` (and Graphify's other dependencies) live inside that isolated env and are not
importable from this plugin's own Python process. Adding `networkx` as a separate dependency just for
this skill's own SCC computation was considered and rejected in favor of the ~40-line hand-rolled
iterative Tarjan's implementation already used in `structure_graphify.py` — keeps this skill's own scripts
at zero third-party dependencies beyond the `graphify` CLI binary itself, consistent with the rest of this
plugin's scripts.
