#!/usr/bin/env python3
"""Generates the assessment-inputs.json fixtures under tests/fixtures/ used by
test_extract_facts.py. Run this to regenerate fixtures after changing which
metric IDs extract_facts.py reads; the fixtures themselves are committed, this
script is not invoked at test time. Follows the same m()/unavailable()/
base_document() pattern as skills/assess-repo/scripts/tests/build_fixtures.py
(kept as a local copy, not a cross-skill import, since these fixtures cover a
different metric subset and evolve independently).
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def m(value, unit="", source="fixture", confidence="measured", coverage_pct=100, notes=""):
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def unavailable(notes="not available in this fixture"):
    return m(None, confidence="unavailable", coverage_pct=None, notes=notes)


def base_document(assessment_id: str) -> dict:
    metrics = {
        "codebase.total_loc": m(42000, "loc"),
        "codebase.file_count": m(650, "count"),
        "codebase.language_census": m([
            {"language": "Python", "loc": 38000, "pct": 90.5, "files": 580},
            {"language": "Shell", "loc": 4000, "pct": 9.5, "files": 70},
        ], "per_language"),
        "codebase.distinct_stacks_count": m(2, "count"),

        "vcs.commit_msg_issue_ref_pct": m(72.0, "pct"),
        "vcs.merge_commit_ratio": m(0.35, "ratio"),
        "vcs.branch_count": m(6, "count"),
        "vcs.stale_branch_count": m(1, "count"),

        "build.detected_systems": m(["poetry"], "list"),
        "build.containerized": m(True, "bool"),
        "build.devcontainer_present": m(True, "bool"),
        "build.lockfiles_present": m(True, "bool"),
        "build.external_service_deps": m(["postgres"], "list"),
        "build.required_env_var_count": m(2, "count"),

        "test.frameworks_detected": m(["pytest"], "list"),
        "test.test_file_count": m(210, "count"),
        "test.test_to_source_ratio": m(0.36, "ratio"),
        "test.coverage_pct": m(85.0, "pct"),
        "test.coverage_source": m("coverage.py", ""),
        "test.suite_executes": m(True, "bool"),
        "test.suite_duration_s": m(95.0, "seconds"),
        "test.pass_rate": m(99.5, "pct"),
        "test.flake_indicators": m(0, "count"),
        "test.unit_present": m(True, "bool"),
        "test.integration_present": m(True, "bool"),
        "test.e2e_present": m(True, "bool"),
        "test.fixture_or_seed_data_present": m(True, "bool"),

        "ci.systems_detected": m(["github-actions"], "list"),
        "ci.runs_on_pr": m(True, "bool"),
        "ci.gates": m({"lint": True, "test": True, "coverage": True, "security": True, "build": True}, "object"),

        "deps.manifest_count": m(1, "count"),
        "deps.direct_count": m(28, "count"),
        "deps.transitive_count": m(140, "count"),
        "deps.duplicate_framework_versions": m([], "list"),

        "structure.parser_coverage_pct": m(95.0, "pct"),
        "structure.module_count": m(48, "count"),
        "structure.community_count": m(6, "count"),
        "structure.god_nodes": m([], "list"),
        "structure.cyclic_dependency_count": m(0, "count"),
        "structure.avg_fan_out": m(3.1, "count"),
        "structure.max_fan_out": m(14, "count"),
        "structure.cross_stack_edge_count": m(0, "count"),

        "debt.analyzer_used": m("ruff+semgrep", ""),
        "debt.violations_total": m(80, "count"),
        "debt.violations_per_kloc": m(1.9, "ratio"),
        "debt.violations_by_severity": m({"critical": 0, "high": 2, "medium": 30, "low": 48}, "object"),
        "debt.todo_fixme_hack_count": m(35, "count"),
        "debt.baselineable": m(True, "bool"),

        "context.readme_quality_score": m(88.0, "pct"),
        "context.adr_count": m(12, "count"),
        "context.docs_loc": m(3000, "loc"),
        "context.api_spec_present": m(True, "bool"),
        "context.db_schema_docs_present": m(True, "bool"),
        "context.domain_glossary_present": m(True, "bool"),
        "context.ai_context_present": m(True, "bool"),

        "ops.deploy_automation_present": m(True, "bool"),
        "ops.staging_env_declared": m(True, "bool"),
        "ops.observability_present": m(True, "bool"),
        "ops.feature_flag_system_present": m(True, "bool"),
        "ops.rollback_mechanism_documented": m(True, "bool"),

        "architecture.detected_patterns": m(
            [{"pattern": "Layered / Repository", "confidence": "estimated",
              "evidence": "both services/ and repositories/ directories present"}], "list", confidence="estimated"),
        "architecture.style_summary": m("Layered / Repository", "", confidence="estimated"),
    }

    return {
        "schema_version": "1.0",
        "rubric_version": "1.0",
        "assessment_id": assessment_id,
        "generated_at": "2026-07-27T00:00:00+00:00",
        "target": {
            "mode": "git_url", "source": "https://example.com/org/repo.git",
            "resolved_commit": "a" * 40, "default_branch": "main", "history_complete": True,
            "analyzed_path": "/tmp/repo", "is_monorepo": False, "detected_projects": [], "submodules": [],
        },
        "human_inputs": {
            "business_criticality_1_5": 4,
            "roadmap_demand_next_2q": "heavy",
            "collected_at": "2026-07-27T00:00:00+00:00",
        },
        "metrics": metrics,
    }


def scenario_rich_signal() -> dict:
    """Structure.* fully populated as if /map-codebase already ran: a
    monorepo with a couple of god nodes and one cyclic dependency group, so
    build_architecture_facts()'s risk_areas synthesis has something to find."""
    doc = base_document("fixture-rich-signal")
    doc["target"]["is_monorepo"] = True
    doc["target"]["detected_projects"] = [
        {"path": "services/api", "stack": "python"},
        {"path": "services/web", "stack": "javascript"},
    ]
    overrides = {
        "structure.god_nodes": m([
            {"symbol": "EngineCore", "path": "src/core/engine.py", "fan_in": 40, "fan_out": 22},
            {"symbol": "Utils", "path": "src/util.py", "fan_in": 55, "fan_out": 3},
        ], "list"),
        "structure.cyclic_dependency_count": m(2, "count"),
        "codebase.language_census": m([
            {"language": "Python", "loc": 20000, "pct": 55.0, "files": 300},
            {"language": "TypeScript", "loc": 12000, "pct": 33.0, "files": 200},
            {"language": "CSS", "loc": 4400, "pct": 12.0, "files": 40},
        ], "per_language"),
    }
    doc["metrics"].update(overrides)
    return doc


