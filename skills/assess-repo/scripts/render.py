#!/usr/bin/env python3
"""Renders assessment-inputs.json + assessment-scores.json into the narrative
outputs: agent-readiness-report.md, remediation-plan.md, zones.json, and a
row appended to portfolio.csv. This is the only place in the skill that
produces prose — it must never disagree with what assessment-scores.json
already computed; it narrates that file, it doesn't re-derive it.

Usage:
    python3 render.py <out_dir> [--portfolio-csv PATH]

<out_dir> must already contain assessment-inputs.json and assessment-scores.json
(from collect.py and score.py).
"""
from __future__ import annotations

import argparse
import csv
import json
import string
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR.parent / "assets" / "templates"

GATE_PHASE_MAP = {
    "GATE_VCS": "Phase 0 (this skill) — resolve a real git source",
    "GATE_BUILD": "Phase 1 — autonomy floor",
    "GATE_TEST_SIGNAL": "Phase 1 — autonomy floor (Phase 3 if a test suite must be created from scratch)",
    "GATE_CI": "Phase 1 — autonomy floor",
    "GATE_POLICY": "Organizational/legal — not an engineering phase",
}

DIMENSION_PHASE_MAP = {
    "build_reproducibility": "Phase 1 — autonomy floor",
    "test_safety_net": "Phase 1 — autonomy floor / Phase 3 — /characterize",
    "change_demand": "Business input — not a phase to remediate",
    "structural_modularity": "Phase 2 — /map-codebase, Phase 5 — /plan-seams",
    "stack_coherence": "Cross-cutting — not owned by a single phase",
    "debt_containability": "Phase 4 — /baseline-debt",
    "context_availability": "Phase 2 — /discover-constitution, /generate-zone-context",
    "blast_radius_containment": "Phase 5 — /plan-seams, Phase 6 — graduated autonomy",
    "analyzability": "Phase 2 — /map-codebase",
}

