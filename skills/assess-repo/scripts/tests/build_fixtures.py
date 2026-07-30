#!/usr/bin/env python3
"""Generates the scored-scenario fixtures under tests/fixtures/ used by
test_score.py. Run this to regenerate fixtures after changing the schema;
the fixtures themselves are committed, this script is not invoked at test
time.
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "assessment-inputs.schema.json"


def m(value, unit="", source="fixture", confidence="measured", coverage_pct=100, notes=""):
    return {"value": value, "unit": unit, "source": source, "confidence": confidence,
            "coverage_pct": coverage_pct, "notes": notes}


def unavailable(notes="not available in this fixture"):
    return m(None, confidence="unavailable", coverage_pct=None, notes=notes)


def base_document(assessment_id: str) -> dict:
    """A fully-populated, internally-consistent 'strong repo' baseline.
    Scenario fixtures below start from this and override specific metrics."""
    metrics = {
        # codebase.*
        "codebase.total_loc": m(42000, "loc"),
        "codebase.file_count": m(650, "count"),
        "codebase.language_census": m([
            {"language": "Python", "loc": 38000, "pct": 90.5, "files": 580},
            {"language": "Shell", "loc": 4000, "pct": 9.5, "files": 70},
        ], "per_language"),
        "codebase.distinct_stacks_count": m(2, "count"),
        "codebase.generated_loc_pct": m(1.2, "pct"),
        "codebase.largest_file_loc": m(1200, "loc"),
        "codebase.avg_file_loc": m(64.6, "loc"),
        "codebase.p95_file_loc": m(310, "loc"),

        # vcs.*
        "vcs.history_days": m(2200, "days"),
        "vcs.commits_last_90d": m(180, "count"),
        "vcs.commits_last_365d": m(720, "count"),
        "vcs.active_authors_last_90d": m(12, "count"),
        "vcs.total_authors": m(45, "count"),
        "vcs.author_concentration_gini": m(0.42, "gini"),
        "vcs.single_author_file_pct": m(18.0, "pct"),
        "vcs.default_branch": m("main", ""),
        "vcs.branch_count": m(6, "count"),
        "vcs.stale_branch_count": m(1, "count"),
        "vcs.merge_commit_ratio": m(0.35, "ratio"),
        "vcs.commit_msg_issue_ref_pct": m(72.0, "pct"),
        "vcs.hotspots": m([
            {"path": "src/core/engine.py", "commits_365d": 40, "loc": 800, "authors": 6, "hotspot_score": 32000},
        ], "ranked_list"),

        # build.*
        "build.detected_systems": m(["poetry"], "list"),
        "build.containerized": m(True, "bool"),
        "build.devcontainer_present": m(True, "bool"),
        "build.one_command_build_documented": m(True, "bool"),
        "build.lockfiles_present": m(True, "bool"),
        "build.required_env_var_count": m(2, "count"),
        "build.external_service_deps": m(["postgres"], "list"),
        "build.attempt": m({"attempted": False, "exit_code": None, "duration_s": None, "stderr_tail": ""}, "object"),

        # test.*
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

        # ci.*
        "ci.systems_detected": m(["github-actions"], "list"),
        "ci.runs_on_pr": m(True, "bool"),
        "ci.gates": m({"lint": True, "test": True, "coverage": True, "security": True, "build": True}, "object"),
        "ci.success_rate_recent": m(96.0, "pct"),
        "ci.avg_duration_s": m(420.0, "seconds"),

        # deps.*
        "deps.manifest_count": m(1, "count"),
        "deps.direct_count": m(28, "count"),
        "deps.transitive_count": m(140, "count"),
        "deps.duplicate_framework_versions": m([], "list"),
        "deps.eol_components": m([], "list"),
        "deps.median_majors_behind": m(0, "count"),
        "deps.known_vuln_count_by_severity": m({"critical": 0, "high": 0, "medium": 1, "low": 3}, "object"),

        # structure.*
        "structure.parser_coverage_pct": m(95.0, "pct"),
        "structure.module_count": m(48, "count"),
        "structure.community_count": m(6, "count"),
        "structure.god_nodes": m([], "list"),
        "structure.cyclic_dependency_count": m(0, "count"),
        "structure.avg_fan_out": m(3.1, "count"),
        "structure.max_fan_out": m(14, "count"),
        "structure.cross_stack_edge_count": m(0, "count"),

        # debt.*
        "debt.analyzer_used": m("ruff+semgrep", ""),
        "debt.violations_total": m(80, "count"),
        "debt.violations_per_kloc": m(1.9, "ratio"),
        "debt.violations_by_severity": m({"critical": 0, "high": 2, "medium": 30, "low": 48}, "object"),
        "debt.todo_fixme_hack_count": m(35, "count"),
        "debt.baselineable": m(True, "bool"),

        # context.*
        "context.readme_quality_score": m(88.0, "pct"),
        "context.adr_count": m(12, "count"),
        "context.docs_loc": m(3000, "loc"),
        "context.api_spec_present": m(True, "bool"),
        "context.db_schema_docs_present": m(True, "bool"),
        "context.domain_glossary_present": m(True, "bool"),
        "context.ai_context_present": m(True, "bool"),

        # ops.*
        "ops.deploy_automation_present": m(True, "bool"),
        "ops.staging_env_declared": m(True, "bool"),
        "ops.observability_present": m(True, "bool"),
        "ops.feature_flag_system_present": m(True, "bool"),
        "ops.rollback_mechanism_documented": m(True, "bool"),

        # architecture.* — Phase-0 heuristic only, never wired into a rubric.yaml dimension
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
        "providers": [{"name": "git", "version": "", "status": "ok", "reason": ""}],
        "exclusions": {"patterns": ["node_modules/**"], "excluded_loc": 500, "excluded_file_count": 20},
        "human_inputs": {
            "business_criticality_1_5": 4,
            "roadmap_demand_next_2q": "heavy",
            "client_data_policy": {
                "third_party_tooling_allowed": True,
                "external_llm_allowed": True,
                "code_may_leave_premises": False,
            },
            "sunset_or_replatform_planned": False,
            "sunset_target_date": None,
            "domain_expert_available": True,
            "onboarding_squad_size": 2,
            "regulatory_or_audit_constraints": None,
            "collected_at": "2026-07-27T00:00:00+00:00",
        },
        "metrics": metrics,
    }


def scenario_strong() -> dict:
    return base_document("fixture-strong")


def scenario_sparse_legacy() -> dict:
    """No tests, no CI on PR, no containerization — gates fail even though
    what data IS available paints a middling structural picture."""
    doc = base_document("fixture-sparse-legacy")
    doc["human_inputs"]["roadmap_demand_next_2q"] = "moderate"
    overrides = {
        "build.containerized": m(False, "bool"),
        "build.devcontainer_present": m(False, "bool"),
        "build.one_command_build_documented": m(False, "bool"),
        "build.detected_systems": m(["msbuild"], "list"),
        "build.lockfiles_present": m(False, "bool"),
        "test.suite_executes": m(False, "bool"),
        "test.test_file_count": m(0, "count"),
        "test.coverage_pct": m(None, "pct", confidence="unavailable", coverage_pct=None,
                                 notes="no test suite to measure coverage from"),
        "test.unit_present": m(False, "bool"),
        "test.integration_present": m(False, "bool"),
        "ci.systems_detected": m([], "list"),
        "ci.runs_on_pr": m(False, "bool"),
        "structure.parser_coverage_pct": m(35.0, "pct", notes="legacy VB6 modules unsupported by tree-sitter grammar"),
        "codebase.distinct_stacks_count": m(5, "count"),
        "deps.duplicate_framework_versions": m(["React 16", "React 18"], "list"),
        "debt.violations_per_kloc": m(65.0, "ratio"),
        "context.ai_context_present": m(False, "bool"),
        "context.readme_quality_score": m(20.0, "pct"),
        "context.adr_count": m(0, "count"),
        "context.domain_glossary_present": m(False, "bool"),
    }
    doc["metrics"].update(overrides)
    return doc


def scenario_do_not_onboard() -> dict:
    """Identical to the strong fixture — score would be perfect — except the
    repo is stable and unwanted: DO_NOT_ONBOARD must still win outright."""
    doc = base_document("fixture-do-not-onboard")
    doc["human_inputs"]["roadmap_demand_next_2q"] = "none"
    return doc


def scenario_defer() -> dict:
    """Gates all pass (a real autonomy floor exists — one_command/containerized
    still counts as 'a build path exists', suite still executes), but every
    dimension's *sub-score* is pushed to its floor while remaining just
    gate-passing, so the weighted total lands well under the remediation
    threshold. Demand is heavy, so this should land on DEFER, not
    ONBOARD_AFTER_REMEDIATION."""
    doc = base_document("fixture-defer")
    overrides = {
        # GATE_BUILD only needs ONE of these true; keep containerized true so
        # the gate passes, but starve every other build_reproducibility band
        # input so its sub-score floors at 0 (see score_build_reproducibility).
        "build.containerized": m(True, "bool"),
        "build.devcontainer_present": m(False, "bool"),
        "build.one_command_build_documented": m(False, "bool"),
        "build.lockfiles_present": m(False, "bool"),
        "build.detected_systems": m([], "list"),
        # GATE_TEST_SIGNAL only needs suite_executes true; coverage/unit/integration
        # can all be poor and test_safety_net still floors at 60, not 0.
        "test.coverage_pct": m(5.0, "pct"),
        "test.unit_present": m(False, "bool"),
        "test.integration_present": m(False, "bool"),
        "structure.cyclic_dependency_count": m(25, "count"),
        "structure.god_nodes": m([{"symbol": "GodManager", "path": "src/god.py", "fan_in": 40, "fan_out": 55}], "list"),
        "structure.avg_fan_out": m(22.0, "count"),
        "structure.parser_coverage_pct": m(60.0, "pct"),  # stays >= usability threshold, but lowers analyzability's own band
        "codebase.distinct_stacks_count": m(9, "count"),
        "deps.duplicate_framework_versions": m(["Flask 1", "Flask 2", "Flask 3"], "list"),
        "debt.violations_per_kloc": m(180.0, "ratio"),
        "context.ai_context_present": m(False, "bool"),
        "context.readme_quality_score": m(10.0, "pct"),
        "context.adr_count": m(0, "count"),
        "context.domain_glossary_present": m(False, "bool"),
        "ops.staging_env_declared": m(False, "bool"),
    }
    doc["metrics"].update(overrides)
    return doc


def scenario_gates_pass_no_dimension_data() -> dict:
    """Contrived by design: every gate's OWN narrow metric requirement is
    satisfied, but each dimension's WIDER backing-metric set is not — isolating
    the weighted_score-is-None verdict branch, which real provider coverage
    gaps can't otherwise reach (gate failures dominate first in practice)."""
    doc = base_document("fixture-gates-pass-no-data")
    doc["human_inputs"]["roadmap_demand_next_2q"] = None  # keep DEFER/DO_NOT_ONBOARD out of play
    for metric_id in list(doc["metrics"].keys()):
        doc["metrics"][metric_id] = unavailable("withheld to isolate the weighted_score=None branch")
    # Only the exact metrics each gate function reads are restored as available.
    doc["metrics"]["build.containerized"] = m(True, "bool")
    doc["metrics"]["build.devcontainer_present"] = m(False, "bool")
    doc["metrics"]["build.one_command_build_documented"] = m(False, "bool")
    doc["metrics"]["test.suite_executes"] = m(True, "bool")
    doc["metrics"]["ci.systems_detected"] = m(["github-actions"], "list")
    doc["metrics"]["ci.runs_on_pr"] = m(True, "bool")
    return doc