def scenario_sparse_legacy() -> dict:
    """No structure.* family at all (map-codebase never ran), no tests, no
    CI — the degraded-mode case build_facts() must never crash on."""
    doc = base_document("fixture-sparse-legacy")
    overrides = {
        "structure.parser_coverage_pct": unavailable("graphify not installed"),
        "structure.module_count": unavailable("graphify not installed"),
        "structure.community_count": unavailable("graphify not installed"),
        "structure.god_nodes": unavailable("graphify not installed"),
        "structure.cyclic_dependency_count": unavailable("graphify not installed"),
        "structure.avg_fan_out": unavailable("graphify not installed"),
        "structure.max_fan_out": unavailable("graphify not installed"),
        "structure.cross_stack_edge_count": unavailable("graphify not installed"),
        "test.suite_executes": m(False, "bool"),
        "test.test_file_count": m(0, "count"),
        "test.coverage_pct": unavailable("no test suite to measure coverage from"),
        "test.unit_present": m(False, "bool"),
        "test.integration_present": m(False, "bool"),
        "ci.systems_detected": m([], "list"),
        "ci.runs_on_pr": m(False, "bool"),
        "context.ai_context_present": m(False, "bool"),
        "context.api_spec_present": m(False, "bool"),
        "context.db_schema_docs_present": m(False, "bool"),
    }
    doc["metrics"].update(overrides)
    return doc


ZONES_SAMPLE = [
    {
        "id": "ZONE-01", "name": "src/core", "paths": ["src/core/engine.py"], "stack": ["py"],
        "loc": 800, "coverage_pct": None, "churn_rank": 1,
        "coupling_score": 0.72, "blast_radius": "wide",
        "recommended_trust_level": "L0", "blockers": ["GATE_TEST_SIGNAL"],
        "rationale": "Highest combined churn x size in this pass.",
    },
    {
        "id": "ZONE-02", "name": "src/util", "paths": ["src/util.py"], "stack": ["py"],
        "loc": 200, "coverage_pct": None, "churn_rank": 2,
        "coupling_score": 0.10, "blast_radius": "contained",
        "recommended_trust_level": "L1", "blockers": [],
        "rationale": "Second-highest combined churn x size in this pass.",
    },
]


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = {
        "assessment-inputs-rich-signal.json": scenario_rich_signal(),
        "assessment-inputs-sparse-legacy.json": scenario_sparse_legacy(),
    }
    for filename, doc in scenarios.items():
        path = FIXTURES_DIR / filename
        path.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"wrote {path}")

    zones_path = FIXTURES_DIR / "zones-sample.json"
    zones_path.write_text(json.dumps(ZONES_SAMPLE, indent=2) + "\n")
    print(f"wrote {zones_path}")


if __name__ == "__main__":
    main()
