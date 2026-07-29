#!/usr/bin/env python3
"""Layer 2 provider: structural metrics (the `structure.*` family) via Graphify
(`uv tool install graphifyy`) — local, deterministic tree-sitter AST parsing
via `graphify extract --code-only`, no model calls, no running server or graph
DB.

Schema verified against a real `graphify` install (0.9.29) run against a small
synthetic repo — this replaced an earlier version of this file that guessed at
a `nodes`/`edges`/`modules`/`cycles`/`parser_coverage` shape which turned out
to be wrong on every field. The real shape:

- `graphify-out/graph.json` — NetworkX node-link format: top-level
  `directed`/`multigraph`/`graph`/`nodes`/`links`/`hyperedges`. Each node has
  `id`, `label`, `file_type`, `source_file`, `source_location`, `community`.
  Each link has `source`, `target`, `relation` (e.g. `imports_from`, `calls`,
  `contains`, `method`), `confidence`, `weight`.
- `graphify-out/.graphify_analysis.json` — sidecar file, NOT part of
  `graph.json`: `communities` (community_id -> list of node ids), `cohesion`
  (community_id -> float), `gods` (list of `{id, label, degree}`, the
  highest-degree hub nodes), `surprises` (cross-community edges Graphify's own
  heuristics flagged as unexpected), `tokens` (LLM usage — 0 for
  `--code-only`).

Graphify itself reports no `parser_coverage`, `cycles`, or `cross_stack_edge`
concept anywhere in its output — those three are computed in-house here, on
top of the real graph, rather than read off a field that doesn't exist:
- `parser_coverage_pct`: distinct `source_file` values referenced by any node,
  divided by `total_file_count` (the caller's already-computed included-file
  count) — an approximation, not an exact "files Graphify's grammars support"
  figure, since we don't have that denominator directly.
- `cyclic_dependency_count`: strongly-connected-components (size > 1) over a
  dependency-relevant subset of edges, via a hand-rolled iterative Tarjan's
  algorithm — no `networkx` dependency here even though Graphify uses it
  internally, because that copy lives inside Graphify's own isolated `uv tool`
  environment and is not importable from this plugin's scripts.
- `cross_stack_edge_count`: an edge whose source and target nodes' file
  extensions differ — a coarse proxy for "different stack" (e.g. counts
  `.jsx`/`.js` as different, which is an over-count for same-ecosystem code),
  documented as such rather than presented as exact.

Clean-skip behavior (fully verified): if neither an existing
`graphify-out/graph.json` nor a `graphify` binary is found, every `structure.*`
metric is reported `unavailable` with a clear reason — Phase 0 never requires
this provider.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

STRUCTURAL_RELATIONS_EXCLUDED = {"contains", "method", "attribute", "field", "parameter"}
GOD_NODE_MIN_DEGREE = 10


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def _unavailable(notes: str) -> dict:
    return _envelope(None, "", "", "unavailable", None, notes)


def _find_existing_graph(repo_path: Path) -> Path | None:
    candidate = repo_path / "graphify-out" / "graph.json"
    return candidate if candidate.exists() else None


def _run_graphify(repo_path: Path) -> Path | None:
    """Runs the real, verified CLI invocation: `graphify extract <path> --code-only`.
    Deterministic AST-only extraction, no LLM calls, no API key needed — matches
    this provider's "no model calls" contract. Falls back silently on any
    failure (missing binary, non-zero exit, timeout), which clean-skips this
    whole provider rather than crashing collect.py."""
    if shutil.which("graphify") is None:
        return None
    try:
        subprocess.run(["graphify", "extract", str(repo_path), "--code-only"],
                        capture_output=True, text=True, timeout=300, check=False)
    except Exception:
        return None
    graph_path = repo_path / "graphify-out" / "graph.json"
    return graph_path if graph_path.exists() else None


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _strongly_connected_components(graph: dict[str, list[str]]) -> list[list[str]]:
    """Iterative Tarjan's SCC — iterative to avoid Python's recursion limit on
    large real graphs. No third-party dependency (see module docstring)."""
    index_counter = [0]
    stack: list[str] = []
    lowlink: dict[str, int] = {}
    index: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    result: list[list[str]] = []

    def strongconnect(start: str) -> None:
        work = [(start, iter(graph.get(start, [])))]
        index[start] = index_counter[0]
        lowlink[start] = index_counter[0]
        index_counter[0] += 1
        stack.append(start)
        on_stack[start] = True

        while work:
            v, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = index_counter[0]
                    lowlink[w] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(w)
                    on_stack[w] = True
                    work.append((w, iter(graph.get(w, []))))
                    advanced = True
                    break
                elif on_stack.get(w):
                    lowlink[v] = min(lowlink[v], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[v])
            if lowlink[v] == index[v]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == v:
                        break
                result.append(component)

    for node in list(graph.keys()):
        if node not in index:
            strongconnect(node)
    return result


def _compute_cycles(nodes: list[dict], links: list[dict]) -> int:
    graph: dict[str, list[str]] = {n["id"]: [] for n in nodes if "id" in n}
    for link in links:
        if link.get("relation") in STRUCTURAL_RELATIONS_EXCLUDED:
            continue
        source, target = link.get("source"), link.get("target")
        if source in graph:
            graph[source].append(target)
    sccs = _strongly_connected_components(graph)
    return sum(1 for c in sccs if len(c) > 1)


def _fan_in_out(links: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    fan_out: dict[str, int] = {}
    fan_in: dict[str, int] = {}
    for link in links:
        source, target = link.get("source"), link.get("target")
        if source is not None:
            fan_out[source] = fan_out.get(source, 0) + 1
        if target is not None:
            fan_in[target] = fan_in.get(target, 0) + 1
    return fan_in, fan_out


def _cross_stack_edge_count(nodes_by_id: dict[str, dict], links: list[dict]) -> int:
    count = 0
    for link in links:
        source_node = nodes_by_id.get(link.get("source"))
        target_node = nodes_by_id.get(link.get("target"))
        if not source_node or not target_node:
            continue
        source_file, target_file = source_node.get("source_file"), target_node.get("source_file")
        if not source_file or not target_file:
            continue
        if Path(source_file).suffix != Path(target_file).suffix:
            count += 1
    return count


def collect(repo_path: Path, total_file_count: int) -> dict[str, dict]:
    repo_path = Path(repo_path)
    graph_path = _find_existing_graph(repo_path) or _run_graphify(repo_path)

    metric_ids = ["parser_coverage_pct", "module_count", "community_count", "god_nodes",
                  "cyclic_dependency_count", "avg_fan_out", "max_fan_out", "cross_stack_edge_count"]

    if graph_path is None:
        reason = ("Graphify not installed and no graphify-out/graph.json present — install via "
                   "`uv tool install graphifyy` for structural metrics, or run /map-codebase to "
                   "produce the graph directly")
        return {f"structure.{name}": _unavailable(reason) for name in metric_ids}

    graph = _load_json(graph_path)
    if graph is None:
        reason = f"found {graph_path} but it wasn't valid JSON — Graphify run may have failed partway"
        return {f"structure.{name}": _unavailable(reason) for name in metric_ids}

    nodes = graph.get("nodes", []) if isinstance(graph.get("nodes"), list) else []
    links = graph.get("links", []) if isinstance(graph.get("links"), list) else []
    nodes_by_id = {n["id"]: n for n in nodes if isinstance(n, dict) and "id" in n}

    analysis_path = repo_path / "graphify-out" / ".graphify_analysis.json"
    analysis = _load_json(analysis_path) if analysis_path.exists() else None

    fan_in, fan_out = _fan_in_out(links)

    source_files = {n.get("source_file") for n in nodes if n.get("source_file")}
    parser_coverage_pct = (
        round(100 * len(source_files) / total_file_count, 2) if total_file_count else None
    )

    metrics: dict[str, dict] = {}

    if parser_coverage_pct is not None:
        metrics["structure.parser_coverage_pct"] = _envelope(
            parser_coverage_pct, "pct", "graphify", "estimated", 100,
            "distinct source_file values referenced in graph.json's nodes, over the caller's "
            "included-file count — approximates 'files Graphify's grammars actually covered', "
            "not an exact figure Graphify itself reports",
        )
    else:
        metrics["structure.parser_coverage_pct"] = _unavailable("total_file_count was 0 or unavailable")

    metrics["structure.module_count"] = (
        _envelope(len(source_files), "count", "graphify", "measured", 100,
                  "count of distinct source files with at least one extracted node")
        if source_files else _unavailable("graph.json has no nodes with a source_file")
    )

    if analysis and isinstance(analysis.get("communities"), dict):
        metrics["structure.community_count"] = _envelope(
            len(analysis["communities"]), "count", "graphify", "measured", 100,
            "from .graphify_analysis.json's communities (graph-clustering output, run via `graphify cluster-only`)",
        )
    else:
        metrics["structure.community_count"] = _unavailable(
            "no .graphify_analysis.json communities found — run `graphify cluster-only` on this repo first")

    if analysis and isinstance(analysis.get("gods"), list):
        god_nodes = []
        for g in analysis["gods"]:
            node_id = g.get("id")
            node = nodes_by_id.get(node_id, {})
            if g.get("degree", 0) < GOD_NODE_MIN_DEGREE:
                continue
            god_nodes.append({
                "symbol": g.get("label", ""),
                "path": node.get("source_file", ""),
                "fan_in": fan_in.get(node_id, 0),
                "fan_out": fan_out.get(node_id, 0),
            })
        metrics["structure.god_nodes"] = _envelope(
            god_nodes, "list", "graphify", "derived", 100,
            f"from .graphify_analysis.json's gods (highest total-degree nodes), filtered to degree >= {GOD_NODE_MIN_DEGREE}; "
            "fan_in/fan_out split computed here from graph.json's links, not from Graphify's own (undirected) degree figure",
        )
    else:
        metrics["structure.god_nodes"] = _unavailable(
            "no .graphify_analysis.json gods found — run `graphify cluster-only` on this repo first")

    metrics["structure.cyclic_dependency_count"] = _envelope(
        _compute_cycles(nodes, links), "count", "in-house", "derived", 100,
        f"strongly-connected-components (size > 1) over graph.json's links, excluding structural "
        f"relations {sorted(STRUCTURAL_RELATIONS_EXCLUDED)} — Graphify itself reports no cycle count",
    )

    if fan_out:
        metrics["structure.avg_fan_out"] = _envelope(
            round(sum(fan_out.values()) / len(fan_out), 2), "count", "in-house", "derived", 100,
            "computed from graph.json's links (out-degree per node), not a Graphify-native field")
        metrics["structure.max_fan_out"] = _envelope(
            max(fan_out.values()), "count", "in-house", "derived", 100, "")
    else:
        metrics["structure.avg_fan_out"] = _unavailable("graph.json has no links")
        metrics["structure.max_fan_out"] = _unavailable("graph.json has no links")

    metrics["structure.cross_stack_edge_count"] = _envelope(
        _cross_stack_edge_count(nodes_by_id, links), "count", "in-house", "estimated", 100,
        "edges whose endpoints' file extensions differ — a coarse proxy for 'different stack' "
        "(e.g. counts .jsx vs .js as different), not a real language/framework classification",
    )

    return metrics
