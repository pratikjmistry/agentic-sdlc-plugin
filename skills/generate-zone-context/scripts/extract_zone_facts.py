#!/usr/bin/env python3
"""Layer 1 extraction for /generate-zone-context.

Reads `/assess-repo`'s `zones.json` (required — this skill has nothing to
generate without it) and filters `/map-codebase`'s already-computed
`graphify-out/graph.json` + `.graphify_analysis.json` down to each zone's own
paths — a `path in list` membership check, not new graph analysis. Cyclic
dependencies are deliberately NOT handled here: `map-codebase/scripts/
synthesize.py` computes them via hand-rolled SCC but never persists them to
any JSON artifact (only rendered text in `docs/codebase-map.md`), so
re-implementing SCC here just to filter it would duplicate real graph-analysis
logic instead of merely filtering already-computed output. Per-zone cycle
detail is left to the Step 3 generation agent, which reads
`docs/codebase-map.md`'s Cyclic Dependencies section directly (a narrative
read, the same kind `/discover-constitution`'s agents already do).

`load_graph`/`fan_in_out`/community-naming are duplicated from
`skills/map-codebase/scripts/synthesize.py` rather than imported — no skill in
this plugin cross-imports another skill's Python module. These are trivial
edge-counting/formatting helpers, not hub/community *detection* — the
community and hub lists themselves still come straight from Graphify's own
`.graphify_analysis.json` output.

Pure function, no wall-clock/network calls — byte-identical output across
repeated calls on the same input, same discipline as
`skills/discover-constitution/scripts/extract_facts.py`.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


def load_zones(assessment_dir: Path) -> list[dict]:
    path = Path(assessment_dir) / "zones.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run /assess-repo on this repo first; "
            "/generate-zone-context has nothing to generate without zones.json."
        )
    zones = json.loads(path.read_text())
    if not zones:
        raise ValueError(
            f"{path} is empty — /assess-repo found no candidate zones for this repo; "
            "/generate-zone-context has nothing to generate."
        )
    return zones


def load_constitution_facts(assessment_dir: Path) -> dict | None:
    path = Path(assessment_dir) / "constitution-facts.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def find_map_codebase_outputs(repo_path: Path) -> dict:
    repo_path = Path(repo_path)
    codebase_map = repo_path / "docs" / "codebase-map.md"
    graphify_analysis = repo_path / "graphify-out" / ".graphify_analysis.json"
    graph_json = repo_path / "graphify-out" / "graph.json"
    return {
        "codebase_map_present": codebase_map.exists(),
        "codebase_map_path": str(codebase_map) if codebase_map.exists() else None,
        "graphify_analysis_present": graphify_analysis.exists(),
        "graphify_analysis_path": str(graphify_analysis) if graphify_analysis.exists() else None,
        "graph_json_present": graph_json.exists(),
        "graph_json_path": str(graph_json) if graph_json.exists() else None,
    }


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def load_graph(repo_path: Path) -> tuple[dict, dict | None] | None:
    """Mirrors synthesize.py's load_graph() exactly — duplicated, not
    imported. Returns None when graph.json itself is absent/unreadable;
    analysis (.graphify_analysis.json) degrades independently to None."""
    repo_path = Path(repo_path)
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
    """Duplicated verbatim from synthesize.py — edge-counting, not hub
    detection; the hub list itself still comes from Graphify's own gods[]."""
    fan_out: dict[str, int] = {}
    fan_in: dict[str, int] = {}
    for link in links:
        source, target = link.get("source"), link.get("target")
        if source is not None:
            fan_out[source] = fan_out.get(source, 0) + 1
        if target is not None:
            fan_in[target] = fan_in.get(target, 0) + 1
    return fan_in, fan_out


def _community_name(member_ids: list[str], nodes_by_id: dict[str, dict]) -> str:
    """Duplicated from synthesize.py's community_name() — names a community
    after its most common full source file's stem."""
    source_files = [nodes_by_id[nid]["source_file"] for nid in member_ids
                     if nid in nodes_by_id and nodes_by_id[nid].get("source_file")]
    if not source_files:
        return "(unlabeled)"
    most_common_file = Counter(source_files).most_common(1)[0][0]
    return Path(most_common_file).stem


