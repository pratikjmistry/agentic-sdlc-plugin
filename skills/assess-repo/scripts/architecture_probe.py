#!/usr/bin/env python3
"""Layer 1 provider for the `architecture.*` metric family — cheap, Phase-0
heuristic signals of architectural/design-pattern style. Lives at scripts/
root (like exclusions.py/context_ops_probe.py), not under providers/, for the
same reason context_ops_probe.py does: a cross-cutting concern that doesn't
belong to one stack/tool.

Deliberately NOT wired into any rubric.yaml dimension — purely informational
for the report's Quantitative Codebase Overview. Every value here is
`confidence: "estimated"`, never higher: this is directory-naming and
dependency-convention pattern-matching, not real AST-based analysis (that's
/map-codebase's job, via Graphify's real dependency graph). Never guesses a
pattern from a single weak signal — each pattern below requires at least two
corroborating directory names, or an explicit dependency match.
"""
from __future__ import annotations

from pathlib import Path

from context_ops_probe import _search_manifests_and_config

STATE_MANAGEMENT_KEYWORDS = [r"\bredux\b", r"@reduxjs/toolkit", r"\bvuex\b", r"\bmobx\b",
                              r"\bpinia\b", r"\bngrx\b"]
ENTRYPOINT_NAME_HINTS = {"main", "app", "index", "program", "__main__"}
FLAT_STRUCTURE_MAX_DEPTH = 2


def _envelope(value, unit, source, confidence, coverage_pct, notes) -> dict:
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def _directories(included_files: list[str]) -> set[str]:
    dirs = set()
    for f in included_files:
        for part_count in range(1, len(Path(f).parts)):
            dirs.add("/".join(Path(f).parts[:part_count]).lower())
        parts = Path(f).parts[:-1]
        for p in parts:
            dirs.add(p.lower())
    return dirs


def detect_mvc(directories: set[str]) -> dict | None:
    hits = [d for d in ["controllers", "models", "views"] if d in directories]
    if len(hits) >= 2:
        return {"pattern": "MVC", "confidence": "estimated",
                 "evidence": f"directories present: {', '.join(sorted(hits))}"}
    return None


def detect_layered_repository(directories: set[str]) -> dict | None:
    has_services = "services" in directories
    has_repos = "repositories" in directories or "repository" in directories
    if has_services and has_repos:
        return {"pattern": "Layered / Repository", "confidence": "estimated",
                 "evidence": "both services/ and repositories/ directories present"}
    return None


def detect_state_management(repo_path: Path, included_files: list[str]) -> dict | None:
    if _search_manifests_and_config(repo_path, included_files, STATE_MANAGEMENT_KEYWORDS):
        return {"pattern": "Flux-style state management", "confidence": "estimated",
                 "evidence": "redux/vuex/mobx/pinia/ngrx keyword found in a manifest or config file"}
    return None


def detect_simple_monolithic(included_files: list[str]) -> dict | None:
    root_entrypoints = [
        f for f in included_files
        if "/" not in f and Path(f).stem.lower() in ENTRYPOINT_NAME_HINTS
    ]
    if not root_entrypoints:
        return None
    max_depth = max((len(Path(f).parts) for f in included_files), default=1)
    if max_depth <= FLAT_STRUCTURE_MAX_DEPTH:
        return {"pattern": "Simple / monolithic", "confidence": "estimated",
                 "evidence": f"root-level entrypoint ({root_entrypoints[0]}) with shallow directory depth ({max_depth})"}
    return None


def style_summary(patterns: list[dict]) -> str:
    if not patterns:
        return "inconclusive — no directory-naming or dependency-convention signal matched"
    return " + ".join(p["pattern"] for p in patterns)


def collect(repo_path: Path, included_files: list[str]) -> dict[str, dict]:
    repo_path = Path(repo_path)
    directories = _directories(included_files)

    detectors = [
        detect_mvc(directories),
        detect_layered_repository(directories),
        detect_state_management(repo_path, included_files),
        detect_simple_monolithic(included_files),
    ]
    patterns = [p for p in detectors if p is not None]

    return {
        "architecture.detected_patterns": _envelope(
            patterns, "list", "architecture_probe", "estimated", 100,
            "Phase-0 heuristic only — directory-naming + dependency-convention signals; "
            "not a substitute for /map-codebase's real dependency-graph analysis",
        ),
        "architecture.style_summary": _envelope(
            style_summary(patterns), "", "architecture_probe", "estimated", 100,
            "short label derived from detected_patterns above",
        ),
    }
