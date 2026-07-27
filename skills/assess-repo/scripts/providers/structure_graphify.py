#!/usr/bin/env python3
"""Layer 2 provider: structural metrics (the `structure.*` family) via Graphify
(`uv tool install graphifyy`) — local, deterministic tree-sitter AST parsing,
no model calls, no running server or graph DB.

IMPORTANT — schema caveat: Graphify is not installed in this development
environment, and its `graph.json` output schema was not available to verify
against. The shape assumed below (`nodes`/`edges`/`modules`/`parser_coverage`/
`cycles`, with per-node `fan_in`/`fan_out`) is a reasonable best guess for what
a tree-sitter-based structural graph tool would emit, not a confirmed schema.
Every field access below is defensive (guarded, falls back to `unavailable`
per-metric rather than crashing the whole provider) specifically because of
this uncertainty. Treat this file as needing a revision pass against a real
`graphify-out/graph.json` before trusting its output in production — that
revision is a bounded follow-up, not a redesign, once a real sample is
available.

Clean-skip behavior (this part IS fully verified): if neither an existing
`graphify-out/graph.json` nor a `graphify` binary is found, every `structure.*`
metric is reported `unavailable` with a clear reason — Phase 0 never requires
this provider.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def _unavailable(notes: str) -> dict:
    return _envelope(None, "", "", "unavailable", None, notes)


SCHEMA_CAVEAT = "Graphify graph.json schema unverified in this build — see module docstring"


def _find_existing_graph(repo_path: Path) -> Path | None:
    candidate = repo_path / "graphify-out" / "graph.json"
    return candidate if candidate.exists() else None


def _run_graphify(repo_path: Path) -> Path | None:
    """Best-effort — not exercised against a real graphify binary in this
    environment (none installed). Invocation syntax is a guess; falls back
    silently on any failure, which clean-skips this whole provider."""
    if shutil.which("graphify") is None:
        return None
    out_dir = repo_path / "graphify-out"
    try:
        subprocess.run(["graphify", "analyze", str(repo_path), "--out", str(out_dir)],
                        capture_output=True, text=True, timeout=300, check=False)
    except Exception:
        return None
    graph_path = out_dir / "graph.json"
    return graph_path if graph_path.exists() else None


def _parse_graph(graph_path: Path) -> dict | None:
    try:
        return json.loads(graph_path.read_text())
    except (OSError, ValueError):
        return None


def collect(repo_path: Path, total_file_count: int) -> dict[str, dict]:
    repo_path = Path(repo_path)
    graph_path = _find_existing_graph(repo_path) or _run_graphify(repo_path)

    if graph_path is None:
        reason = ("Graphify not installed and no graphify-out/graph.json present — install via "
                   "`uv tool install graphifyy` for structural metrics, or Phase 2's /map-codebase "
                   "will produce a deeper graph")
        return {f"structure.{name}": _unavailable(reason) for name in [
            "parser_coverage_pct", "module_count", "community_count", "god_nodes",
            "cyclic_dependency_count", "avg_fan_out", "max_fan_out", "cross_stack_edge_count",
        ]}

    graph = _parse_graph(graph_path)
    if graph is None:
        reason = f"found {graph_path} but it wasn't valid JSON — Graphify run may have failed partway"
        return {f"structure.{name}": _unavailable(reason) for name in [
            "parser_coverage_pct", "module_count", "community_count", "god_nodes",
            "cyclic_dependency_count", "avg_fan_out", "max_fan_out", "cross_stack_edge_count",
        ]}

    nodes = graph.get("nodes", []) if isinstance(graph.get("nodes"), list) else []
    edges = graph.get("edges", []) if isinstance(graph.get("edges"), list) else []
    modules = graph.get("modules", []) if isinstance(graph.get("modules"), list) else []
    cycles = graph.get("cycles", []) if isinstance(graph.get("cycles"), list) else []
    coverage_info = graph.get("parser_coverage", {}) if isinstance(graph.get("parser_coverage"), dict) else {}

    parsed_files = coverage_info.get("parsed_files")
    total_files = coverage_info.get("total_files") or total_file_count
    parser_coverage_pct = (
        round(100 * parsed_files / total_files, 2) if parsed_files is not None and total_files else None
    )

    fan_outs = [n.get("fan_out") for n in nodes if isinstance(n, dict) and isinstance(n.get("fan_out"), (int, float))]
    god_nodes = [
        {"symbol": n.get("symbol", ""), "path": n.get("path", ""),
         "fan_in": n.get("fan_in", 0), "fan_out": n.get("fan_out", 0)}
        for n in nodes if isinstance(n, dict) and (n.get("fan_out", 0) or 0) >= 20
    ]

    metrics: dict[str, dict] = {}

    if parser_coverage_pct is not None:
        metrics["structure.parser_coverage_pct"] = _envelope(
            parser_coverage_pct, "pct", "graphify", "measured", 100, SCHEMA_CAVEAT)
    else:
        metrics["structure.parser_coverage_pct"] = _unavailable(
            f"graph.json present but missing parser_coverage info — {SCHEMA_CAVEAT}")

    metrics["structure.module_count"] = (
        _envelope(len(modules), "count", "graphify", "measured", 100, SCHEMA_CAVEAT) if modules
        else _unavailable(f"no modules[] in graph.json — {SCHEMA_CAVEAT}")
    )
    metrics["structure.community_count"] = _unavailable(
        f"community detection not represented in the assumed graph.json shape — {SCHEMA_CAVEAT}")
    metrics["structure.god_nodes"] = _envelope(
        god_nodes, "list", "graphify", "derived", 100,
        f"fan_out >= 20 threshold, in-house on top of graphify's node list — {SCHEMA_CAVEAT}")
    metrics["structure.cyclic_dependency_count"] = (
        _envelope(len(cycles), "count", "graphify", "measured", 100, SCHEMA_CAVEAT) if graph.get("cycles") is not None
        else _unavailable(f"no cycles[] in graph.json — {SCHEMA_CAVEAT}")
    )
    if fan_outs:
        metrics["structure.avg_fan_out"] = _envelope(round(sum(fan_outs) / len(fan_outs), 2), "count", "graphify", "derived", 100, SCHEMA_CAVEAT)
        metrics["structure.max_fan_out"] = _envelope(max(fan_outs), "count", "graphify", "measured", 100, SCHEMA_CAVEAT)
    else:
        metrics["structure.avg_fan_out"] = _unavailable(f"no per-node fan_out in graph.json — {SCHEMA_CAVEAT}")
        metrics["structure.max_fan_out"] = _unavailable(f"no per-node fan_out in graph.json — {SCHEMA_CAVEAT}")

    metrics["structure.cross_stack_edge_count"] = _unavailable(
        f"cross-stack edge classification not represented in the assumed graph.json shape — {SCHEMA_CAVEAT}")

    return metrics