def zone_node_ids(zone: dict, nodes: list[dict]) -> set[str]:
    paths = set(zone.get("paths", []))
    return {n["id"] for n in nodes if n.get("source_file") in paths and "id" in n}


def filter_communities_for_zone(zone_ids: set[str], analysis: dict | None, nodes_by_id: dict[str, dict]) -> list[dict]:
    if not analysis or not isinstance(analysis.get("communities"), dict):
        return []
    cohesion = analysis.get("cohesion", {})
    result = []
    for community_id, member_ids in analysis["communities"].items():
        overlap = [mid for mid in member_ids if mid in zone_ids]
        if not overlap:
            continue
        files = sorted({nodes_by_id[nid]["source_file"] for nid in member_ids
                        if nid in nodes_by_id and nodes_by_id[nid].get("source_file")})
        result.append({
            "id": community_id,
            "name": _community_name(member_ids, nodes_by_id),
            "member_count": len(member_ids),
            "overlap_count": len(overlap),
            "cohesion": cohesion.get(community_id),
            "files": files,
        })
    result.sort(key=lambda c: c["overlap_count"], reverse=True)
    return result


def filter_hubs_for_zone(zone_ids: set[str], analysis: dict | None, nodes_by_id: dict[str, dict],
                          fan_in: dict[str, int], fan_out: dict[str, int]) -> list[dict]:
    if not analysis or not isinstance(analysis.get("gods"), list):
        return []
    hubs = []
    for g in analysis["gods"]:
        gid = g.get("id")
        if gid not in zone_ids:
            continue
        node = nodes_by_id.get(gid, {})
        hubs.append({
            "label": g.get("label", ""),
            "path": node.get("source_file", ""),
            "fan_in": fan_in.get(gid, 0),
            "fan_out": fan_out.get(gid, 0),
            "degree": g.get("degree", 0),
        })
    return hubs


def filter_surprises_for_zone(zone: dict, analysis: dict | None) -> list[dict]:
    if not analysis or not isinstance(analysis.get("surprises"), list):
        return []
    paths = set(zone.get("paths", []))
    return [s for s in analysis["surprises"] if any(sf in paths for sf in (s.get("source_files") or []))]


def cross_reference_risk_areas(zone: dict, constitution_facts: dict | None) -> list[dict]:
    if not constitution_facts:
        return []
    architecture = (constitution_facts.get("facts") or {}).get("architecture") or {}
    risk_areas = architecture.get("risk_areas") or []
    identifiers = {zone.get("name"), zone.get("id")}
    return [ra for ra in risk_areas if ra.get("kind") == "zone_blast_radius" and ra.get("identifier") in identifiers]


def slugify_zone_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name or "").strip("-").lower()
    return slug or "zone"


def zone_paths_dir_is_reconcilable(repo_path: Path, pathspec: str, draft_dir_hint: str) -> tuple[bool, str]:
    """Same 3-branch git-status logic as extract_facts.py's
    ai_context_is_reconcilable(), generalized to any pathspec so
    ai-context/zones/ and .claude/rules/zones/ can each be checked
    independently — a dirty one must not block generation into the other."""
    repo_path = Path(repo_path)
    if not (repo_path / ".git").exists():
        return False, (f"not a git repository (no .git at repo root) — cannot verify {pathspec} is "
                        f"unmodified, draft to {draft_dir_hint} instead of overwriting")
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain", "--", pathspec],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"git status failed ({exc}) — draft to {draft_dir_hint} instead of overwriting"
    if result.returncode != 0:
        return False, f"git status exited {result.returncode} — draft to {draft_dir_hint} instead of overwriting"
    if result.stdout.strip():
        return False, (f"{pathspec} has uncommitted changes (git status is non-empty) — draft to "
                        f"{draft_dir_hint} instead of overwriting")
    return True, (f"{pathspec} matches HEAD (git status is empty) — safe to overwrite; "
                  f"review with `git diff {pathspec}` after")