def scenario_redistribution() -> dict:
    """Every dimension available except debt_containability (both its backing
    metrics unavailable) — isolates the weight-redistribution arithmetic."""
    doc = base_document("fixture-redistribution")
    doc["metrics"]["debt.violations_per_kloc"] = unavailable("debt_probe not yet implemented")
    doc["metrics"]["debt.baselineable"] = unavailable("debt_probe not yet implemented")
    return doc


def scenario_only_layer1() -> dict:
    """What collect.py actually produces today: only codebase.* and vcs.* are
    measured, everything else unavailable. Mirrors the real dry-run shape."""
    doc = base_document("fixture-only-layer1")
    families_to_blank = ["build", "test", "ci", "deps", "structure", "debt", "context", "ops", "architecture"]
    for metric_id in list(doc["metrics"].keys()):
        family = metric_id.split(".")[0]
        if family in families_to_blank:
            doc["metrics"][metric_id] = unavailable("provider not yet implemented (steps 5-6)")
    doc["human_inputs"] = {}
    return doc


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = {
        "scored-strong.json": scenario_strong(),
        "scored-sparse-legacy.json": scenario_sparse_legacy(),
        "scored-do-not-onboard.json": scenario_do_not_onboard(),
        "scored-defer.json": scenario_defer(),
        "scored-redistribution.json": scenario_redistribution(),
        "scored-only-layer1.json": scenario_only_layer1(),
        "scored-gates-pass-no-data.json": scenario_gates_pass_no_dimension_data(),
    }
    for filename, doc in scenarios.items():
        path = FIXTURES_DIR / filename
        path.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
