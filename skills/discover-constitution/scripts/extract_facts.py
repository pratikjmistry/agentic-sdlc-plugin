#!/usr/bin/env python3
"""Layer 1 extraction for /discover-constitution.

Reads `/assess-repo`'s `assessment-inputs.json` + `zones.json` (required — this
skill's entire fact base comes from them, no fallback source exists) and checks
for `/map-codebase`'s output in the target repo (`docs/codebase-map.md`,
`graphify-out/.graphify_analysis.json`) without re-deriving anything those
scripts already computed — cycles, entry points, hub fan-in/out, and community
naming stay in `synthesize.py`; this script only records whether those files
exist so the per-file generation agents know to read them directly for
narrative content.

The only things genuinely new here: partitioning the 82 measured metrics by
which draft `ai-context/*.md` file they inform, a fresh DB/ORM marker scan (no
existing metric family covers this), a CODEOWNERS marker scan, and a
`git status`-based check for whether an existing `ai-context/` is safe to
overwrite. Pure function, no wall-clock/network calls, same envelope-shaped
metrics passed straight through from `assessment-inputs.json` — byte-identical
output across repeated calls on the same input, same discipline as
`skills/assess-repo/scripts/score.py`.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

DB_ORM_MARKER_FILES = [
    "alembic.ini", "prisma/schema.prisma", "knexfile.js", "knexfile.ts",
    "ormconfig.json", "ormconfig.js", ".sequelizerc", "config/database.yml",
    "flyway.conf", "liquibase.properties",
]
DB_MIGRATIONS_DIR_NAMES = ["migrations", "db/migrations", "database/migrations"]
EF_CORE_PATTERN = re.compile(r"Microsoft\.EntityFrameworkCore", re.IGNORECASE)
CODEOWNERS_PATHS = [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]
OWNER_PATTERN = re.compile(r"@[\w-]+(?:/[\w-]+)?")

TECH_STACK_METRICS = [
    "codebase.language_census", "codebase.distinct_stacks_count",
    "build.detected_systems", "build.containerized", "build.lockfiles_present",
    "deps.manifest_count", "deps.direct_count", "deps.transitive_count",
    "deps.duplicate_framework_versions", "ci.systems_detected",
]
ARCHITECTURE_METRICS = [
    "structure.parser_coverage_pct", "structure.module_count", "structure.community_count",
    "structure.god_nodes", "structure.cyclic_dependency_count", "structure.avg_fan_out",
    "structure.max_fan_out", "structure.cross_stack_edge_count",
    "architecture.detected_patterns", "architecture.style_summary",
]
CODING_STANDARDS_METRICS = [
    "debt.analyzer_used", "debt.violations_total", "debt.violations_per_kloc",
    "debt.violations_by_severity", "debt.todo_fixme_hack_count", "debt.baselineable",
    "vcs.commit_msg_issue_ref_pct", "vcs.merge_commit_ratio", "vcs.branch_count", "vcs.stale_branch_count",
]
TESTING_METRICS = [
    "test.frameworks_detected", "test.test_file_count", "test.test_to_source_ratio",
    "test.coverage_pct", "test.coverage_source", "test.suite_executes", "test.suite_duration_s",
    "test.pass_rate", "test.flake_indicators", "test.unit_present", "test.integration_present",
    "test.e2e_present", "test.fixture_or_seed_data_present", "ci.gates", "ci.runs_on_pr",
]
SECURITY_METRICS = [
    "deps.direct_count", "deps.duplicate_framework_versions", "build.external_service_deps",
    "build.required_env_var_count", "ops.observability_present",
]
DEPLOYMENT_METRICS = [
    "ops.deploy_automation_present", "ops.staging_env_declared", "ops.rollback_mechanism_documented",
    "build.containerized", "build.devcontainer_present", "ci.systems_detected", "build.external_service_deps",
]
OBSERVABILITY_METRICS = ["ops.observability_present", "ops.feature_flag_system_present"]
REPO_STRUCTURE_METRICS = [
    "structure.module_count", "structure.community_count",
    "context.readme_quality_score", "context.docs_loc", "context.adr_count",
]
FRONTEND_LANGUAGES = {"javascript", "typescript", "css", "scss", "html"}


def _pick(metrics: dict, ids: list[str]) -> dict:
    return {mid: metrics[mid] for mid in ids if mid in metrics}


def load_assessment_inputs(assessment_dir: Path) -> dict:
    path = Path(assessment_dir) / "assessment-inputs.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run /assess-repo on this repo first; "
            "/discover-constitution has no fallback source for these facts."
        )
    return json.loads(path.read_text())


def load_zones(assessment_dir: Path) -> list[dict]:
    path = Path(assessment_dir) / "zones.json"
    if not path.exists():
        return []
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


def check_existing_ai_context(repo_path: Path) -> dict:
    ai_context_dir = Path(repo_path) / "ai-context"
    if not ai_context_dir.is_dir():
        return {"present": False, "files": []}
    return {"present": True, "files": sorted(p.name for p in ai_context_dir.glob("*.md"))}


def ai_context_is_reconcilable(repo_path: Path) -> tuple[bool, str]:
    """Only ever says "safe to overwrite" when git can positively confirm
    ai-context/ is unmodified relative to HEAD. Every other case (no git, git
    error, uncommitted changes) errs toward not overwriting."""
    repo_path = Path(repo_path)
    if not (repo_path / ".git").exists():
        return False, ("not a git repository (no .git at repo root) — cannot verify ai-context/ is "
                        "unmodified, draft to a staging directory instead of overwriting")
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain", "--", "ai-context/"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"git status failed ({exc}) — draft to a staging directory instead of overwriting"
    if result.returncode != 0:
        return False, f"git status exited {result.returncode} — draft to a staging directory instead of overwriting"
    if result.stdout.strip():
        return False, ("ai-context/ has uncommitted changes (git status is non-empty) — draft to "
                        "ai-context/.discover-constitution-draft/ instead of overwriting")
    return True, "ai-context/ matches HEAD (git status is empty) — safe to overwrite; review with `git diff ai-context/` after"


def detect_db_orm(repo_path: Path) -> dict:
    repo_path = Path(repo_path)
    evidence = [m for m in DB_ORM_MARKER_FILES if (repo_path / m).exists()]

    migrations_dir = next((d for d in DB_MIGRATIONS_DIR_NAMES if (repo_path / d).is_dir()), None)
    if migrations_dir:
        evidence.append(f"{migrations_dir}/ directory")

    for csproj in list(repo_path.rglob("*.csproj"))[:50]:
        try:
            if EF_CORE_PATTERN.search(csproj.read_text(errors="replace")):
                evidence.append(str(csproj.relative_to(repo_path)))
                break
        except OSError:
            continue

    present = bool(evidence)
    return {
        "present": present,
        "evidence": evidence,
        "confidence": "derived",
        "notes": ("marker-file/migrations-directory/EF-Core-reference heuristic scan"
                  if present else "no ORM/migration markers found in this scan"),
    }


def detect_codeowners(repo_path: Path) -> dict:
    repo_path = Path(repo_path)
    for rel in CODEOWNERS_PATHS:
        path = repo_path / rel
        if not path.exists():
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        owners: list[str] = []
        for match in OWNER_PATTERN.findall(text):
            if match not in owners:
                owners.append(match)
            if len(owners) >= 5:
                break
        return {"present": True, "path": rel, "owners_sample": owners}
    return {"present": False, "path": None, "owners_sample": []}


def _build_risk_areas(metrics: dict, zones: list[dict]) -> list[dict]:
    """Feathers-style seam/characterization-test candidates: architectural hubs,
    cyclic dependencies, and zones with wide blast radius or high coupling —
    surfaced here, never invented, and only from what assessment-inputs.json and
    zones.json already measured (no re-parsing of docs/codebase-map.md)."""
    risk_areas: list[dict] = []

    god_nodes_env = metrics.get("structure.god_nodes", {})
    if god_nodes_env.get("confidence") not in (None, "unavailable"):
        nodes = sorted(
            god_nodes_env.get("value") or [],
            key=lambda n: (n.get("fan_in", 0) or 0) + (n.get("fan_out", 0) or 0),
            reverse=True,
        )
        for node in nodes[:5]:
            risk_areas.append({
                "kind": "god_node",
                "identifier": node.get("symbol") or node.get("path") or "unknown",
                "detail": f"fan_in={node.get('fan_in')}, fan_out={node.get('fan_out')} at {node.get('path')}",
                "why": ("High-coupling hub — a seam candidate for /plan-seams and a characterization-test "
                        "priority for /characterize before any refactor touches it."),
                "confidence": "derived",
            })

    cyclic_env = metrics.get("structure.cyclic_dependency_count", {})
    if cyclic_env.get("confidence") not in (None, "unavailable") and (cyclic_env.get("value") or 0) > 0:
        risk_areas.append({
            "kind": "cyclic_dependencies",
            "identifier": f"{cyclic_env['value']} cyclic dependency group(s)",
            "detail": "See docs/codebase-map.md's Cyclic Dependencies section for the specific groups.",
            "why": ("Cyclic dependencies are a classic seam blocker — breaking one is often the seam "
                    "/plan-seams needs to introduce a test point."),
            "confidence": "derived",
        })

    for zone in zones:
        coupling_score = zone.get("coupling_score")
        wide_coupling = isinstance(coupling_score, (int, float)) and coupling_score > 0.5
        if zone.get("blast_radius") == "wide" or wide_coupling:
            risk_areas.append({
                "kind": "zone_blast_radius",
                "identifier": zone.get("name") or zone.get("id") or "unknown zone",
                "detail": (f"blast_radius={zone.get('blast_radius')}, coupling_score={coupling_score}, "
                           f"churn_rank={zone.get('churn_rank')}"),
                "why": ("Wide blast radius plus high churn — prioritize a characterization test here "
                        "before /plan-seams proposes a seam."),
                "confidence": "derived",
            })

    return risk_areas


def build_tech_stack_facts(inputs: dict) -> dict:
    return {"metrics": _pick(inputs.get("metrics", {}), TECH_STACK_METRICS)}


def build_architecture_facts(inputs: dict, zones: list[dict], map_outputs: dict) -> dict:
    metrics = _pick(inputs.get("metrics", {}), ARCHITECTURE_METRICS)
    target = inputs.get("target", {})
    return {
        "metrics": metrics,
        "is_monorepo": target.get("is_monorepo"),
        "detected_projects": target.get("detected_projects", []),
        "zones": zones,
        "map_codebase_outputs": map_outputs,
        "risk_areas": _build_risk_areas(metrics, zones),
    }


def build_coding_standards_facts(inputs: dict) -> dict:
    return {"metrics": _pick(inputs.get("metrics", {}), CODING_STANDARDS_METRICS)}


def build_testing_facts(inputs: dict) -> dict:
    return {"metrics": _pick(inputs.get("metrics", {}), TESTING_METRICS)}


def build_security_facts(inputs: dict) -> dict:
    return {
        "metrics": _pick(inputs.get("metrics", {}), SECURITY_METRICS),
        "notes": ("assess-repo collects no auth/authz signal directly — every claim in security.md beyond "
                  "these weak proxies must be treated as [DECISION PENDING] and confirmed with the team."),
    }


def build_deployment_facts(inputs: dict, zones: list[dict]) -> dict:
    return {"metrics": _pick(inputs.get("metrics", {}), DEPLOYMENT_METRICS), "zone_count": len(zones)}


def build_observability_facts(inputs: dict) -> dict:
    return {"metrics": _pick(inputs.get("metrics", {}), OBSERVABILITY_METRICS)}


def build_repo_structure_facts(inputs: dict, zones: list[dict]) -> dict:
    target = inputs.get("target", {})
    return {
        "metrics": _pick(inputs.get("metrics", {}), REPO_STRUCTURE_METRICS),
        "is_monorepo": target.get("is_monorepo"),
        "detected_projects": target.get("detected_projects", []),
        "zones": zones,
    }


def build_database_guidelines_facts(inputs: dict, db_orm: dict) -> dict:
    return {
        "metrics": _pick(inputs.get("metrics", {}), ["context.db_schema_docs_present"]),
        "db_orm": db_orm,
    }


def recommend_files(inputs: dict, db_orm: dict) -> dict:
    metrics = inputs.get("metrics", {})
    target = inputs.get("target", {})

    def val(mid):
        return (metrics.get(mid) or {}).get("value")

    language_census = val("codebase.language_census") or []
    frontend_pct = sum(
        row.get("pct", 0) or 0 for row in language_census
        if str(row.get("language", "")).lower() in FRONTEND_LANGUAGES
    )
    api_spec_present = bool(val("context.api_spec_present"))
    db_schema_docs_present = bool(val("context.db_schema_docs_present"))
    is_monorepo = bool(target.get("is_monorepo"))
    module_count = val("structure.module_count") or 0

    return {
        "security.md": {
            "recommend": True,
            "reason": ("Always recommended — assess-repo has no direct auth/authz signal, but every "
                       "production codebase needs a documented security posture."),
            "confidence": "estimated",
        },
        "api-guidelines.md": {
            "recommend": api_spec_present,
            "reason": ("OpenAPI/Swagger/.proto spec file detected." if api_spec_present
                       else "No API spec marker file found."),
            "confidence": "derived",
        },
        "design-system.md": {
            "recommend": frontend_pct >= 15,
            "reason": (f"Frontend languages are {frontend_pct:.0f}% of the codebase." if frontend_pct
                       else "No significant frontend-language share detected."),
            "confidence": "derived",
        },
        "deployment.md": {
            "recommend": bool(val("build.containerized") or val("ops.deploy_automation_present") or val("ci.systems_detected")),
            "reason": ("Containerization, deploy automation, or a CI system was detected."
                       if bool(val("build.containerized") or val("ops.deploy_automation_present") or val("ci.systems_detected"))
                       else "No containerization, deploy automation, or CI system detected."),
            "confidence": "derived",
        },
        "observability.md": {
            "recommend": bool(val("ops.observability_present") or val("ops.feature_flag_system_present")),
            "reason": ("Observability tooling or a feature-flag system was detected."
                       if bool(val("ops.observability_present") or val("ops.feature_flag_system_present"))
                       else "No observability tooling or feature-flag system detected."),
            "confidence": "derived",
        },
        "repo-structure.md": {
            "recommend": is_monorepo or module_count > 5,
            "reason": "Monorepo or multi-module structure detected." if (is_monorepo or module_count > 5)
                      else "Single-module structure — architecture.md likely covers this already.",
            "confidence": "derived",
        },
        "database-guidelines.md": {
            "recommend": bool(db_orm.get("present")) or db_schema_docs_present,
            "reason": ("ORM/migration markers or documented DB schema found." if (db_orm.get("present") or db_schema_docs_present)
                       else "No ORM/migration markers or DB schema docs found."),
            "confidence": "derived",
        },
        "ralph-agent-spec.md": {
            "recommend": True,
            "reason": "Always recommended — this pipeline exists to run agentic coding loops against this repo.",
            "confidence": "measured",
        },
    }


def build_facts(assessment_dir: Path, repo_path: Path) -> dict:
    assessment_dir = Path(assessment_dir)
    repo_path = Path(repo_path)

    inputs = load_assessment_inputs(assessment_dir)
    zones = load_zones(assessment_dir)
    map_outputs = find_map_codebase_outputs(repo_path)
    existing_ai_context = check_existing_ai_context(repo_path)
    reconcilable, reconcile_detail = ai_context_is_reconcilable(repo_path)
    db_orm = detect_db_orm(repo_path)
    codeowners = detect_codeowners(repo_path)

    return {
        "schema_version": "1.0",
        "source_assessment_id": inputs.get("assessment_id"),
        "source_generated_at": inputs.get("generated_at"),
        "repo_path": str(repo_path),
        "map_codebase_outputs": map_outputs,
        "existing_ai_context": existing_ai_context,
        "reconciliation": {"reconcilable": reconcilable, "detail": reconcile_detail},
        "db_orm": db_orm,
        "codeowners": codeowners,
        "file_recommendations": recommend_files(inputs, db_orm),
        "facts": {
            "tech_stack": build_tech_stack_facts(inputs),
            "architecture": build_architecture_facts(inputs, zones, map_outputs),
            "coding_standards": build_coding_standards_facts(inputs),
            "testing": build_testing_facts(inputs),
            "security": build_security_facts(inputs),
            "deployment": build_deployment_facts(inputs, zones),
            "observability": build_observability_facts(inputs),
            "repo_structure": build_repo_structure_facts(inputs, zones),
            "database_guidelines": build_database_guidelines_facts(inputs, db_orm),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract constitution-drafting facts for /discover-constitution")
    parser.add_argument("assessment_dir", help="Path to /assess-repo's .assessment/<repo>-<shortsha>/ output dir")
    parser.add_argument("repo_path", help="Path to the target repo (checked for ai-context/, docs/codebase-map.md, graphify-out/)")
    parser.add_argument("--out", type=str, default=None, help="Defaults to <assessment_dir>/constitution-facts.json")
    args = parser.parse_args(argv)

    facts = build_facts(Path(args.assessment_dir), Path(args.repo_path))
    out_path = Path(args.out) if args.out else Path(args.assessment_dir) / "constitution-facts.json"
    out_path.write_text(json.dumps(facts, indent=2) + "\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