# Rough, portfolio-triage-level T-shirt sizes only — Phase 0 cannot estimate
# real effort without the deeper analysis those phases themselves perform.
EFFORT_ESTIMATE = {
    "GATE_VCS": "S", "GATE_BUILD": "M", "GATE_TEST_SIGNAL": "L", "GATE_CI": "S", "GATE_POLICY": "S",
    "build_reproducibility": "M", "test_safety_net": "L", "structural_modularity": "L",
    "stack_coherence": "L", "debt_containability": "M", "context_availability": "S",
    "blast_radius_containment": "M", "analyzability": "S",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "*(none)*"
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def build_gates_table(scores: dict) -> str:
    rows = []
    for g in scores["gates"]:
        status = "✅ PASS" if g["passed"] else "⛔ FAIL"
        remediation = g["remediation"] or "—"
        rows.append([g["id"], status, g["reason"], remediation])
    return _md_table(["Gate", "Result", "Reason", "Remediation"], rows)


def build_dimensions_table(scores: dict) -> str:
    rows = []
    for d in scores["dimensions"]:
        score_display = str(d["sub_score"]) if d["available"] else "unavailable"
        rows.append([d["id"], d["weight"], score_display, d["reason"]])
    return _md_table(["Dimension", "Weight", "Sub-score", "Evidence"], rows)


def build_hotspots_table(inputs: dict) -> str:
    hotspots = inputs["metrics"].get("vcs.hotspots", {}).get("value") or []
    rows = [[h["path"], h["commits_365d"], h["loc"], h["authors"], h["hotspot_score"]]
             for h in hotspots[:10]]
    return _md_table(["Path", "Commits (365d)", "LOC", "Authors", "Hotspot Score"], rows)


def build_unavailable_section(inputs: dict) -> str:
    unavailable = [(mid, env["notes"]) for mid, env in inputs["metrics"].items()
                    if env["confidence"] == "unavailable"]
    if not unavailable:
        return "Every metric in this assessment was measured — no gaps to report."
    by_family: dict[str, list[tuple[str, str]]] = {}
    for mid, notes in unavailable:
        family = mid.split(".")[0]
        by_family.setdefault(family, []).append((mid, notes))
    lines = []
    for family in sorted(by_family):
        lines.append(f"**`{family}.*`** ({len(by_family[family])} metric(s) unavailable)")
        # one representative reason per family is usually enough — they mostly share one cause
        sample_notes = by_family[family][0][1]
        lines.append(f"- {sample_notes}")
    return "\n".join(lines)


def build_effort_table(scores: dict) -> str:
    rows = []
    for g in scores["gates"]:
        if not g["passed"]:
            rows.append([GATE_PHASE_MAP[g["id"]], g["id"], EFFORT_ESTIMATE[g["id"]]])
    for d in scores["dimensions"]:
        if d["available"] and d["sub_score"] < 70:
            rows.append([DIMENSION_PHASE_MAP[d["id"]], d["id"], EFFORT_ESTIMATE.get(d["id"], "?")])
        elif not d["available"] and d["id"] != "change_demand":
            rows.append([DIMENSION_PHASE_MAP[d["id"]], f"{d['id']} (unmeasured)", EFFORT_ESTIMATE.get(d["id"], "?")])
    if not rows:
        return "No blockers identified — every gate passed and every measured dimension scored >= 70."
    return _md_table(["Phase", "Item", "Rough effort (S/M/L)"], rows)


def build_blockers_table(scores: dict) -> str:
    rows = []
    for g in scores["gates"]:
        if not g["passed"]:
            rows.append([f"**{g['id']}**", GATE_PHASE_MAP[g["id"]], EFFORT_ESTIMATE[g["id"]],
                          "Engineering (build/test/CI owner)", g["remediation"]])
    for d in scores["dimensions"]:
        if d["available"] and d["sub_score"] < 70:
            rows.append([d["id"], DIMENSION_PHASE_MAP[d["id"]], EFFORT_ESTIMATE.get(d["id"], "?"),
                          "Varies by phase", d["reason"]])
    if not rows:
        return "*(no blockers — see the dimension table in the report for scores.)*"
    return _md_table(["Blocker", "Phase", "Effort", "Suggested Driver", "Detail"], rows)


def build_pilot_zone_section(zones: list[dict]) -> str:
    if not zones:
        return "No candidate zones identified — vcs.hotspots was empty or unavailable."
    top = zones[0]
    lines = [
        f"**`{top['name']}`** ({top['loc']} LOC, churn rank #{top['churn_rank']})",
        "",
        top["rationale"],
        "",
        f"Recommended starting trust level: **{top['recommended_trust_level'] or 'N/A'}**",
    ]
    if top["blockers"]:
        lines.append(f"Blockers: {', '.join(top['blockers'])}")
    return "\n".join(lines)


def carve_zones(inputs: dict, scores: dict, max_zones: int = 5) -> list[dict]:
    hotspots = inputs["metrics"].get("vcs.hotspots", {}).get("value") or []
    if not hotspots:
        return []

    by_dir: dict[str, dict] = {}
    for h in hotspots:
        path = h["path"]
        segments = path.split("/")
        if len(segments) < 2:
            # Root-level files (CHANGES.rst, pyproject.toml, README) aren't a
            # cohesive code area — grouping them as "the root zone" would let
            # unrelated scattered files outrank a real module just by summing
            # individually-high churn scores. They're excluded from zone
            # candidacy entirely, even if individually hot.
            continue
        # Group by the first two path segments (e.g. "src/flask" covers both
        # src/flask/app.py and src/flask/sansio/app.py) rather than the
        # immediate parent directory — this keeps a package's submodules in
        # one zone instead of fragmenting it by every nested subdirectory.
        directory = "/".join(segments[:2])
        zone = by_dir.setdefault(directory, {"paths": [], "loc": 0, "score_sum": 0, "commits": 0})
        zone["paths"].append(path)
        zone["loc"] += h["loc"]
        zone["score_sum"] += h["hotspot_score"]
        zone["commits"] += h["commits_365d"]

    ranked = sorted(by_dir.items(), key=lambda kv: kv[1]["score_sum"], reverse=True)[:max_zones]

    repo_wide_blockers = [g["id"] for g in scores["gates"] if not g["passed"]]
    repo_wide_trust_level = scores["recommended_starting_trust_level"]

    zones = []
    for rank, (directory, data) in enumerate(ranked, start=1):
        stacks = sorted({Path(p).suffix.lstrip(".") or "no-ext" for p in data["paths"]})
        zones.append({
            "id": f"ZONE-{rank:02d}",
            "name": directory,
            "paths": data["paths"],
            "stack": stacks,
            "loc": data["loc"],
            "coverage_pct": None,  # Phase 0's test_probe only reports aggregate coverage, not per-zone
            "churn_rank": rank,
            "coupling_score": None,  # requires structure.* (Graphify) — see blockers if unavailable
            "blast_radius": "unknown",  # requires a real dependency graph (Phase 2) to classify contained vs. wide
            "recommended_trust_level": repo_wide_trust_level,
            "blockers": repo_wide_blockers,
            "rationale": (
                f"Highest combined churn x size in this pass ({data['commits']} commits across "
                f"{len(data['paths'])} file(s) in the last 365 days, {data['loc']} LOC) — the small, "
                f"high-churn subset this pathway prioritizes opening to agents first, not a full-repo partition."
            ),
        })
    return zones


def render_report(repo_name: str, short_sha: str, inputs: dict, scores: dict, zones: list[dict]) -> str:
    template = string.Template(Path(TEMPLATES_DIR / "agent-readiness-report.md.tmpl").read_text())
    weighted = scores["weighted_score"]
    trust = scores["recommended_starting_trust_level"]
    evidence_gate = scores["evidence_gate_to_advance"]
    return template.substitute(
        repo_name=repo_name,
        generated_at=inputs["generated_at"],
        short_sha=short_sha,
        assessment_id=scores["assessment_id"],
        verdict=scores["verdict"],
        weighted_score_display=weighted if weighted is not None else "n/a (insufficient data)",
        trust_level_display=trust if trust else "N/A",
        evidence_gate_display=evidence_gate or "—",
        verdict_reason=scores["verdict_reason"],
        gates_table=build_gates_table(scores),
        dimensions_table=build_dimensions_table(scores),
        hotspots_table=build_hotspots_table(inputs),
        pilot_zone_section=build_pilot_zone_section(zones),
        unavailable_section=build_unavailable_section(inputs),
        effort_table=build_effort_table(scores),
        next_command=(
            "# fix the gates/dimensions above, then re-run:\n"
            f"python3 scripts/collect.py {inputs['target']['source']} --out <out_dir>\n"
            "python3 scripts/score.py <out_dir>/assessment-inputs.json --out <out_dir>/assessment-scores.json"
            if scores["verdict"] != "ONBOARD_NOW"
            else "/map-codebase  # Phase 2 — this repo is ready to move forward"
        ),
    )


def render_remediation_plan(repo_name: str, inputs: dict, scores: dict) -> str:
    template = string.Template(Path(TEMPLATES_DIR / "remediation-plan.md.tmpl").read_text())
    all_passed = scores["gates_all_passed"]
    minimum_viable = (
        "All hard gates already pass. The single highest-leverage fix is whichever dimension above "
        "has the lowest sub-score relative to its weight."
        if all_passed else
        "Fix the failing hard gates first — they cap the verdict regardless of any dimension score. "
        "Everything else in this plan is secondary until GATE_BUILD, GATE_TEST_SIGNAL, and GATE_CI all pass."
    )
    return template.substitute(
        repo_name=repo_name,
        generated_at=inputs["generated_at"],
        verdict=scores["verdict"],
        blockers_table=build_blockers_table(scores),
        minimum_viable_section=minimum_viable,
    )


def append_portfolio_csv(path: Path, repo_name: str, inputs: dict, scores: dict) -> None:
    is_new = not path.exists()
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow([
                "assessment_id", "repo", "source", "generated_at", "verdict", "weighted_score",
                "gates_all_passed", "recommended_starting_trust_level", "total_loc", "history_days",
            ])
        writer.writerow([
            scores["assessment_id"], repo_name, inputs["target"]["source"], inputs["generated_at"],
            scores["verdict"], scores["weighted_score"], scores["gates_all_passed"],
            scores["recommended_starting_trust_level"],
            inputs["metrics"].get("codebase.total_loc", {}).get("value"),
            inputs["metrics"].get("vcs.history_days", {}).get("value"),
        ])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render narrative outputs for /assess-repo")
    parser.add_argument("out_dir")
    parser.add_argument("--portfolio-csv", type=str, default=None)
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    inputs = _load(out_dir / "assessment-inputs.json")
    scores = _load(out_dir / "assessment-scores.json")

    repo_name = inputs["target"]["source"].rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    short_sha = (inputs["target"]["resolved_commit"] or "nogit")[:7]

    zones = carve_zones(inputs, scores)
    (out_dir / "zones.json").write_text(json.dumps(zones, indent=2) + "\n")

    report = render_report(repo_name, short_sha, inputs, scores, zones)
    (out_dir / "agent-readiness-report.md").write_text(report)

    plan = render_remediation_plan(repo_name, inputs, scores)
    (out_dir / "remediation-plan.md").write_text(plan)

    portfolio_path = Path(args.portfolio_csv) if args.portfolio_csv else out_dir.parent / "portfolio.csv"
    append_portfolio_csv(portfolio_path, repo_name, inputs, scores)

    print(f"✅ wrote {out_dir / 'zones.json'}")
    print(f"✅ wrote {out_dir / 'agent-readiness-report.md'}")
    print(f"✅ wrote {out_dir / 'remediation-plan.md'}")
    print(f"✅ appended a row to {portfolio_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