def zones_dir_is_reconcilable(repo_path: Path) -> tuple[bool, str]:
    """Thin wrapper over zone_paths_dir_is_reconcilable() scoped to
    ai-context/zones/ — kept so existing call sites/tests don't need to change."""
    return zone_paths_dir_is_reconcilable(
        repo_path, "ai-context/zones/", "ai-context/zones/.generate-zone-context-draft/")


def rules_dir_is_reconcilable(repo_path: Path) -> tuple[bool, str]:
    """Same helper scoped to .claude/rules/zones/ — checked independently so a
    dirty ai-context/zones/ doesn't block rule generation and vice versa."""
    return zone_paths_dir_is_reconcilable(
        repo_path, ".claude/rules/zones/", ".claude/rules/zones/.generate-zone-context-draft/")


def build_zone_facts(zone: dict, graph: dict | None, analysis: dict | None, constitution_facts: dict | None) -> dict:
    slug = slugify_zone_name(zone.get("name", ""))
    zone_id = zone.get("id", "ZONE-00")
    output_filename = f"{zone_id}-{slug}.md"
    rule_output_path = f".claude/rules/zones/{zone_id}-{slug}.md"

    nodes = (graph or {}).get("nodes", [])
    links = (graph or {}).get("links", [])
    nodes_by_id = {n["id"]: n for n in nodes if "id" in n}
    fan_in, fan_out = fan_in_out(links)
    zone_ids = zone_node_ids(zone, nodes)

    return {
        "id": zone_id,
        "slug": slug,
        "output_filename": output_filename,
        "rule_output_path": rule_output_path,
        "zone": zone,
        "map_codebase_available": graph is not None,
        "communities": filter_communities_for_zone(zone_ids, analysis, nodes_by_id),
        "hubs": filter_hubs_for_zone(zone_ids, analysis, nodes_by_id, fan_in, fan_out),
        "surprises": filter_surprises_for_zone(zone, analysis),
        "risk_area_cross_references": cross_reference_risk_areas(zone, constitution_facts),
    }


def build_all_zone_facts(assessment_dir: Path, repo_path: Path) -> dict:
    assessment_dir = Path(assessment_dir)
    repo_path = Path(repo_path)

    zones = load_zones(assessment_dir)
    constitution_facts = load_constitution_facts(assessment_dir)
    map_outputs = find_map_codebase_outputs(repo_path)
    graph_result = load_graph(repo_path)
    graph, analysis = graph_result if graph_result else (None, None)
    ai_context_reconcilable, ai_context_detail = zones_dir_is_reconcilable(repo_path)
    rules_reconcilable, rules_detail = rules_dir_is_reconcilable(repo_path)

    return {
        "schema_version": "1.0",
        "source_zones_path": str(Path(assessment_dir) / "zones.json"),
        "map_codebase_outputs": map_outputs,
        "constitution_facts_available": constitution_facts is not None,
        "reconciliation": {
            "ai_context_zones": {"reconcilable": ai_context_reconcilable, "detail": ai_context_detail},
            "rules_zones": {"reconcilable": rules_reconcilable, "detail": rules_detail},
        },
        "zones": [build_zone_facts(z, graph, analysis, constitution_facts) for z in zones],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract per-zone drill-down facts for /generate-zone-context")
    parser.add_argument("assessment_dir", help="Path to /assess-repo's .assessment/<repo>-<shortsha>/ output dir")
    parser.add_argument("repo_path", help="Path to the target repo (checked for ai-context/zones/, docs/codebase-map.md, graphify-out/)")
    parser.add_argument("--out", type=str, default=None, help="Defaults to <assessment_dir>/zone-facts.json")
    args = parser.parse_args(argv)

    facts = build_all_zone_facts(Path(args.assessment_dir), Path(args.repo_path))
    out_path = Path(args.out) if args.out else Path(args.assessment_dir) / "zone-facts.json"
    out_path.write_text(json.dumps(facts, indent=2) + "\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
