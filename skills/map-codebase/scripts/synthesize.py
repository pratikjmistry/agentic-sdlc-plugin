#!/usr/bin/env python3
"""Parses an already-extracted graphify-out/graph.json + .graphify_analysis.json
(produced by `graphify extract`/`cluster-only`, invoked separately per
SKILL.md's Step 2-3) and:

1. Computes what Graphify itself doesn't report as a field — cyclic
   dependencies, candidate entry points, fan_in/fan_out split, community
   names (when --label wasn't used) — see references/graph-schema.md for
   exactly why each of these needs in-house computation.
2. Writes docs/codebase-map.md from assets/templates/codebase-map.md.tmpl.
3. Refreshes a zones.json (from a prior /assess-repo run) with real
   coupling_score/blast_radius, if one is pointed at.

Zero third-party dependencies — see references/graph-schema.md for why this
doesn't use networkx even though Graphify itself does internally.

Usage:
    python3 synthesize.py <target-repo-path> [--out DIR] [--zones PATH]
"""
from __future__ import annotations

import argparse
import json
import string
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "assets" / "templates" / "codebase-map.md.tmpl"

STRUCTURAL_RELATIONS_EXCLUDED = {"contains", "method", "attribute", "field", "parameter"}
ENTRY_POINT_NAME_HINTS = {"main", "app", "index", "server", "cli", "__main__"}


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def load_graph(repo_path: Path) -> tuple[dict, dict | None] | None:
    graph_path = repo_path / "graphify-out" / "graph.json"
    if not graph_path.exists():
        return None
    graph = _load_json(graph_path)
    if graph is None:
        return None
    analysis_path = repo_path / "graphify-out" / ".graphify_analysis.json"
    analysis = _load_json(analysis_path) if analysis_path.exists() else None
    return graph, analysis


def fan_in_out(links: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    fan_out: dict[str, int] = {}
    fan_in: dict[str, int] = {}
    for link in links:
        source, target = link.get("source"), link.get("target")
        if source is not None:
            fan_out[source] = fan_out.get(source, 0) + 1
        if target is not None:
            fan_in[target] = fan_in.get(target, 0) + 1
    return fan_in, fan_out


def strongly_connected_components(graph: dict[str, list[str]]) -> list[list[str]]:
    """Iterative Tarjan's SCC — see references/graph-schema.md for why this
    is hand-rolled rather than a networkx import."""
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


def compute_cycles(nodes: list[dict], links: list[dict]) -> list[list[dict]]:
    """Returns cyclic groups as lists of node dicts (not just IDs) so the
    report can show real labels/paths."""
    nodes_by_id = {n["id"]: n for n in nodes if "id" in n}
    graph: dict[str, list[str]] = {n["id"]: [] for n in nodes if "id" in n}
    for link in links:
        if link.get("relation") in STRUCTURAL_RELATIONS_EXCLUDED:
            continue
        source, target = link.get("source"), link.get("target")
        if source in graph:
            graph[source].append(target)
    sccs = strongly_connected_components(graph)
    return [[nodes_by_id[nid] for nid in c if nid in nodes_by_id] for c in sccs if len(c) > 1]


def is_file_level_node(node: dict) -> bool:
    source_file = node.get("source_file")
    if not source_file:
        return False
    return node.get("label") == Path(source_file).name


def detect_entry_points(nodes: list[dict], fan_in: dict[str, int]) -> list[dict]:
    candidates = []
    for n in nodes:
        if not is_file_level_node(n):
            continue
        if fan_in.get(n["id"], 0) > 0:
            continue
        stem = Path(n.get("source_file", "")).stem.lower()
        candidates.append({
            "path": n.get("source_file", ""),
            "name_hint_match": stem in ENTRY_POINT_NAME_HINTS,
        })
    candidates.sort(key=lambda c: (not c["name_hint_match"], c["path"]))
    return candidates


def community_name(member_ids: list[str], nodes_by_id: dict[str, dict]) -> str:
    """Names a community after its most common *full* source file's stem, not
    just the top-level directory — communities are typically clustered around
    one or two files' worth of symbols, and most repos have a single top-level
    `src/`, so naming by first path segment alone collapses distinct
    communities (e.g. models.py's and service.py's) to the same "src" name."""
    source_files = [nodes_by_id[nid]["source_file"] for nid in member_ids
                     if nid in nodes_by_id and nodes_by_id[nid].get("source_file")]
    if not source_files:
        return "(unlabeled)"
    most_common_file = Counter(source_files).most_common(1)[0][0]
    return Path(most_common_file).stem


def summarize_communities(analysis: dict | None, nodes_by_id: dict[str, dict]) -> list[dict]:
    if not analysis or not isinstance(analysis.get("communities"), dict):
        return []
    cohesion = analysis.get("cohesion", {})
    summary = []
    for community_id, member_ids in analysis["communities"].items():
        files = sorted({nodes_by_id[nid]["source_file"] for nid in member_ids
                        if nid in nodes_by_id and nodes_by_id[nid].get("source_file")})
        summary.append({
            "id": community_id,
            "name": community_name(member_ids, nodes_by_id),
            "member_count": len(member_ids),
            "cohesion": cohesion.get(community_id),
            "files": files,
        })
    summary.sort(key=lambda c: c["member_count"], reverse=True)
    return summary


def summarize_hubs(analysis: dict | None, nodes_by_id: dict[str, dict],
                    fan_in: dict[str, int], fan_out: dict[str, int]) -> list[dict]:
    if not analysis or not isinstance(analysis.get("gods"), list):
        return []
    hubs = []
    for g in analysis["gods"]:
        node = nodes_by_id.get(g.get("id"), {})
        hubs.append({
            "label": g.get("label", ""),
            "path": node.get("source_file", ""),
            "fan_in": fan_in.get(g.get("id"), 0),
            "fan_out": fan_out.get(g.get("id"), 0),
            "degree": g.get("degree", 0),
        })
    return hubs


def _md_table(headers: list[str], rows: list[list]) -> str:
    if not rows:
        return "*(none)*"
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def render_report(repo_name: str, short_sha: str, graph: dict, analysis: dict | None,
                   nodes: list[dict], links: list[dict], entry_points: list[dict],
                   communities: list[dict], hubs: list[dict], surprises: list[dict],
                   cycles: list[list[dict]]) -> str:
    template = string.Template(TEMPLATE_PATH.read_text())

    entry_points_table = _md_table(
        ["Path", "Name matches common entry-point convention?"],
        [[e["path"], "Yes" if e["name_hint_match"] else "No"] for e in entry_points[:20]],
    )
    if len(entry_points) > 20:
        entry_points_table += f"\n\n*(+{len(entry_points) - 20} more — see graph.json directly)*"

    communities_table = _md_table(
        ["Community", "Files", "Cohesion", "Sample paths"],
        [[c["name"], c["member_count"], c["cohesion"], ", ".join(c["files"][:3]) + ("…" if len(c["files"]) > 3 else "")]
         for c in communities],
    )

    hubs_table = _md_table(
        ["Symbol", "Path", "Fan-in", "Fan-out", "Total degree"],
        [[h["label"], h["path"], h["fan_in"], h["fan_out"], h["degree"]] for h in hubs],
    )

    surprises_table = _md_table(
        ["Source", "Target", "Relation", "Why"],
        [[s.get("source", ""), s.get("target", ""), s.get("relation", ""), s.get("why", "")] for s in surprises],
    )

    if cycles:
        cycles_lines = []
        for i, group in enumerate(cycles, start=1):
            labels = ", ".join(f"`{n.get('label', n.get('id', '?'))}`" for n in group)
            cycles_lines.append(f"{i}. {labels}")
        cycles_section = "\n".join(cycles_lines)
    else:
        cycles_section = "None detected."

    return template.substitute(
        repo_name=repo_name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        short_sha=short_sha,
        extraction_mode="code-only (deterministic, no LLM)" if (analysis or {}).get("tokens", {}).get("input", 0) == 0 else "deep (LLM-assisted)",
        node_count=len(nodes),
        edge_count=len(links),
        community_count=len(communities),
        files_covered=len({n.get("source_file") for n in nodes if n.get("source_file")}),
        cycle_count=len(cycles),
        entry_points_section=entry_points_table,
        communities_section=communities_table,
        hubs_section=hubs_table,
        surprises_section=surprises_table,
        cycles_section=cycles_section,
    )


def refresh_zones(zones_path: Path, nodes: list[dict], links: list[dict]) -> int:
    """Updates coupling_score/blast_radius in place. Returns count of zones matched."""
    zones = _load_json(zones_path)
    if not isinstance(zones, list):
        return 0

    node_by_source_file: dict[str, list[dict]] = {}
    for n in nodes:
        sf = n.get("source_file")
        if sf:
            node_by_source_file.setdefault(sf, []).append(n)

    matched = 0
    for zone in zones:
        zone_node_ids: set[str] = set()
        zone_communities: set = set()
        for path in zone.get("paths", []):
            for n in node_by_source_file.get(path, []):
                zone_node_ids.add(n["id"])
                if "community" in n:
                    zone_communities.add(n["community"])

        if not zone_node_ids:
            zone["blast_radius"] = "unknown"
            zone["coupling_score"] = None
            continue

        matched += 1
        internal_edges = 0
        external_edges = 0
        incoming_internal = 0
        incoming_external = 0
        for link in links:
            source_in, target_in = link.get("source") in zone_node_ids, link.get("target") in zone_node_ids
            if source_in and target_in:
                internal_edges += 1
            elif source_in or target_in:
                external_edges += 1
            if target_in and not source_in:
                incoming_external += 1
            elif target_in and source_in:
                incoming_internal += 1

        total_edges = internal_edges + external_edges
        coupling_score = round(external_edges / total_edges, 3) if total_edges else 0.0
        total_incoming = incoming_internal + incoming_external
        contained_ratio = (incoming_internal / total_incoming) if total_incoming else 1.0

        zone["coupling_score"] = coupling_score
        zone["blast_radius"] = "contained" if contained_ratio > 0.8 else "wide"

    zones_path.write_text(json.dumps(zones, indent=2) + "\n")
    return matched


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Synthesize a codebase map from an existing graphify-out/")
    parser.add_argument("repo_path")
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--zones", type=str, default=None)
    args = parser.parse_args(argv)

    repo_path = Path(args.repo_path).expanduser().resolve()
    loaded = load_graph(repo_path)
    if loaded is None:
        print(
            f"✗ No graphify-out/graph.json found under {repo_path}. Run `graphify extract {repo_path} "
            "--code-only` first (see SKILL.md Step 2).",
            file=sys.stderr,
        )
        return 1

    graph, analysis = loaded
    nodes = graph.get("nodes", []) if isinstance(graph.get("nodes"), list) else []
    links = graph.get("links", []) if isinstance(graph.get("links"), list) else []
    nodes_by_id = {n["id"]: n for n in nodes if isinstance(n, dict) and "id" in n}

    fan_in, fan_out = fan_in_out(links)
    cycles = compute_cycles(nodes, links)
    entry_points = detect_entry_points(nodes, fan_in)
    communities = summarize_communities(analysis, nodes_by_id)
    hubs = summarize_hubs(analysis, nodes_by_id, fan_in, fan_out)
    surprises = (analysis or {}).get("surprises", []) if isinstance((analysis or {}).get("surprises"), list) else []

    repo_name = repo_path.name
    short_sha = "not a git repository"
    try:
        result = subprocess.run(["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
                                  capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            short_sha = result.stdout.strip()
    except OSError:
        pass

    report = render_report(repo_name, short_sha, graph, analysis, nodes, links,
                             entry_points, communities, hubs, surprises, cycles)

    out_dir = Path(args.out) if args.out else repo_path / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "codebase-map.md"
    out_path.write_text(report)
    print(f"✅ wrote {out_path}")
    print(f"   {len(nodes)} nodes, {len(links)} edges, {len(communities)} communities, "
          f"{len(cycles)} cyclic group(s), {len(entry_points)} candidate entry point(s)")

    if args.zones:
        zones_path = Path(args.zones)
        if zones_path.exists():
            matched = refresh_zones(zones_path, nodes, links)
            print(f"✅ refreshed {matched} zone(s) in {zones_path}")
        else:
            print(f"   zones file not found at {zones_path} — skipped (this skill doesn't require /assess-repo to have run)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
